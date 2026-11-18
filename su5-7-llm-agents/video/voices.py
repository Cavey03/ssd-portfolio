"""Speak text with Kokoro-82M, a small open text-to-speech model (Apache 2.0), run locally.

Each "character" in the video has its own clearly different voice, so it is obvious the narration is AI:
the narrator, Mission Control, the fine-tuned router, Opus and the worker.

  distrobox enter gpu -- ~/.venvs/tts/bin/python voices.py --samples      -> samples/*.wav + samples/cast.wav
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
RATE = 24_000  # Kokoro's sample rate
# Kokoro runs in the `gpu` container, which has no ffmpeg: use the host's.
FFMPEG = ["ffmpeg"] if shutil.which("ffmpeg") else ["distrobox-host-exec", "ffmpeg"]

# role: (Kokoro voice, language code a = American / b = British, speed)
CAST = {
    "narrator": ("bm_george", "b", 1.0),
    "mission-control": ("af_nova", "a", 1.1),
    "router": ("am_puck", "a", 1.2),
    "opus": ("am_onyx", "a", 0.92),
    "worker": ("bf_lily", "b", 1.0),
}

SAMPLES = {
    "narrator": "This is Mission Control: one hub for all my coding agents, including a model that runs on my own GPU.",
    "mission-control": "Ollama started. Model loaded. GPU at nine point one gigabytes.",
    "router": "Local. Fifty milliseconds.",
    "opus": "I'll take this one. Worker: the local model. Time limit: ten minutes.",
    "worker": "Done. I added the option, and all tests pass.",
}

# A "robot" voice: the phase of every frequency is set to zero, which removes the natural pitch movement.
ROBOT_FILTER = "afftfilt=real='hypot(re,im)*sin(0)':imag='hypot(re,im)*cos(0)':win_size=512:overlap=0.75"


def speak(role: str, text: str, out: Path, device: str = "cpu") -> Path:
    """Write `text` in `role`'s voice to a WAV file."""
    import numpy as np
    import soundfile as sf
    from kokoro import KPipeline

    voice, lang, speed = CAST[role]
    pipeline = KPipeline(lang_code=lang, device=device)
    audio = np.concatenate([chunk for _, _, chunk in pipeline(text, voice=voice, speed=speed)])
    out.parent.mkdir(parents=True, exist_ok=True)
    sf.write(out, audio, RATE)
    return out


def robotize(src: Path, out: Path) -> Path:
    subprocess.run([*FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", str(src), "-af", ROBOT_FILTER, str(out)],
                   check=True)
    return out


def samples() -> None:
    folder = HERE / "samples"
    files = []
    for role, text in SAMPLES.items():
        files.append(speak(role, text, folder / f"{role}.wav"))
        print(f"{role:<16} {CAST[role][0]:<10} {files[-1]}")
    files.append(robotize(folder / "mission-control.wav", folder / "mission-control-robot.wav"))
    print(f"{'robot version':<16} {'':<10} {files[-1]}")
    # All of them in a row, with half a second between, to hear the cast together.
    gap = folder / "gap.wav"
    subprocess.run([*FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    f"anullsrc=r={RATE}:cl=mono", "-t", "0.6", str(gap)], check=True)
    listing = folder / "cast.txt"
    listing.write_text("".join(f"file '{f.name}'\nfile 'gap.wav'\n" for f in files))
    subprocess.run([*FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i",
                    str(listing), "-c:a", "pcm_s16le", str(folder / "cast.wav")], check=True)
    print(f"\nall together: {folder / 'cast.wav'}")


if __name__ == "__main__":
    if "--samples" in sys.argv:
        samples()
