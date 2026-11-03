"""Remember user choices (currently just the theme) between runs.

Stored as JSON in $XDG_CONFIG_HOME/mission-control/settings.json, which is
usually ~/.config/mission-control/settings.json. Set MISSION_CONTROL_CONFIG_DIR
to use another folder (the tests do this so they never touch your real file).
"""

from __future__ import annotations

import json
import os
from pathlib import Path


def settings_path() -> Path:
    """Where the settings file lives."""
    override = os.environ.get("MISSION_CONTROL_CONFIG_DIR")
    if override:
        return Path(override) / "settings.json"
    config_home = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(config_home) / "mission-control" / "settings.json"


def load_settings() -> dict[str, object]:
    """Return the saved settings, or {} if there are none or the file is broken."""
    try:
        data = json.loads(settings_path().read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_setting(key: str, value: object) -> None:
    """Save one setting, keeping the others. Failing to save is never fatal."""
    data = load_settings()
    if data.get(key) == value:
        return
    data[key] = value
    path = settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2) + "\n")
        tmp.replace(path)  # atomic: never leaves a half-written file
    except OSError:
        pass
