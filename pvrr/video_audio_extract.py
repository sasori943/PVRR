"""
Extract audio from video containers via ffmpeg (MP3 or lossless WAV).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def convert_video_to_mp3(
    input_video: Path,
    output_mp3: Path,
    bitrate: str = "192k",
    overwrite: bool = False,
) -> None:
    """
    Extract audio track from a video file and encode it as MP3.
    Requires ffmpeg.
    """
    if not input_video.exists():
        raise FileNotFoundError(f"Input video not found: {input_video}")

    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        raise RuntimeError(
            "ffmpeg is required for video-to-mp3 conversion. "
            "Install with: brew install ffmpeg"
        )

    output_mp3.parent.mkdir(parents=True, exist_ok=True)
    overwrite_flag = "-y" if overwrite else "-n"

    cmd = [
        ffmpeg_bin,
        overwrite_flag,
        "-i",
        str(input_video),
        "-vn",
        "-acodec",
        "libmp3lame",
        "-b:a",
        bitrate,
        str(output_mp3),
    ]
    subprocess.run(cmd, check=True)


def convert_video_to_wav(
    input_video: Path,
    output_wav: Path,
    sample_rate: int = 44100,
    overwrite: bool = False,
) -> None:
    """
    Extract audio from video as 16-bit PCM WAV (lossless container, no MP3 artifacts).
    Requires ffmpeg.
    """
    if not input_video.exists():
        raise FileNotFoundError(f"Input video not found: {input_video}")

    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        raise RuntimeError(
            "ffmpeg is required for video-to-wav conversion. "
            "Install with: brew install ffmpeg"
        )

    output_wav.parent.mkdir(parents=True, exist_ok=True)
    overwrite_flag = "-y" if overwrite else "-n"

    cmd = [
        ffmpeg_bin,
        overwrite_flag,
        "-i",
        str(input_video),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        str(sample_rate),
        "-ac",
        "1",
        str(output_wav),
    ]
    subprocess.run(cmd, check=True)
