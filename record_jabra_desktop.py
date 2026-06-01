import subprocess
import threading
import time
import os
from datetime import datetime

import numpy as np
import soundcard as sc
import soundfile as sf

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


def start_screen_recording(output_file="screen.mp4", fps=30):
    cmd = [
        "ffmpeg",
        "-y",
        "-f", "gdigrab",
        "-framerate", str(fps),
        "-i", "desktop",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        output_file
    ]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE, text=True)


def save_audio_file(filename, chunks, samplerate, channels):
    if chunks:
        audio = np.concatenate(chunks, axis=0)
    else:
        audio = np.empty((0, channels), dtype=np.float32)
    sf.write(filename, audio, samplerate)
    print(f"Saved {filename}")


def safe_delete(path):
    if os.path.exists(path):
        try:
            os.remove(path)
            print(f"Deleted temporary file: {path}")
        except Exception as e:
            print(f"Warning: could not delete {path}: {e}")


def main():
    global running, mic_chunks, sys_chunks

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    video_file = f"screen_{timestamp}.mp4"
    mic_file = f"jabra_mic_{timestamp}.wav"
    sys_file = f"jabra_system_{timestamp}.wav"
    mixed_audio_file = f"mixed_audio_{timestamp}.wav"
    final_file = f"desktop_jabra_final_{timestamp}.mp4"

    temp_files = [video_file, mic_file, sys_file, mixed_audio_file]

    # Reset buffers in case script structure evolves
    mic_chunks = []
    sys_chunks = []
    running = True

    screen_proc = start_screen_recording(video_file, fps=30)

    mic_thread = threading.Thread(target=record_microphone, args=("Jabra",), daemon=True)
    sys_thread = threading.Thread(target=record_system_audio, args=("Jabra",), daemon=True)

    mic_thread.start()
    sys_thread.start()

    try:
        input(f"Recording desktop + Jabra mic + Jabra system audio...\nOutput will be: {final_file}\nPress Enter to stop.\n")
    finally:
        running = False
        time.sleep(1.0)

        if screen_proc.poll() is None and screen_proc.stdin:
            screen_proc.stdin.write("q\n")
            screen_proc.stdin.flush()
            screen_proc.wait()

    save_audio_file(mic_file, mic_chunks, SAMPLERATE, 1)
    save_audio_file(sys_file, sys_chunks, SAMPLERATE, 2)

    subprocess.run([
        "ffmpeg",
        "-y",
        "-i", mic_file,
        "-i", sys_file,
        "-filter_complex",
        "[0:a]volume=1.5[m];[1:a]volume=1.0[s];[m][s]amix=inputs=2:duration=longest:dropout_transition=2[aout]",
        "-map", "[aout]",
        mixed_audio_file
    ], check=True)

    subprocess.run([
        "ffmpeg",
        "-y",
        "-i", video_file,
        "-i", mixed_audio_file,
        "-c:v", "copy",
        "-c:a", "aac",
        final_file
    ], check=True)

    print(f"\nDone. Final file: {final_file}")

    # Cleanup temporary files only after success
    for f in temp_files:
        safe_delete(f)


if __name__ == "__main__":
    main()
