"""Generate the soft outro music: a calm chord progression (pad, bells, bass), synthesised from sine waves.

Original, made by this script, so there are no licensing questions. make_video.py mixes it under the last
shot (the documentation) and fades it out as the closing voice starts.

  python3 music.py        -> music/outro.wav   (needs numpy; the `gpu` container's ~/.venvs/tts has it)
"""

from __future__ import annotations

import subprocess
import wave
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
RATE = 48_000
CHORD_SECONDS = 4.0

# MIDI note numbers. Fmaj7 - Cmaj7/E - Dm7 - Cmaj7 - Fmaj7 - Am7 - Dm7 - G(sus)
PROGRESSION = [
    [53, 57, 60, 64], [52, 55, 59, 60], [50, 53, 57, 60], [48, 52, 55, 59],
    [53, 57, 60, 64], [45, 52, 55, 60], [50, 53, 57, 60], [43, 50, 55, 60],
]


def hz(note: int) -> float:
    return 440.0 * 2 ** ((note - 69) / 12)


def envelope(n: int, attack: float, release: float) -> np.ndarray:
    env = np.ones(n)
    a, r = int(attack * RATE), int(release * RATE)
    env[:a] = np.linspace(0, 1, a) ** 2
    env[-r:] *= np.linspace(1, 0, r) ** 2
    return env


def render() -> np.ndarray:
    total = int((len(PROGRESSION) * CHORD_SECONDS + 3) * RATE)
    out = np.zeros(total)
    for i, chord in enumerate(PROGRESSION):
        start = int(i * CHORD_SECONDS * RATE)
        # Pad: each note as two slightly detuned sines, overlapping into the next chord.
        n = int((CHORD_SECONDS + 1.5) * RATE)
        t = np.arange(n) / RATE
        env = envelope(n, 1.2, 1.8)
        for note in chord:
            f = hz(note)
            out[start:start + n] += 0.07 * env * (np.sin(2 * np.pi * f * t) + np.sin(2 * np.pi * f * 1.003 * t))
        # Bass: the root an octave down.
        out[start:start + n] += 0.12 * env * np.sin(2 * np.pi * hz(chord[0] - 12) * t)
        # Bells: the chord an octave up, as a slow arpeggio (one note every half second).
        for k in range(int(CHORD_SECONDS / 0.5)):
            note = chord[[0, 2, 1, 3, 2, 1, 3, 2][k % 8]] + 12
            b0 = start + int(k * 0.5 * RATE)
            m = int(1.6 * RATE)
            tb = np.arange(m) / RATE
            bell = (np.sin(2 * np.pi * hz(note) * tb) + 0.25 * np.sin(2 * np.pi * hz(note) * 2 * tb)) * np.exp(-tb * 2.6)
            out[b0:b0 + m] += 0.05 * bell * np.minimum(1, tb * 200)
    out /= np.max(np.abs(out)) * 1.1
    return out


def main() -> None:
    folder = HERE / "music"
    folder.mkdir(exist_ok=True)
    dry = folder / "outro-dry.wav"
    with wave.open(str(dry), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((render() * 32767).astype(np.int16).tobytes())
    ffmpeg = ["ffmpeg"] if subprocess.run(["which", "ffmpeg"], capture_output=True).returncode == 0 else ["distrobox-host-exec", "ffmpeg"]
    # A little room reverb and a soft top end, in stereo.
    subprocess.run([*ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(dry), "-af",
                    "aecho=0.8:0.6:70|140|230:0.35|0.25|0.15,lowpass=f=5000,aformat=channel_layouts=stereo",
                    str(folder / "outro.wav")], check=True)
    print(folder / "outro.wav")


if __name__ == "__main__":
    main()
