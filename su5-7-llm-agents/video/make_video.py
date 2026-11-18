"""Build the intro video from raw screen recordings: captions, narration, speed-ups, title and end cards.

1. Record each shot as its own clip (Spectacle: New Screen Recording), in the order of SHOTS below.
2. Put the clips in video/clips/ (any names: they are taken in recording order, i.e. sorted by name, which
   Spectacle's date-time names already are).
3. Narration (optional): `voices.py` writes narration/title.wav, narration/1.wav ... narration/end.wav.
4. python3 make_video.py            -> video/out/mission-control-intro.mp4 and video/out/contact-sheet.png

Only ffmpeg is needed (on the Bazzite host). Edit SHOTS to change a caption, speed up a slow part or trim.
Each shot: caption (one or two lines), speed (2 = twice as fast), trim_start / trim_end in seconds (cut from
the start / end of the clip), position "bottom" (just above Mission Control's key hints) or "top".
If a shot is shorter than its narration, its last frame is held until the narration ends.
Avoid arrows (→) in captions: the font has no glyph for them.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
CLIPS = HERE / "clips"
NARRATION = HERE / "narration"
OUT = HERE / "out"
WORK = OUT / "parts"
FONT = "/usr/share/fonts/google-noto-vf/NotoSans[wght].ttf"
W, H, FPS = 1920, 1080, 30
VOICE_START = 0.4  # seconds of quiet before the narration of each part starts
VOICE_TAIL = 1.0   # seconds of quiet after it, before the next part

TITLE = ("Agentic coding system", "Mission Control · local LLM · Dispatch · fine-tuned router", "626 portfolio · SU5–7")
END = ("Thanks for watching",
       "Narration: Kokoro text-to-speech, run locally on the GPU, structured by Claude",
       "Design: su5-7-llm-agents/DESIGN.md   ·   Usage: su5-7-llm-agents/USAGE.md")

SHOTS = [
    {"caption": "Mission Control: one hub for all the coding agents"},
    {"caption": "Panels: projects, tasks, usage · containers, local LLM, running agents"},
    {"caption": "o starts the local model server (Ollama) on the GPU"},
    {"caption": "4 opens Codex on the local model: free, offline and private"},
    {"caption": "d = Dispatch: the fine-tuned router suggests a worker at once,\nthen Opus plans the task and writes the brief"},
    {"caption": "The worker runs in its own copy of the project (a git worktree), with a time limit", "speed": 8},
    {"caption": "Opus reviews the change, then a human decides: m merges, x discards"},
    {"caption": "Router fine-tuned with Unsloth: from 52% to 63% balanced accuracy,\nas good as a 9B model that thinks first, ~100× faster"},
    {"caption": "Everything is documented in the portfolio repo"},
]

ENCODE = ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
          "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2"]


def run(args: list[str]) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(json.loads(out)["format"]["duration"])


def esc(path: Path) -> str:
    """Escape a path for use inside an ffmpeg filter."""
    return str(path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def voice_for(key: str) -> Path | None:
    path = NARRATION / f"{key}.wav"
    return path if path.is_file() else None


def audio_input(voice: Path | None) -> tuple[list[str], str]:
    """ffmpeg input args and filter for a part's sound: its narration after a short pause, or silence."""
    if voice is None:
        return ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"], "[1:a]anull[a]"
    delay = int(VOICE_START * 1000)
    return ["-i", str(voice)], f"[1:a]adelay={delay}:all=1,aresample=48000,aformat=channel_layouts=stereo,apad[a]"


def needed_length(voice: Path | None) -> float:
    return VOICE_START + duration(voice) + VOICE_TAIL if voice else 0.0


def caption_filter(text_file: Path, position: str) -> str:
    """A semi-transparent bar with white text, every line centred on its own.

    Each line is drawn separately (one text file per line): drawtext would otherwise align the lines
    to the left of the widest one, and draw the line break itself as a box.
    """
    lines = text_file.read_text().splitlines()
    bar_h = 40 + 62 * len(lines)
    y = 24 if position == "top" else H - bar_h - 70  # 70 px keeps Mission Control's key hints visible
    filters = [f"drawbox=x=0:y={y}:w=iw:h={bar_h}:color=black@0.75:t=fill"]
    for i, line in enumerate(lines):
        line_file = text_file.with_name(f"{text_file.stem}-line{i}.txt")
        line_file.write_text(line)
        filters.append(f"drawtext=expansion=none:fontfile='{FONT}':textfile='{esc(line_file)}':fontcolor=white:"
                       f"fontsize=46:x=(w-text_w)/2:y={y + 24 + 62 * i}")
    return ",".join(filters)


