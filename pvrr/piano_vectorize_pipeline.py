"""
Piano audio → MIDI (Basic Pitch) → optional tempo / quantization → WAV (FluidSynth).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import mido
from mido import Message, MetaMessage, MidiTrack


def estimate_bpm_from_audio(input_audio: Path) -> float:
    """Estimate source BPM from audio using librosa beat tracking."""
    try:
        import librosa
    except Exception as exc:
        raise RuntimeError(
            "Automatic BPM estimation requires librosa. Install dependencies first."
        ) from exc

    y, sr = librosa.load(str(input_audio), sr=None, mono=True)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    bpm = float(tempo.item() if hasattr(tempo, "item") else tempo)
    if bpm <= 0:
        raise RuntimeError("Failed to estimate BPM from input audio.")
    return bpm


def resolve_target_bpm(
    input_audio: Path,
    target_bpm: float | None,
    speed_ratio: float | None,
    preserve_midi_tempo: bool = False,
) -> float | None:
    """
    Resolve target BPM for rewriting MIDI set_tempo, or None to keep Basic Pitch tempo.

    When preserve_midi_tempo is True, returns None (no librosa-based tempo overwrite).
    Otherwise requires --target-bpm or --speed-ratio.
    """
    if preserve_midi_tempo:
        if target_bpm is not None or speed_ratio is not None:
            print(
                "[INFO] --preserve-midi-tempo: not rewriting MIDI tempo; "
                "--target-bpm / --speed-ratio are ignored for the MIDI file."
            )
        return None

    if target_bpm is not None:
        if target_bpm <= 0:
            raise ValueError("--target-bpm must be > 0.")
        if speed_ratio is not None:
            print("[INFO] --target-bpm is provided; --speed-ratio is ignored.")
        return target_bpm

    if speed_ratio is None:
        raise ValueError("Provide either --target-bpm or --speed-ratio, or use --preserve-midi-tempo.")
    if speed_ratio <= 0:
        raise ValueError("--speed-ratio must be > 0.")

    source_bpm = estimate_bpm_from_audio(input_audio)
    target = source_bpm * speed_ratio
    print(f"[INFO] Estimated source BPM: {source_bpm:.2f}")
    print(f"[INFO] Target BPM (source * ratio): {target:.2f}")
    return target


def _is_note_off(msg: Message) -> bool:
    return msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0)


def _quantize_tick(abs_tick: int, grid_step: int) -> int:
    if grid_step <= 0:
        return abs_tick
    return int(round(abs_tick / grid_step) * grid_step)


def _track_to_absolute(track: MidiTrack) -> List[Tuple[int, int, Message]]:
    abs_tick = 0
    items: List[Tuple[int, int, Message]] = []
    for idx, msg in enumerate(track):
        abs_tick += msg.time
        items.append((abs_tick, idx, msg.copy()))
    return items


def _absolute_to_track(items: Iterable[Tuple[int, int, Message]]) -> MidiTrack:
    sorted_items = sorted(
        items,
        key=lambda x: (
            x[0],
            0 if _is_note_off(x[2]) else 1 if x[2].type == "note_on" else 2,
            x[1],
        ),
    )
    track = MidiTrack()
    prev_tick = 0
    for abs_tick, _, msg in sorted_items:
        delta = max(0, abs_tick - prev_tick)
        msg.time = delta
        track.append(msg)
        prev_tick = abs_tick
    return track


def extract_midi_with_basic_pitch(input_audio: Path, output_mid: Path) -> None:
    """Use Spotify Basic Pitch (CNN) for note/onset/velocity extraction."""
    output_mid.parent.mkdir(parents=True, exist_ok=True)

    try:
        from basic_pitch.inference import predict
    except Exception:
        predict = None

    if predict is not None:
        _, midi_data, _ = predict(str(input_audio))
        midi_data.write(str(output_mid))
        return

    if shutil.which("basic-pitch") is None:
        raise RuntimeError(
            "basic-pitch is not importable and CLI binary is missing. "
            "Please install `basic-pitch` in the active environment."
        )

    tmp_dir = output_mid.parent / "_bp_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["basic-pitch", str(tmp_dir), str(input_audio)], check=True)

    midi_candidates = sorted(tmp_dir.glob("*.mid"), key=lambda p: p.stat().st_mtime)
    if not midi_candidates:
        raise RuntimeError("Basic Pitch finished but no MIDI file was generated.")

    midi_candidates[-1].replace(output_mid)


def adjust_midi_tempo_and_quantize(
    input_mid: Path,
    output_mid: Path,
    target_bpm: float | None,
    quantize_division: int | None = 16,
) -> None:
    """
    Optionally rewrite all set_tempo to target_bpm, and optionally quantize notes.

    If target_bpm is None, keep Basic Pitch / file tempo events unchanged.
    If quantize_division is None or 0, skip quantization (preserve micro-timing).
    """
    midi = mido.MidiFile(str(input_mid))
    ticks_per_beat = midi.ticks_per_beat
    do_tempo = target_bpm is not None
    tempo_us_per_beat = mido.bpm2tempo(target_bpm) if do_tempo else None
    do_quantize = quantize_division is not None and quantize_division > 0
    grid_step = (ticks_per_beat * 4 // quantize_division) if do_quantize else 0

    tempo_found = False
    new_tracks: List[MidiTrack] = []

    for old_track in midi.tracks:
        abs_items = _track_to_absolute(old_track)
        transformed: List[Tuple[int, int, Message]] = []
        open_notes: Dict[Tuple[int, int], List[Tuple[int, int, int]]] = {}

        for abs_tick, idx, msg in abs_items:
            new_abs_tick = abs_tick
            if do_quantize:
                if msg.type == "note_on" and msg.velocity > 0:
                    new_abs_tick = max(0, _quantize_tick(abs_tick, grid_step))
                    key = (msg.channel, msg.note)
                    open_notes.setdefault(key, []).append((abs_tick, new_abs_tick, idx))
                elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                    key = (msg.channel, msg.note)
                    note_stack = open_notes.get(key, [])
                    if note_stack:
                        start_abs, start_q, _ = note_stack.pop(0)
                        raw_duration = max(1, abs_tick - start_abs)
                        quantized_duration = max(grid_step, _quantize_tick(raw_duration, grid_step))
                        new_abs_tick = start_q + quantized_duration
                    else:
                        new_abs_tick = max(0, _quantize_tick(abs_tick, grid_step))

            if msg.type == "set_tempo":
                if do_tempo and tempo_us_per_beat is not None:
                    msg.tempo = tempo_us_per_beat
                tempo_found = True

            transformed.append((new_abs_tick, idx, msg))

        new_tracks.append(_absolute_to_track(transformed))

    if do_tempo and tempo_us_per_beat is not None and not tempo_found:
        if not new_tracks:
            new_tracks = [MidiTrack()]
        new_tracks[0].insert(0, MetaMessage("set_tempo", tempo=tempo_us_per_beat, time=0))

    out_midi = mido.MidiFile(ticks_per_beat=ticks_per_beat)
    out_midi.tracks.extend(new_tracks)
    output_mid.parent.mkdir(parents=True, exist_ok=True)
    out_midi.save(str(output_mid))


def render_with_fluidsynth(
    input_mid: Path, soundfont_sf2: Path, output_wav: Path, sample_rate: int = 44100
) -> None:
    """Render MIDI to WAV via FluidSynth."""
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    fluidsynth_bin = shutil.which("fluidsynth")
    if not fluidsynth_bin:
        raise RuntimeError("fluidsynth binary not found. Please install FluidSynth first.")

    cmd = [
        fluidsynth_bin,
        "-ni",
        "-F",
        str(output_wav),
        "-r",
        str(sample_rate),
        str(soundfont_sf2),
        str(input_mid),
    ]
    subprocess.run(cmd, check=True)


def run_vectorize_pipeline(
    input_audio: Path,
    vector_mid: Path,
    adjusted_mid: Path,
    soundfont_sf2: Path,
    output_wav: Path,
    target_bpm: float | None,
    quantize_division: int | None,
    sample_rate: int,
) -> None:
    extract_midi_with_basic_pitch(input_audio, vector_mid)
    adjust_midi_tempo_and_quantize(
        vector_mid, adjusted_mid, target_bpm=target_bpm, quantize_division=quantize_division
    )
    render_with_fluidsynth(adjusted_mid, soundfont_sf2, output_wav, sample_rate=sample_rate)
