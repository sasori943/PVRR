# Audio Vector Workflow (Basic Pitch + Mido + FluidSynth)

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
- `original_piano.wav`
- `piano_library.sf2`

## 3) Run end-to-end pipeline

```bash
python3 audio_vector_workflow.py \
  --input-wav original_piano.wav \
  --vector-mid original_piano.mid \
  --adjusted-mid adjusted.mid \
  --soundfont piano_library.sf2 \
  --output-wav final_accompaniment_BPM.wav \
  --target-bpm 92 \
  --quantize-division 16
```

## 4) What this script does

1. Uses Spotify Basic Pitch (CNN encoder) to extract polyphonic MIDI with onset and velocity.
2. Rewrites MIDI `set_tempo` to match `TARGET_BPM` (microseconds per beat).
3. Quantizes note events to a 1/16 grid (`quantize-division=16`) to remove extraction jitter.
4. Re-synthesizes adjusted MIDI via FluidSynth + your `.sf2` piano library.
