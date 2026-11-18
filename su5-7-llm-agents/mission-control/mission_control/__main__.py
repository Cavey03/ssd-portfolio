"""Run the Mission Control dashboard, or `mc task ...` (Dispatch on the command line)."""

import sys


def main() -> int:
    if sys.argv[1:2] == ["task"]:
        from mission_control.cli import main as task_main  # no UI needed for the command line
        return task_main(sys.argv[2:])
    from mission_control.app import MissionControlApp
    MissionControlApp().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
