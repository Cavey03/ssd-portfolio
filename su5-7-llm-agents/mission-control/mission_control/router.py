"""The fine-tuned local router: a small model that suggests a worker for a task in under a second.

Trained with Unsloth on reviewed routing labels (models/router-finetune/ in the portfolio) and served by
Ollama like the other local models. Dispatch shows its suggestion next to Opus's plan, uses it when Opus
can't be reached, and logs both, so the two can be compared over time.

The prompt must be exactly the one the model was trained with (train_router.SYSTEM_PROMPT).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from mission_control.localllm import ollama_url

ROUTER_MODEL = os.environ.get("MISSION_CONTROL_ROUTER", "router-rtx5070")
SYSTEM_PROMPT = "Route the coding task to one worker: local, codex or claude. Answer with JSON."
LABELS = ("local", "codex", "claude")
SCHEMA = {"type": "object", "properties": {"agent": {"type": "string", "enum": list(LABELS)}},
          "required": ["agent"]}


def local_route(task: str, model: str | None = None, timeout: float = 20.0) -> str | None:
    """Return the router's suggestion ("local", "codex" or "claude"), or None if it isn't available.

    None covers: Ollama stopped, the router model not installed, or an unusable answer.
    """
    body = json.dumps({
        "model": model or ROUTER_MODEL, "stream": False, "think": False, "format": SCHEMA,
        "options": {"temperature": 0},
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": f"Task: {task}"}],
    }).encode()
    request = urllib.request.Request(f"{ollama_url()}/api/chat", data=body,
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            agent = json.loads(json.loads(response.read())["message"]["content"]).get("agent")
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None
    return agent if agent in LABELS else None
