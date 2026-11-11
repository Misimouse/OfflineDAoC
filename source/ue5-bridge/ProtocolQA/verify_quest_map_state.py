"""Exercise the quest objective projection adapter in a disposable Godot project."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess

from prepare_combined_expansion_data import digest


def verify(workspace, install):
    source = Path(__file__).resolve().parents[1] / "Godot"
    root = workspace / "QuestMapLab/State" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    root.mkdir(parents=True)
    (root / "project.godot").write_text('[application]\nconfig/name="Private Quest Map QA"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n')
    inputs = {}
    for name in ("quest_map_state.gd", "test_quest_map.gd"):
        path = source / name
        inputs[str(path)] = digest(path)
        shutil.copy2(path, root / name)
    executable = install / "new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe"
    env = dict(os.environ, APPDATA=str(root / "AppData"), LOCALAPPDATA=str(root / "LocalAppData"))
    run = subprocess.run([str(executable), "--headless", "--path", str(root), "--script", "res://test_quest_map.gd"],
                         env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                         timeout=40, creationflags=subprocess.CREATE_NO_WINDOW)
    (root / "godot.log").write_text(run.stdout, encoding="utf-8")
    assert run.returncode == 0 and "ERROR:" not in run.stdout, run.stdout
    result = json.loads((root / "verified_state.json").read_text())
    assert result["passed"] and result["checks"] == 15 and not result["failures"]
    assert all(digest(Path(path)) == sha for path, sha in inputs.items())
    result.update(source_inputs=inputs, normal_installation_modified=False)
    proof = root / "verified.json"
    proof.write_text(json.dumps(result, indent=2))
    return dict(passed=True, checks=result["checks"], proof=str(proof))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("workspace", "install"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.workspace.resolve(), args.install.resolve())))
