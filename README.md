# Audio Vector Workflow (Basic Pitch + Mido + FluidSynth)

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

## Project layout

```text
PVRR/
├── audio_vector_workflow.py
├── requirements.txt
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

## 3) Run end-to-end pipeline

```bash
python3 audio_vector_workflow.py \
  --input-wav input/original_piano.wav \
  --vector-mid output/midi/original_piano.mid \
  --adjusted-mid output/midi/adjusted.mid \
  --soundfont soundfonts/piano_library.sf2 \
  --output-wav output/audio/final_accompaniment_BPM.wav \
  --target-bpm 92 \
  --quantize-division 16
```

Or use automatic BPM estimation + speed ratio (e.g. half speed):

```bash
python3 audio_vector_workflow.py \
  --input-wav input/original_piano.wav \
  --soundfont soundfonts/piano_library.sf2 \
  --vector-mid output/midi/original_piano.mid \
  --adjusted-mid output/midi/half_speed.mid \
  --output-wav output/audio/half_speed.wav \
  --speed-ratio 0.5
```

## 4) What this script does

1. Uses Spotify Basic Pitch (CNN encoder) to extract polyphonic MIDI with onset and velocity.
2. Rewrites MIDI `set_tempo` to match `TARGET_BPM` (microseconds per beat).
3. Quantizes note events to a 1/16 grid (`quantize-division=16`) to remove extraction jitter.
4. Re-synthesizes adjusted MIDI via FluidSynth + your `.sf2` piano library.
