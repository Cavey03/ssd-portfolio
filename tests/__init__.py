"""Test package setup: keep tests away from the user's real settings file."""

import os
import tempfile

os.environ["MISSION_CONTROL_CONFIG_DIR"] = tempfile.mkdtemp(prefix="mission-control-tests-")
