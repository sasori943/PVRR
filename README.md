# Piano Vectorizer & Re-Renderer

## Project name

**Piano Vectorizer & Re-Renderer**

## Why this name

The name describes the full pipeline:
- **Piano**: the target source is piano performance audio.
- **Vectorizer**: converts waveform audio into symbolic MIDI events (note, onset, velocity).
- **Re-Renderer**: synthesizes adjusted MIDI back to audio with a SoundFont via FluidSynth.

In short, this project does not do direct waveform stretching. It vectorizes first, then re-renders.

## 命名由来（中文）

项目名 **Piano Vectorizer & Re-Renderer** 对应完整技术路径：
- **Piano**：面向钢琴演奏音频。
- **Vectorizer**：将波形音频升维为 MIDI 符号事件（音高、起音、力度）。
- **Re-Renderer**：把调整后的 MIDI 通过 SoundFont + FluidSynth 重新渲染为音频。

核心思想是“先矢量化，再重渲染”，而不是直接对波形做时域拉伸。

## Python files（文件名与职责）

| File | Role |
|------|------|
| `pvrr_cli.py` | **Main CLI** — run subcommands (`vectorize`, `video-to-mp3`, `video-to-wav`). Same as `python -m pvrr`. |
| `legacy_vectorize_from_wav.py` | **Legacy** — old scripts that pass `--input-wav`; forwards to `vectorize --input-audio`. |
| `pvrr/__main__.py` | Module entry so **`python -m pvrr`** works. |
| `pvrr/command_line.py` | Argparse setup and subcommand dispatch. |
| `pvrr/piano_vectorize_pipeline.py` | Audio → Basic Pitch MIDI → optional tempo / quantize → FluidSynth WAV. |
| `pvrr/video_audio_extract.py` | ffmpeg wrappers: video → MP3 or lossless WAV. |

## Project layout

```text
PVRR/
├── pvrr_cli.py                 # primary CLI entry (or: python -m pvrr)
├── legacy_vectorize_from_wav.py
├── requirements.txt
├── pvrr/
│   ├── __init__.py
│   ├── __main__.py
│   ├── command_line.py
│   ├── piano_vectorize_pipeline.py
│   └── video_audio_extract.py
├── input/
├── soundfonts/
├── output/
│   ├── midi/
│   └── audio/
└── garageband/
```

## 1) Environment setup

```bash
# Rendering engine
brew install fluidsynth

# Python 3.10 env (if conda is available)
conda create -n audio_vector python=3.10 -y
conda activate audio_vector

# Python deps
pip install -r requirements.txt
```

## 2) Input files

Place files in this folder (or pass absolute paths):
- `input/original_piano.wav` (or `.mp3` / `.m4a`)
- `soundfonts/piano_library.sf2`

## 3) Command line usage

Use either **`python3 pvrr_cli.py`** or **`python3 -m pvrr`** (equivalent).

### A) Vectorize + tempo adjust + re-render

```bash
python3 pvrr_cli.py vectorize \
  --input-audio input/original_piano.wav \
  --vector-mid output/midi/original_piano.mid \
  --adjusted-mid output/midi/adjusted.mid \
  --soundfont soundfonts/piano_library.sf2 \
  --output-wav output/audio/final_accompaniment_BPM.wav \
  --target-bpm 92 \
  --quantize-division 16
```

Use automatic BPM estimation + speed ratio (e.g. half speed):

```bash
python3 -m pvrr vectorize \
  --input-audio input/original_piano.wav \
  --soundfont soundfonts/piano_library.sf2 \
  --vector-mid output/midi/original_piano.mid \
  --adjusted-mid output/midi/half_speed.mid \
  --output-wav output/audio/half_speed.wav \
  --speed-ratio 0.5
```

### B) Convert MP4 video to MP3

```bash
python3 pvrr_cli.py video-to-mp3 \
  --input-video input/sample.mp4 \
  --output-mp3 output/audio/sample.mp3 \
  --bitrate 192k \
  --overwrite
```

### C) Convert MP4 to lossless WAV (recommended before vectorize)

MP3 compression can blur transients and confuse pitch/onset detection. For transcription, prefer extracting PCM WAV from the video:

```bash
python3 pvrr_cli.py video-to-wav \
  --input-video input/sample.mp4 \
  --output-wav output/audio/sample.wav \
  --overwrite
```

Then run `vectorize` on the WAV. Optional flags to keep timing closer to the recording:

```bash
python3 pvrr_cli.py vectorize \
  --input-audio output/audio/sample.wav \
  --soundfont soundfonts/piano_library.sf2 \
  --preserve-midi-tempo \
  --no-quantize
```

### D) Legacy `--input-wav` wrapper

If an old script still uses `--input-wav`:

```bash
python3 legacy_vectorize_from_wav.py --input-wav input/old.wav --soundfont soundfonts/piano_library.sf2
```

This is equivalent to `pvrr_cli.py vectorize --input-audio input/old.wav …` (other flags pass through).

This command requires `ffmpeg`:

```bash
brew install ffmpeg
```

## 4) What the toolkit does

1. Uses Spotify Basic Pitch (CNN encoder) to extract polyphonic MIDI with onset and velocity.
2. Optionally rewrites MIDI `set_tempo` to match estimated or explicit BPM; use `--preserve-midi-tempo` to keep Basic Pitch’s tempo map.
3. Optionally quantizes note events to a grid (`--quantize-division`, default 16); use `--no-quantize` to keep detected micro-timing.
4. Re-synthesizes adjusted MIDI via FluidSynth + your `.sf2` piano library.
5. Converts video files to MP3 or lossless WAV via `ffmpeg`.
