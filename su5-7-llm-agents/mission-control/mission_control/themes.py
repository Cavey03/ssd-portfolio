"""Colour themes for Mission Control.

All colours come from Textual's theme system:
- app.tcss uses theme variables such as $primary and $background, so the
  layout recolours itself when the theme changes.
- The coloured text inside tables and bars is built in Python with Rich, which
  needs plain "#rrggbb" colours. palette_from_variables() turns the active
  theme's variables into a Palette with exactly those.

Because only standard theme roles are used (plus three agent colours with
defaults), Textual's built-in themes (Nord, Dracula, ...) work too, via the
command palette (Ctrl+P → "Change theme").
"""

from __future__ import annotations

from dataclasses import dataclass, field

from textual.color import Color
from textual.theme import Theme

DEFAULT_THEME = "neon-city"

# Agent colours used when a theme (e.g. a built-in one) doesn't define its own.
AGENT_VARIABLE_DEFAULTS = {
    "agent-claude": "#d7875f",
    "agent-codex": "#c3e88d",
    "agent-agy": "#61afef",
}

NEON_CITY = Theme(
    name="neon-city",
    # Cyberpunk: deep purple-black, glowing cyan and electric yellow, hot-pink alerts.
    primary="#00f0ff",
    secondary="#fcee0a",
    accent="#ff2a6d",
    success="#00ff9f",
    warning="#fcee0a",
    error="#ff2a6d",
    foreground="#e6f6ff",
    background="#0a0612",
    surface="#140b24",
    panel="#1c1033",
    dark=True,
    variables={
        "agent-claude": "#ff9e3d",
        "agent-codex": "#fcee0a",
        "agent-agy": "#b967ff",
    },
)

CRT_GREEN = Theme(
    name="crt-green",
    # Retro mainframe: green phosphor on black. Nearly monochrome on purpose;
    # only errors break out of the green.
    primary="#33ff66",
    secondary="#9dff4a",
    accent="#33ff66",
    success="#33ff66",
    warning="#c8ff3d",
    error="#ff6b3d",
    foreground="#33ff66",
    background="#020803",
    surface="#06120a",
    panel="#0b1f10",
    dark=True,
    variables={
        "agent-claude": "#b8ffb0",
        "agent-codex": "#33ff66",
        "agent-agy": "#1fcf55",
    },
)

CRT_AMBER = Theme(
    name="crt-amber",
    # The same retro look in amber phosphor.
    primary="#ffb000",
    secondary="#ffd166",
    accent="#ffb000",
    success="#ffc533",
    warning="#ffe08a",
    error="#ff5533",
    foreground="#ffb000",
    background="#0c0700",
    surface="#170e00",
    panel="#211500",
    dark=True,
    variables={
        "agent-claude": "#ffe0a3",
        "agent-codex": "#ffb000",
        "agent-agy": "#ff8c1a",
    },
)

MISSION_TEAL = Theme(
    name="mission-teal",
    # The original Mission Control look.
    primary="#50d6c5",
    secondary="#61afef",
    accent="#50d6c5",
    success="#50d6c5",
    warning="#e5c07b",
    error="#e06c75",
    foreground="#dce5ef",
    background="#10151e",
    surface="#171f2b",
    panel="#1c2633",
    dark=True,
    variables={
        "agent-claude": "#d7875f",
        "agent-codex": "#c3e88d",
        "agent-agy": "#61afef",
    },
)

THEMES: tuple[Theme, ...] = (NEON_CITY, CRT_GREEN, CRT_AMBER, MISSION_TEAL)
"""Our own themes, in the order the `t` key cycles through them."""

THEME_NAMES = {
    "neon-city": "Neon City",
    "crt-green": "CRT Green",
    "crt-amber": "CRT Amber",
    "mission-teal": "Mission Teal",
}


def next_theme(current: str) -> str:
    """The theme after `current` in the cycle (the first one if `current` isn't ours)."""
    names = [theme.name for theme in THEMES]
    if current not in names:
        return names[0]
    return names[(names.index(current) + 1) % len(names)]


def _solid(value: str | None, fallback: str) -> str:
    """Return value as plain "#rrggbb" (Rich can't use alpha or "auto")."""
    try:
        return Color.parse(value).hex6 if value else fallback
    except Exception:  # Textual raises its own ColorParseError for odd values
        return fallback


@dataclass(frozen=True)
class Palette:
    """Plain colours for Rich text, derived from the active theme."""

    ok: str
    warn: str
    alert: str
    info: str
    muted: str
    agents: dict[str, str] = field(default_factory=dict)

    def agent(self, name: str) -> str:
        """Colour for an agent name such as "claude"."""
        return self.agents.get(name, self.info)


def palette_from_variables(variables: dict[str, str]) -> Palette:
    """Build a Palette from the app's CSS variables (App.get_css_variables())."""
    foreground = _solid(variables.get("foreground"), "#e0e0e0")
    background = _solid(variables.get("background"), "#000000")
    # A muted text colour: the foreground blended 45 % of the way to the background.
    muted = Color.parse(foreground).blend(Color.parse(background), 0.45).hex6
    agents = {
        name: _solid(variables.get(f"agent-{name}"), AGENT_VARIABLE_DEFAULTS[f"agent-{name}"])
        for name in ("claude", "codex", "agy")
    }
    return Palette(
        ok=_solid(variables.get("success"), "#4ebf71"),
        warn=_solid(variables.get("warning"), "#fea62b"),
        alert=_solid(variables.get("error"), "#b93c5b"),
        info=_solid(variables.get("primary"), "#0178d4"),
        muted=muted,
        agents=agents,
    )


# Mission Teal as plain colours: used when no app is available (e.g. unit tests).
DEFAULT_PALETTE = Palette(
    ok="#50d6c5",
    warn="#e5c07b",
    alert="#e06c75",
    info="#61afef",
    muted="#8795a8",
    agents={"claude": "#d7875f", "codex": "#c3e88d", "agy": "#61afef"},
)
