"""EmbedWrapper: YOLOE-26s detection + embedding branch as one fixed-shape graph (SPEC 3.1.2).

Inputs: images (1,3,640,640) f32 RGB 0-1; proposal_pe (1,8,512) f32 (text prompt embeddings, fed by
the app so no class list is baked in). Outputs: top-100 anchors by objectness, with the contrastive
head's pre-text-dot vector, so the app scores any concept as
sigmoid(fp_scale*cos(fp, text)+fp_bias).
"""

from __future__ import annotations

import torch
import torch.nn.functional as F
from torch import nn

IMGSZ = 640
TOPK = 100
N_PROMPTS = 8
EMBED = 512


def concept_scores(
    fingerprint: torch.Tensor, fp_scale: torch.Tensor, fp_bias: torch.Tensor, text: torch.Tensor
) -> torch.Tensor:
    """(N,512) fp, (N,) scale, (N,) bias, (M,512) text -> (N,M) sigmoid(scale*cos + bias)."""
    t = F.normalize(text, dim=-1)
    return torch.sigmoid(fp_scale[:, None] * (fingerprint @ t.T) + fp_bias[:, None])


class EmbedWrapper(nn.Module):
    def __init__(self, yoloe_model: nn.Module) -> None:
        super().__init__()
        from ultralytics.utils.tal import dist2bbox, make_anchors

        self.layers = yoloe_model.model[:-1]
        self.head = yoloe_model.model[-1]
        self.save = set(yoloe_model.save)
        self._dist2bbox = dist2bbox
        head = self.head
        if not getattr(head, "one2one_cv2", None) is not None:
            raise NotImplementedError("model has no one2one branch (was it fused?)")
        strides = [float(s) for s in head.stride]
        feats = [torch.zeros(1, 1, IMGSZ // int(s), IMGSZ // int(s)) for s in strides]
        a, s = make_anchors(feats, head.stride, 0.5)
        self.register_buffer("anchors", a.transpose(0, 1).unsqueeze(0).contiguous())  # (1,2,A)
        self.register_buffer("strides", s.transpose(0, 1).contiguous())  # (1,A)
        self.level_sizes = [f.shape[2] * f.shape[3] for f in feats]
        self.eval()

    def _head_inputs(self, images: torch.Tensor) -> list[torch.Tensor]:
        y: list = []
        x = images
        for m in self.layers:
            if m.f != -1:
                x = y[m.f] if isinstance(m.f, int) else [x if j == -1 else y[j] for j in m.f]
            x = m(x)
            y.append(x if m.i in self.save else None)
        f = self.head.f
        return [x if j == -1 else y[j] for j in f]

    def forward(self, images: torch.Tensor, proposal_pe: torch.Tensor):
        head = self.head
        feats = self._head_inputs(images)
        n = len(feats)
        pe = F.normalize(proposal_pe, dim=-1)  # (1,8,512)
        reg = torch.cat(
            [head.one2one_cv2[i](feats[i]).view(1, 4 * head.reg_max, -1) for i in range(n)], -1
        )
        dbox = (
            self._dist2bbox(head.dfl(reg), self.anchors, xywh=False, dim=1) * self.strides
        )  # (1,4,A)
        bn, scale = [], []
        for i in range(n):
            c = head.one2one_cv4[i]
            bn.append(c.norm(head.one2one_cv3[i](feats[i])).flatten(2))  # (1,512,hw)
            scale.append(c.logit_scale.exp().expand(self.level_sizes[i]))
        bn = torch.cat(bn, 2)  # (1,512,A)
        sc = torch.cat(scale, 0)[None]  # (1,A)
        bias = torch.cat(
            [head.one2one_cv4[i].bias.expand(self.level_sizes[i]) for i in range(n)], 0
        )[None]
        norm = bn.norm(dim=1)  # (1,A)
        logits = torch.einsum("bca,bkc->bka", bn, pe) * sc[:, None] + bias[:, None]  # (1,8,A)
        obj = torch.sigmoid(logits).max(dim=1).values  # (1,A)
        score, idx = torch.topk(obj, TOPK, dim=1)  # (1,100)
        ib = idx[:, :, None]
        boxes = dbox.transpose(1, 2).gather(1, ib.expand(-1, -1, 4))
        bn_t = bn.transpose(1, 2)  # (1,A,512)
        fp = F.normalize(bn_t.gather(1, ib.expand(-1, -1, bn_t.shape[-1])), dim=-1)
        fp_scale = (norm * sc).gather(1, idx)
        fp_bias = bias.gather(1, idx)
        return boxes, score, fp, fp_scale, fp_bias


class TextWrapper(nn.Module):
    """MobileCLIP2-B TorchScript text encoder + the head's `reprta`, L2 -> same as get_text_pe."""

    def __init__(self, encoder: nn.Module, reprta: nn.Module) -> None:
        super().__init__()
        self.encoder = encoder
        self.reprta = reprta

    def forward(self, input_ids: torch.Tensor):
        return F.normalize(self.reprta(self.encoder(input_ids)), dim=-1)
