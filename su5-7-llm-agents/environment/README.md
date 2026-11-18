# SSD Portfolio – Agentic Coding Environment on Linux

This repository documents how I set up an agentic coding environment on Linux,
and holds the projects I build with it.

## 1. The host system

| Component | Details |
|---|---|
| OS | Bazzite 44 (KDE / Kinoite), based on Fedora 44 |
| Kernel | 7.2.11 |
| Desktop | KDE Plasma (Wayland) |
| CPU | AMD Ryzen 7 5800X (8 cores / 16 threads) |
| GPU | NVIDIA GeForce RTX 5070 |
| RAM | 32 GB |

Bazzite is an **immutable** (atomic) distribution: the root filesystem is
read-only and updated as a whole image with `rpm-ostree`. Instead of installing
development tools directly on the host, the recommended approach is to use
containers.

## 2. Design decisions

- **One development container, many project folders.** All tools live in a
  single [Distrobox](https://distrobox.it/) container called `dev`. Projects
  live in `~/Projects/`, which is shared between host and container because
  Distrobox mounts the home directory.
  - The host stays clean and stable.
  - If the container breaks, it can be deleted and recreated without losing
    any project files.
- **Cloud AI agents instead of local models.** I chose subscription-based
  agents (Claude, ChatGPT/Codex, Google) over local models such as Ollama,
  because they are much stronger at coding and need no GPU driver setup
  inside the container. Local models remain a possible future extension.

```
Bazzite host (read-only system)
└── /var/home/Kyle/            ← shared with the container
    └── Projects/
        ├── ssd-portfolio/     ← this repository
        └── <other projects>/

Distrobox container "dev" (Fedora 44)
└── node, npm, python3, git, gh, codex
    + claude and agy (installed in ~/.local/bin, shared)
```

## 3. Setup steps

### 3.1 Create the container
```bash
distrobox create --name dev --image registry.fedoraproject.org/fedora-toolbox:44
distrobox enter dev
```

### 3.2 Install Node.js (needed for Codex CLI)
Inside the container:
```bash
sudo dnf install -y nodejs npm     # Node 22, npm 10
```

### 3.3 Install the AI coding agents

| Agent | Command | Install method | Login |
|---|---|---|---|
| Claude Code | `claude` | Native installer → `~/.local/bin` | Claude subscription |
| Codex CLI (OpenAI) | `codex` | `sudo npm install -g @openai/codex` | ChatGPT subscription |
| Antigravity CLI (Google) | `agy` | Official install script → `~/.local/bin` | Google account |

### 3.4 Install the GitHub CLI
```bash
sudo dnf install -y gh
```

## 4. Problems encountered

### Gemini CLI no longer supports personal accounts
I first installed Google's **Gemini CLI** (`npm install -g @google/gemini-cli`).
Signing in failed with:

> This client is no longer supported for Gemini Code Assist for individuals.
> To continue using Gemini, please migrate to the Antigravity suite of products.

Research showed that, from 18 June 2026, Google stopped serving personal accounts
through Gemini CLI and replaced it with **Antigravity CLI** (`agy`).

**Fix:** I uninstalled Gemini CLI and installed Antigravity CLI instead.

### Reviewing an install script before running it
The usual install command is `curl ... | bash`, which runs a script from the
internet without looking at it first. Instead I downloaded the script, read it,
and confirmed what it does: it detects the platform, downloads the binary, checks
its SHA512 checksum, installs to `~/.local/bin`, and adds that directory to `PATH`
in `~/.bashrc`. Only then did I run it.

## 5. Daily workflow

```bash
distrobox enter dev               # enter the dev container
cd ~/Projects/<project>           # always start the agent inside the project folder
claude                            # or: codex / agy
```

Each agent treats the folder it is started in as its workspace, so starting it
in the right project folder keeps work and history separated per project.