def card(lines: tuple[str, str, str], out: Path, voice: Path | None, minimum: float = 4.0) -> None:
    """A dark card with a big title and two smaller lines, long enough for its narration."""
    seconds = max(minimum, needed_length(voice))
    files = []
    for i, text in enumerate(lines):
        f = WORK / f"{out.stem}-{i}.txt"
        f.write_text(text)
        files.append(f)
    filters = [
        f"drawtext=expansion=none:fontfile='{FONT}':textfile='{esc(files[0])}':fontcolor=white:fontsize=84:x=(w-text_w)/2:y=h/2-130",
        f"drawtext=expansion=none:fontfile='{FONT}':textfile='{esc(files[1])}':fontcolor=0x9fd8ff:fontsize=40:x=(w-text_w)/2:y=h/2+10",
        f"drawtext=expansion=none:fontfile='{FONT}':textfile='{esc(files[2])}':fontcolor=0xaaaaaa:fontsize=34:x=(w-text_w)/2:y=h/2+90",
        f"fade=in:0:{FPS // 2},fade=out:st={seconds - 0.5}:d=0.5",
    ]
    audio_args, audio_filter = audio_input(voice)
    run(["-f", "lavfi", "-i", f"color=c=0x101418:s={W}x{H}:r={FPS}:d={seconds}", *audio_args,
         "-filter_complex", f"[0:v]{','.join(filters)}[v];{audio_filter}", "-map", "[v]", "-map", "[a]",
         "-t", f"{seconds:.3f}", *ENCODE, str(out)])


def shot(clip: Path, spec: dict, index: int) -> Path:
    """Trim, speed up, scale to 1080p, caption and narrate one clip (the clip's own sound is dropped)."""
    out = WORK / f"{index:02d}.mp4"
    text_file = WORK / f"{index:02d}.txt"
    speed = spec.get("speed", 1)
    text_file.write_text(spec["caption"] + (f"   (×{speed})" if speed != 1 else ""))
    start = spec.get("trim_start", 0)
    end = duration(clip) - spec.get("trim_end", 0)
    voice = voice_for(str(index))
    video_seconds = (end - start) / speed
    seconds = max(video_seconds, needed_length(voice))
    hold = seconds - video_seconds  # freeze the last frame while the narration finishes
    filters = [
        f"scale={W}:{H}:force_original_aspect_ratio=decrease", f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black",
        f"setpts=(PTS-STARTPTS)/{speed}", f"fps={FPS}",
        *([f"tpad=stop_mode=clone:stop_duration={hold + 0.1:.3f}"] if hold > 0 else []),
        caption_filter(text_file, spec.get("position", "bottom")),
    ]
    audio_args, audio_filter = audio_input(voice)
    run(["-ss", str(start), "-to", str(end), "-i", str(clip), *audio_args,
         "-filter_complex", f"[0:v]{','.join(filters)}[v];{audio_filter}", "-map", "[v]", "-map", "[a]",
         "-t", f"{seconds:.3f}", *ENCODE, str(out)])
    return out


def contact_sheet(parts: list[Path]) -> None:
    """One frame from the middle of every part, in a grid: to check captions without watching it all."""
    frames = []
    for p in parts:
        f = WORK / f"{p.stem}-frame.png"
        run(["-ss", str(duration(p) / 2), "-i", str(p), "-frames:v", "1", "-vf", "scale=640:-1", str(f)])
        frames.append(f)
    if len(frames) == 1:
        shutil.copy(frames[0], OUT / "contact-sheet.png")
        return
    cols = 3
    inputs = [x for f in frames for x in ("-i", str(f))]
    layout = "|".join(f"{(i % cols) * 640}_{(i // cols) * 360}" for i in range(len(frames)))
    run([*inputs, "-filter_complex", f"xstack=inputs={len(frames)}:layout={layout}:fill=black",
         "-frames:v", "1", str(OUT / "contact-sheet.png")])


def main() -> None:
    clips = sorted(p for p in CLIPS.iterdir() if p.suffix.lower() in (".mp4", ".webm", ".mkv", ".mov"))
    if len(clips) != len(SHOTS):
        sys.exit(f"Found {len(clips)} clips in {CLIPS}, but SHOTS has {len(SHOTS)} entries. "
                 "Add or remove entries in SHOTS so they match.")
    WORK.mkdir(parents=True, exist_ok=True)
    parts = [WORK / "00-title.mp4"]
    card(TITLE, parts[0], voice_for("title"))
    for i, (clip, spec) in enumerate(zip(clips, SHOTS), 1):
        print(f"{i}. {clip.name}  ->  {spec['caption'].splitlines()[0]}")
        parts.append(shot(clip, spec, i))
    parts.append(WORK / "99-end.mp4")
    card(END, parts[-1], voice_for("end"), minimum=5.0)
    listing = WORK / "parts.txt"
    listing.write_text("".join(f"file '{p.name}'\n" for p in parts))
    final = OUT / "mission-control-intro.mp4"
    run(["-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", "-movflags", "+faststart", str(final)])
    contact_sheet(parts)
    print(f"\n{final}  ({duration(final):.0f} s, {final.stat().st_size / 1e6:.1f} MB)")
    print(f"{OUT / 'contact-sheet.png'}")


if __name__ == "__main__":
    main()
