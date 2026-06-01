# recordSnd

Record a selected monitor on Windows and capture:

- screen video with `ffmpeg`
- microphone audio
- system audio loopback

The script then mixes the audio tracks and muxes them into a final `.mp4` file.

## Requirements

- Windows
- Conda
- `ffmpeg` available through the Conda environment
- A working microphone and speaker device
- Python packages listed in `environment.yml`

## Setup

Create the Conda environment:

```powershell
conda env create -f environment.yml
conda activate recordsnd
```

## Install file

This project uses `environment.yml` so Conda can install both Python dependencies and the native `ffmpeg` package.

## Run

```powershell
python .\record-desktop-with-selection-of-monitor.py
```

## How it works

1. Lists detected monitors
2. Prompts for the monitor index to record
3. Starts screen recording with `ffmpeg`
4. Records:
   - microphone audio
   - system loopback audio
5. Stops when ENTER is pressed
6. Mixes audio into one WAV file
7. Combines mixed audio with recorded video into a final MP4

## Output

Recordings are saved in:

```text
.\recordings\
```

Generated files include:

- temporary screen recording
- temporary microphone WAV
- temporary system-audio WAV
- temporary mixed-audio WAV
- final MP4 output

Temporary files are deleted after the final video is created.

## Notes

- The current script looks for device names containing `Jabra`.
- If device names differ, update these defaults in the script:
  - `record_microphone("Jabra")`
  - `record_system_audio("Jabra")`

## Troubleshooting

### `ffmpeg` not found

Make sure the Conda environment is activated:

```powershell
conda activate recordsnd
```

Then verify:

```powershell
ffmpeg -version
```

### No monitors detected

Check that Windows detects the displays and that the monitor is enabled.

### Audio device not found

The script matches devices by partial name. If `Jabra` does not match the actual device name, change it in the script.

## Main files

- `record-desktop-with-selection-of-monitor.py` — recording script
- `environment.yml` — Conda environment definition
