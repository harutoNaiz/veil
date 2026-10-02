"""Qualcomm AI Hub checks: account set up, 8 Elite Gen 5 devices listed, and a tiny profile job.

The API token is never read or printed here: it lives in ~/.qai_hub/client.ini (or the file
QAIHUB_CLIENT_INI environment variable), written by `qai-hub configure`.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

FAMILY_RE = re.compile(r"8[\s_-]*elite[\s_-]*gen[\s_-]*5|sm8850", re.I)
TINY_MODEL_NAME = "veil-1.1-bench-tiny"


def is_configured() -> bool:
    """True when a client.ini exists. It says nothing about whether the token is still valid."""
    return Path(os.environ.get("QAIHUB_CLIENT_INI", "~/.qai_hub/client.ini")).expanduser().exists()


def family_devices() -> list[str]:
    """Sorted names of AI Hub devices whose name or an attribute is the 8 Elite Gen 5 family."""
    import qai_hub as hub  # imported late: it is slow to import and needs the client file

    names: set[str] = set()
    for device in hub.get_devices():
        haystack = [device.name, *list(device.attributes)]
        if any(FAMILY_RE.search(item) for item in haystack):
            names.add(device.name)
    return sorted(names)


def make_tiny_onnx(path: Path) -> None:
    """Write a tiny ONNX model: x [1,3,32,32] -> Conv(8 filters 3x3) -> Relu -> y [1,8,32,32]."""
    import numpy as np
    import onnx
    from onnx import TensorProto, helper, numpy_helper

    rng = np.random.default_rng(0)
    weights = (rng.standard_normal((8, 3, 3, 3)) * 0.1).astype(np.float32)
    bias = np.zeros(8, dtype=np.float32)
    graph = helper.make_graph(
        [
            helper.make_node(
                "Conv", ["x", "w", "b"], ["c"], kernel_shape=[3, 3], pads=[1, 1, 1, 1]
            ),
            helper.make_node("Relu", ["c"], ["y"]),
        ],
        "veil_tiny",
        [helper.make_tensor_value_info("x", TensorProto.FLOAT, [1, 3, 32, 32])],
        [helper.make_tensor_value_info("y", TensorProto.FLOAT, [1, 8, 32, 32])],
        initializer=[numpy_helper.from_array(weights, "w"), numpy_helper.from_array(bias, "b")],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])
    model.ir_version = 10
    onnx.checker.check_model(model)
    path.parent.mkdir(parents=True, exist_ok=True)
    onnx.save(model, str(path))


def tiny_profile(device_name: str, workdir: Path, timeout_s: int = 1800) -> dict:
    """Compile the tiny model for `device_name`, profile it on a real device and return the numbers.

    Tries TFLite first and QNN DLC if that compile fails. Uploads only the synthetic tiny model.
    """
    import qai_hub as hub

    onnx_path = workdir / "tiny.onnx"
    make_tiny_onnx(onnx_path)
    device = hub.Device(device_name)
    compile_job = None
    runtime = ""
    for runtime in ("tflite", "qnn_dlc"):
        compile_job = hub.submit_compile_job(
            model=str(onnx_path),
            device=device,
            name=TINY_MODEL_NAME,
            options=f"--target_runtime {runtime}",
        )
        compile_job.wait()
        if compile_job.get_status().success:
            break
    assert compile_job is not None
    if not compile_job.get_status().success:
        raise RuntimeError(f"AI Hub compile failed for tflite and qnn_dlc: {compile_job.url}")
    target = compile_job.get_target_model()
    profile_job = hub.submit_inference_job(
        model=target, device=device, profile=True, name=TINY_MODEL_NAME
    )
    profile_job.wait(timeout=timeout_s)
    if not profile_job.get_status().success:
        raise RuntimeError(f"AI Hub profile job did not succeed: {profile_job.url}")
    profile = profile_job.download_profile()
    return {
        "device": device_name,
        "compileJobId": compile_job.job_id,
        "profileJobId": profile_job.job_id,
        "targetRuntime": runtime,
        "estimatedInferenceTimeUs": profile["execution_summary"]["estimated_inference_time"],
        "url": profile_job.url,
    }
