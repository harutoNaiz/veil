"""Embedding engines for the bank build (torch describer or ONNX with a chosen provider) and the
bounded prefetch pipeline that overlaps downloads with embedding."""

from __future__ import annotations

import queue
import threading
from collections.abc import Callable, Iterable, Iterator
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

import numpy as np

from workshop.forge.siglip2.runtime import OnnxDescriber

BATCH = 16
PROVIDERS = {
    "cpu": ["CPUExecutionProvider"],
    "dml": ["DmlExecutionProvider", "CPUExecutionProvider"],
}


class FixedBatchOnnx(OnnxDescriber):
    """OnnxDescriber that always runs the static b16 image graph (pads the last batch to 16)."""

    def __init__(self, folder: Path, provider: str = "cpu", sessions=None, processor=None) -> None:
        super().__init__(folder, sessions=sessions, processor=processor)
        self.provider = provider

    def _session(self, key: str):
        if key not in self._sessions:
            import onnxruntime as ort

            if key == "text":
                name, prov = "siglip2-text.onnx", PROVIDERS[self.provider]
            else:
                name, prov = "siglip2-image-b16.onnx", PROVIDERS[self.provider]
            self._sessions[key] = ort.InferenceSession(str(self.folder / name), providers=prov)
        return self._sessions[key]

    def _run_chunk(self, pixels: np.ndarray) -> np.ndarray:
        n = pixels.shape[0]
        if n < BATCH:
            pixels = np.concatenate([pixels, np.repeat(pixels[-1:], BATCH - n, axis=0)], axis=0)
        out = self._session("b16").run(["fingerprint"], {"pixel_values": pixels})[0]
        return np.asarray(out)[:n]


def make_describer(engine: str, provider: str, onnx_dir: Path):
    if engine == "onnx":
        return FixedBatchOnnx(onnx_dir, provider)
    from workshop.twin.describer import Describer

    return Describer()


def prefetch(
    chunks: Iterable[list], fetch: Callable, threads: int = 32, depth: int = 4
) -> Iterator[tuple[list, list]]:
    """Yield (chunk, results) in order; downloads run at most `depth` chunks ahead."""
    q: queue.Queue = queue.Queue(maxsize=depth)
    stop = threading.Event()
    ex = ThreadPoolExecutor(threads)

    def produce() -> None:
        try:
            for ch in chunks:
                futs: list[Future] = [ex.submit(fetch, x) for x in ch]
                while not stop.is_set():
                    try:
                        q.put((ch, futs), timeout=0.2)
                        break
                    except queue.Full:
                        continue
                if stop.is_set():
                    return
        except BaseException:
            stop.set()
            raise
        while not stop.is_set():
            try:
                q.put(None, timeout=0.2)
                return
            except queue.Full:
                continue

    t = threading.Thread(target=produce, daemon=True)
    t.start()
    try:
        while (item := q.get()) is not None:
            ch, futs = item
            yield ch, [f.result() for f in futs]
    finally:
        stop.set()
        ex.shutdown(wait=False, cancel_futures=True)
