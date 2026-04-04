"""
Argparse definitions and dispatch for PVRR subcommands (vectorize, video-to-mp3, video-to-wav).
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from pvrr.piano_vectorize_pipeline import resolve_target_bpm, run_vectorize_pipeline
from pvrr.video_audio_extract import convert_video_to_mp3, convert_video_to_wav


def _default_mp3_path(input_video: Path) -> Path:
    return Path("output/audio") / f"{input_video.stem}.mp3"


def _default_wav_path(input_video: Path) -> Path:
    return Path("output/audio") / f"{input_video.stem}.wav"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pvrr",
        description="Piano Vectorizer & Re-Renderer — audio/MIDI/video CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    vectorize = subparsers.add_parser(
        "vectorize",
        help="Audio -> MIDI vectorization -> tempo/quantize -> re-render WAV",
    )
    vectorize.add_argument("--input-audio", type=Path, required=True, help="Input audio file.")
    vectorize.add_argument(
        "--vector-mid",
        type=Path,
        default=Path("output/midi/original_piano.mid"),
        help="Output MIDI from Basic Pitch.",
    )
    vectorize.add_argument(
        "--adjusted-mid",
        type=Path,
        default=Path("output/midi/adjusted.mid"),
        help="Tempo-adjusted + quantized MIDI path.",
    )
    vectorize.add_argument("--soundfont", type=Path, required=True, help="Path to piano .sf2 file.")
    vectorize.add_argument(
        "--output-wav",
        type=Path,
        default=Path("output/audio/final_accompaniment_BPM.wav"),
        help="Rendered WAV output path.",
    )
    vectorize.add_argument(
        "--target-bpm",
        type=float,
        default=None,
        help="Target BPM. If omitted, use --speed-ratio for automatic BPM scaling.",
    )
    vectorize.add_argument(
        "--speed-ratio",
        type=float,
        default=None,
        help="Target speed ratio based on estimated source BPM. 0.5 = half speed.",
    )
    vectorize.add_argument(
        "--preserve-midi-tempo",
        action="store_true",
        help="Keep Basic Pitch tempo in the MIDI; do not replace with estimated BPM.",
    )
    vectorize.add_argument(
        "--no-quantize",
        action="store_true",
        help="Disable rhythmic quantization so note onsets/durations stay as detected.",
    )
    vectorize.add_argument(
        "--quantize-division",
        type=int,
        default=16,
        help="Grid division per 4/4 bar. 16 means 1/16-note quantization.",
    )
    vectorize.add_argument("--sample-rate", type=int, default=44100, help="Output render sample rate.")

    video_to_mp3 = subparsers.add_parser(
        "video-to-mp3",
        help="Extract MP3 audio from video (e.g. mp4)",
    )
    video_to_mp3.add_argument("--input-video", type=Path, required=True, help="Input video path.")
    video_to_mp3.add_argument(
        "--output-mp3",
        type=Path,
        default=None,
        help="Output MP3 path. Default: output/audio/<video_stem>.mp3",
    )
    video_to_mp3.add_argument("--bitrate", type=str, default="192k", help="MP3 bitrate, e.g. 128k/192k/320k.")
    video_to_mp3.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite output file if exists.",
    )

    video_to_wav = subparsers.add_parser(
        "video-to-wav",
        help="Extract lossless PCM WAV from video (better for transcription than MP3).",
    )
    video_to_wav.add_argument("--input-video", type=Path, required=True, help="Input video path.")
    video_to_wav.add_argument(
        "--output-wav",
        type=Path,
        default=None,
        help="Output WAV path. Default: output/audio/<video_stem>.wav",
    )
    video_to_wav.add_argument("--sample-rate", type=int, default=44100, help="Audio sample rate.")
    video_to_wav.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite output file if exists.",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "vectorize":
        target_bpm = resolve_target_bpm(
            input_audio=args.input_audio,
            target_bpm=args.target_bpm,
            speed_ratio=args.speed_ratio,
            preserve_midi_tempo=args.preserve_midi_tempo,
        )
        quantize_division = 0 if args.no_quantize else args.quantize_division
        run_vectorize_pipeline(
            input_audio=args.input_audio,
            vector_mid=args.vector_mid,
            adjusted_mid=args.adjusted_mid,
            soundfont_sf2=args.soundfont,
            output_wav=args.output_wav,
            target_bpm=target_bpm,
            quantize_division=quantize_division,
            sample_rate=args.sample_rate,
        )
        print(f"[OK] MIDI vector map: {args.vector_mid}")
        print(f"[OK] Adjusted MIDI: {args.adjusted_mid}")
        print(f"[OK] Rendered WAV: {args.output_wav}")
        return

    if args.command == "video-to-mp3":
        output_mp3 = args.output_mp3 or _default_mp3_path(args.input_video)
        convert_video_to_mp3(
            input_video=args.input_video,
            output_mp3=output_mp3,
            bitrate=args.bitrate,
            overwrite=args.overwrite,
        )
        print(f"[OK] MP3 output: {output_mp3}")
        return

    if args.command == "video-to-wav":
        output_wav = args.output_wav or _default_wav_path(args.input_video)
        convert_video_to_wav(
            input_video=args.input_video,
            output_wav=output_wav,
            sample_rate=args.sample_rate,
            overwrite=args.overwrite,
        )
        print(f"[OK] WAV output: {output_wav}")
        return

    raise RuntimeError(f"Unknown command: {args.command}")
