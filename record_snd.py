import subprocess
import time

cmd = [
    "ffmpeg",
    "-y",
    "-f", "gdigrab",
    "-framerate", "30",
    "-i", "desktop",
    "-f", "dshow",
    "-i", "audio=External Microphone (Realtek(R) Audio)",
    "-f", "dshow",
    "-i", "audio=Stereo Mix (Realtek(R) Audio)",
    "-filter_complex", "[1:a][2:a]amix=inputs=2:duration=longest[aout]",
    "-map", "0:v",
    "-map", "[aout]",
    "-c:v", "libx264",
    "-c:a", "aac",
    "desktop_mic_system.mp4"
]

p = subprocess.Popen(cmd, stdin=subprocess.PIPE, text=True)

time.sleep(2)

if p.poll() is not None:
    print("ffmpeg exited early. Check device names or ffmpeg output.")
else:
    try:
        input("Recording... Press Enter to stop.\n")
    finally:
        if p.poll() is None and p.stdin:
            p.stdin.write("q\n")
            p.stdin.flush()
            p.wait()
