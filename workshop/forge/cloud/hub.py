"""AI Hub client: Protocol, a fixture replayer, and a live wrapper (late qai_hub import)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

DEVICE = "Samsung Galaxy S26 (Family)"
FIXTURES = Path(__file__).parent / "fixtures" / "1"


def job_url(job_id: str, live: bool) -> str:
    return f"https://app.aihub.qualcomm.com/jobs/{job_id}/" if live else f"fixture://{job_id}"


class HubClient(Protocol):
    def compile(self, model_path: str, precision: str, batch: int) -> dict: ...
    def quantize(self, model_path: str, calib_dir: str, w: str, a: str) -> dict: ...
    def profile(self, job_target: str) -> dict: ...
    def inference(self, job_target: str, inputs: Any) -> dict: ...
    def link(self, targets: list[str]) -> dict: ...


class FixtureClient:
    """Replays fixtures/1/<modelId>/<precision>/{compile,profile,quantize}.json.

    `model_path` / `job_target` is "<modelId>/<precision>" (only its last two parts are used).
    """

    def __init__(self, root: Path | str = FIXTURES):
        self.root = Path(root)

    def _load(self, target: str, kind: str) -> dict:
        parts = str(target).replace("\\", "/").strip("/").split("/")
        path = self.root.joinpath(*parts[-2:], f"{kind}.json")
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def compile(self, model_path: str, precision: str, batch: int) -> dict:
        return self._load(f"{model_path}/{precision}", "compile")

    def quantize(self, model_path: str, calib_dir: str, w: str, a: str) -> dict:
        return self._load(f"{model_path}/{'w8a8' if a == 'int8' else 'w8a16'}", "quantize")

    def profile(self, job_target: str) -> dict:
        return self._load(job_target, "profile")

    def inference(self, job_target: str, inputs: Any) -> dict:
        return self._load(job_target, "inference")

    def link(self, targets: list[str]) -> dict:
        return {"jobId": "fixture-link", "url": "fixture://fixture-link", "status": "SUCCESS"}


class LiveClient:
    """Real AI Hub calls. Needs `qai-hub configure`; never run in verify."""

    def __init__(self, device: str = DEVICE):
        import qai_hub as hub  # late import: slow, needs the client file

        self.hub = hub
        self.device = hub.get_devices(name=device)[0]
        self._jobs: dict[str, Any] = {}

    def _ret(self, job: Any, **extra: Any) -> dict:
        self._jobs[job.job_id] = job
        return {
            "jobId": job.job_id,
            "url": job_url(job.job_id, True),
            "status": "SUBMITTED",
            **extra,
        }

    def compile(self, model_path: str, precision: str, batch: int) -> dict:
        model = (
            self._jobs[model_path].get_target_model() if model_path in self._jobs else model_path
        )
        options = "--target_runtime precompiled_qnn_onnx"
        if precision == "float16":
            options += " --quantize_full_type float16"
        job = self.hub.submit_compile_job(model=model, device=self.device, options=options)
        return self._ret(job)

    def quantize(self, model_path: str, calib_dir: str, w: str, a: str) -> dict:
        import numpy as np

        data = {"x": [np.load(p) for p in sorted(Path(calib_dir).glob("*.npy"))[:64]]}
        job = self.hub.submit_quantize_job(
            model=model_path,
            calibration_data=data,
            weights_dtype=_dtype(w),
            activations_dtype=_dtype(a),
        )
        return self._ret(job)

    def profile(self, job_target: str) -> dict:
        model = self._jobs[job_target].get_target_model()
        job = self.hub.submit_profile_job(model=model, device=self.device)
        job.wait()
        return self._ret(job, status="SUCCESS", profile=job.download_profile())

    def inference(self, job_target: str, inputs: Any) -> dict:
        model = self._jobs[job_target].get_target_model()
        job = self.hub.submit_inference_job(model=model, device=self.device, inputs=inputs)
        job.wait()
        return self._ret(job, status="SUCCESS", outputs=job.download_output_data())

    def link(self, targets: list[str]) -> dict:
        models = [self._jobs[t].get_target_model() for t in targets]
        job = self.hub.submit_link_job(models, device=self.device)
        return self._ret(job)


def _dtype(bits: str) -> Any:
    import qai_hub as hub

    return {"int8": hub.QuantizeDtype.INT8, "int16": hub.QuantizeDtype.INT16}[bits]


def get_client(live: bool) -> HubClient:
    return LiveClient() if live else FixtureClient()
