"""Test package setup: keep tests away from the user's real files.

- settings: a temporary config folder instead of ~/.config/mission-control
- dispatched tasks: a temporary state folder instead of ~/.local/state/mission-control
"""

import os
import tempfile

os.environ["MISSION_CONTROL_CONFIG_DIR"] = tempfile.mkdtemp(prefix="mission-control-tests-")
os.environ["MISSION_CONTROL_STATE"] = tempfile.mkdtemp(prefix="mission-control-test-state-")
