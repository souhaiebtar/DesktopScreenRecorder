import os
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import soundcard as sc
import soundfile as sf
from screeninfo import get_monitors

SAMPLERATE = 48000
BLOCKSIZE = 1024

running = True
mic_chunks = []
sys_chunks = []


def find_speaker(name_part):
    for s in sc.all_speakers():
        if name_part.lower() in s.name.lower():
            return s
    raise RuntimeError(
        f'Speaker containing "{name_part}" not found. '
        f'Available: {[s.name for s in sc.all_speakers()]}'
    )


def find_microphone(name_part):
    for m in sc.all_microphones():
        if name_part.lower() in m.name.lower():
            return m
    raise RuntimeError(
        f'Microphone containing "{name_part}" not found. '
        f'Available: {[m.name for m in sc.all_microphones()]}'
    )


def choose_monitor():
    monitors = get_monitors()

    if not monitors:
        raise RuntimeError("No monitors detected.")

    print("\nAvailable monitors:")
    for i, m in enumerate(monitors):
        print(f"  [{i}] {m.name} | {m.width}x{m.height} | x={m.x}, y={m.y}")

    while True:
        choice = input("\nEnter monitor index to record: ").strip()
        try:
            idx = int(choice)
            if 0 <= idx < len(monitors):
                return monitors[idx], idx
            print(f"Invalid index. Choose a value between 0 and {len(monitors) - 1}.")
        except ValueError:
            print("Please enter a valid integer.")


def record_microphone(mic_name_part="Jabra"):
    global running, mic_chunks
    mic = find_microphone(mic_name_part)
    print(f"Using microphone: {mic.name}")

    with mic.recorder(samplerate=SAMPLERATE, channels=1) as rec:
        while running:
            data = rec.record(numframes=BLOCKSIZE)
            mic_chunks.append(data.copy())


def record_system_audio(speaker_name_part="Jabra"):
    global running, sys_chunks
    speaker = find_speaker(speaker_name_part)
    print(f"Using speaker loopback: {speaker.name}")

    loopback = sc.get_microphone(speaker.name, include_loopback=True)

    with loopback.recorder(samplerate=SAMPLERATE, channels=2) as rec:
        while running:
            data = rec.record(numframes=BLOCKSIZE)
            sys_chunks.append(data.copy())


def start_screen_recording(output_file, monitor, fps=30):
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel", "error",
        "-f", "gdigrab",
        "-framerate", str(fps),
        "-offset_x", str(monitor.x),
        "-offset_y", str(monitor.y),
        "-video_size", f"{monitor.width}x{monitor.height}",
        "-i", "desktop",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        str(output_file)
    ]

    return subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True
    )


def save_audio_file(filename, chunks, samplerate, channels):
    if chunks:
        audio = np.concatenate(chunks, axis=0)
    else:
        audio = np.empty((0, channels), dtype=np.float32)
    sf.write(filename, audio, samplerate)


def safe_delete(path):
    try:
        if Path(path).exists():
            Path(path).unlink()
    except Exception:
        pass


def main():
    global running, mic_chunks, sys_chunks

    monitor, monitor_index = choose_monitor()

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_dir = Path.cwd() / "recordings"
    out_dir.mkdir(parents=True, exist_ok=True)

    video_file = out_dir / f"screen_monitor{monitor_index}_{timestamp}.mp4"
    mic_file = out_dir / f"jabra_mic_{timestamp}.wav"
    sys_file = out_dir / f"jabra_system_{timestamp}.wav"
    mixed_audio_file = out_dir / f"mixed_audio_{timestamp}.wav"
    final_file = out_dir / f"desktop_jabra_monitor{monitor_index}_{timestamp}.mp4"

    temp_files = [video_file, mic_file, sys_file, mixed_audio_file]

    mic_chunks = []
    sys_chunks = []
    running = True

    print("\nRecording configuration:")
    print(f"  Monitor   : [{monitor_index}] {monitor.name}")
    print(f"  Geometry  : {monitor.width}x{monitor.height} at x={monitor.x}, y={monitor.y}")
    print(f"  Output    : {final_file}")
    print("\nPress ENTER to stop recording.\n")

    screen_proc = start_screen_recording(video_file, monitor, fps=30)

    mic_thread = threading.Thread(target=record_microphone, args=("Jabra",), daemon=True)
    sys_thread = threading.Thread(target=record_system_audio, args=("Jabra",), daemon=True)

    mic_thread.start()
    sys_thread.start()

    try:
        input()
    finally:
        running = False
        time.sleep(1.0)

        if screen_proc.poll() is None and screen_proc.stdin:
            try:
                screen_proc.stdin.write("q\n")
                screen_proc.stdin.flush()
            except Exception:
                pass
            screen_proc.wait()

    save_audio_file(mic_file, mic_chunks, SAMPLERATE, 1)
    save_audio_file(sys_file, sys_chunks, SAMPLERATE, 2)

    subprocess.run([
        "ffmpeg",
        "-y",
        "-loglevel", "error",
        "-i", str(mic_file),
        "-i", str(sys_file),
        "-filter_complex",
        "[0:a]volume=1.5[m];[1:a]volume=1.0[s];[m][s]amix=inputs=2:duration=longest:dropout_transition=2[aout]",
        "-map", "[aout]",
        str(mixed_audio_file)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    subprocess.run([
        "ffmpeg",
        "-y",
        "-loglevel", "error",
        "-i", str(video_file),
        "-i", str(mixed_audio_file),
        "-c:v", "copy",
        "-c:a", "aac",
        str(final_file)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    for f in temp_files:
        safe_delete(f)

    print("Recording finished successfully.")
    print(f"Final file: {final_file.resolve()}")


if __name__ == "__main__":
    main()
