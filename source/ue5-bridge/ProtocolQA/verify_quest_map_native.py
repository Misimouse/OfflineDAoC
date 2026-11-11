"""Verify red objective points and removal in the original Unreal zone map."""
import argparse
import json
from pathlib import Path

from verify_quest_indicator_native import verify


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("workspace", "engine"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.workspace.resolve(), args.engine.resolve(),
                            lab="QuestMapLab", test="QuestMap", checks=6, kinds=("map", "cleared"))))
