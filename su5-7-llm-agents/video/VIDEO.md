# Intro video: how it is made

ITRI626 SU5–7 · checklist item *"System documentation: intro video"*.

The video is a **silent screen recording with on-screen captions** (about 4 minutes). At the presentation I
talk over it; anyone watching it later reads the captions. Finished video: `out/mission-control-intro.mp4`.

## How it is made
1. **Record** each shot below as its own short clip with KDE's **Spectacle**
   (*New Screen Recording → Full Screen*; stop with the Spectacle icon in the panel). Record them in order.
2. **Move the clips** into [`clips/`](clips/) (Spectacle saves to `~/Videos` by default). Their date-time names
   keep them in recording order. Retake a shot by deleting its clip and recording it again.
3. **Build:** `python3 make_video.py`. It burns in the captions, speeds up waiting, adds a title and end
   card, and joins everything into `out/mission-control-intro.mp4`. It also writes `out/contact-sheet.png`
   (one frame per shot) to check every caption at a glance.

Captions, speed-ups and trims are in the `SHOTS` list at the top of [`make_video.py`](make_video.py). Only
ffmpeg is used (already on the host); raw clips are not committed.

## Before recording
- Terminal: full screen, **large font** (Ctrl + `+` a few times in Konsole) so it reads on a projector.
- Ollama **stopped** (so shot 3 shows it starting): `systemctl --user stop ollama`.
- Have `models/router-finetune/results/eval.md` ready to show for shot 8 (in a terminal: `cat`, or the README
  on GitHub).
- Nothing private on screen (other windows, notifications).

## Shot list
| # | Do this on screen | Caption (burned in) | Say (talking points) |
|---|---|---|---|
| 1 | Desktop → open a terminal → type `mc` → Mission Control opens | Mission Control: one hub for all my coding agents | "This is my hub for all my coding agents: cloud ones and my own local model." |
| 2 | Press Tab slowly through the panels | Panels: projects, tasks, usage · containers, local LLM, running agents | One line per panel; Bazzite is read-only, so tools live in the `dev` container |
| 3 | Press `o` → Ollama starts, GPU bar fills, `ornith-1.5:9b ★` | o starts the local model server (Ollama) on my RTX 5070 | "The local model runs on my RTX 5070, 100% on the GPU, 64K context." |
| 4 | Select a project, press `4` → Codex on the local model opens; ask it something small; back in Mission Control the Agents panel shows `codex · ornith-1.5:9b` | 4 opens Codex on my local model: free, offline and private | "Same coding agent, but my own model: no cloud, no limits." |
| 5 | Select `mission-control`, press `d`, type *Add a --version option to mc that prints the app version*, Enter → router suggestion, then Opus's plan | d = Dispatch: my fine-tuned router suggests a worker at once, then Opus plans the task and writes the brief | "The small model I fine-tuned answers in 0.05 s; Opus picks the worker and writes its instructions." |
| 6 | Start → Tasks panel `● running …` (keep recording until it finishes; it is sped up ×8) | The worker runs in its own copy of the project (a git worktree), with a time limit | "It works in its own copy: it can't touch my real code." |
| 7 | Notification → select the task → `v` (review + diff) → Esc → `m` → `y` (or `x` to discard) | Opus reviews the change. I decide: m merges, x discards | "Opus reviews it, and I decide what gets merged." |
| 8 | Show the results table (`results/eval.md`) | Router fine-tuned with Unsloth: from 52% to 63% balanced accuracy, as good as a 9B model that thinks first, ~100× faster | "Trained in 4 minutes on my GPU; the first attempt failed because of a missing token, which I tracked down." |
| 9 | The repo on GitHub, or the `su5-7-llm-agents/` folder (`DESIGN.md`, `USAGE.md`) | Everything is documented in the portfolio repo | "Design, usage, evidence of every agent run: all in the repo." |

## Who built what
| Part | By |
|---|---|
| Shot list, captions, `make_video.py` (ffmpeg editing) | Claude Code |
| Recording and live narration | Me |
