"""Working copy of a recording: scale to width 360, pad (black, bottom) or crop to height 800."""

from __future__ import annotations

import subprocess
from pathlib import Path


def downscale(src: Path, dst: Path, width: int = 360, height: int = 800) -> Path:
    vf = f"scale={width}:-2,pad={width}:max({height}\\,ih):0:0:black,crop={width}:{height}:0:0"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-vf", vf]
    cmd += ["-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-pix_fmt", "yuv420p"]
    cmd.append(str(dst))
    subprocess.run(cmd, check=True)
    return Path(dst)
