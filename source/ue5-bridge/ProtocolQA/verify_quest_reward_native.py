"""Render and exercise reward controls using a captured original server dialog."""
import argparse
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from prepare_combined_expansion_data import digest


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def verify(workspace, install, engine, wire_proof):
    root = workspace / "QuestRewardsLab"
    assert wire_proof.resolve().is_relative_to((root / "RealProtocol").resolve())
    proof = read(wire_proof)
    assert proof["passed"] and proof["normal_runtime_unchanged"]
    capture = wire_proof.with_name("reward_outcome.json")
    dialog = read(capture)
    assert all(dialog["checks"].values())
    build_receipt = root / "Native/native_build.json"
    build = read(build_receipt)
    assert build["passed"] and not build["normal_binary_modified"]
    plugin = Path(build["project"]).parent / "Plugins/DAoCVisualBridge"
    normal = workspace / "Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll"
    assert digest(normal) == build["normal_binary_sha256"]
    assert all(digest(plugin / "Binaries/Win64" / name) == sha for name, sha in build["binaries_sha256"].items())
    source = root / "Native/CandidateSource"
    assert all(digest(source / name) == sha for name, sha in build["source_sha256"].items())
    host = root / "Native/InterfaceHost"
    ui_plugin = host / "Plugins/DAoCVisualBridge"
    binary = ui_plugin / "Binaries/Win64"
    binary.mkdir(parents=True, exist_ok=True)
    for name, sha in build["binaries_sha256"].items():
        shutil.copy2(plugin / "Binaries/Win64" / name, binary / name)
        assert digest(binary / name) == sha
    shutil.copy2(plugin / "DAoCVisualBridge.uplugin", ui_plugin / "DAoCVisualBridge.uplugin")
    # Only Slate textures are needed for this replay. The world content
    # junction on the full test host can dominate asset discovery.
    def quote(path):
        return "'" + str(path).replace("'", "''") + "'"
    for directory in ("ClassicUI", "InterfaceFonts"):
        ui_content = ui_plugin / "Content" / directory
        actual_ui = workspace / "Client/Plugins/DAoCVisualBridge/Content" / directory
        ui_content.parent.mkdir(exist_ok=True)
        if not ui_content.exists():
            subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                            "New-Item -ItemType Junction -Path " + quote(ui_content) + " -Target " + quote(actual_ui) + " | Out-Null"],
                           check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        assert ui_content.is_junction() and ui_content.resolve() == actual_ui.resolve()
    project = host / "QuestRewardUI.uproject"
    shutil.copy2(build["project"], project)
    icon_path = install / "new-client/godot/content/items/model_icons.json"
    icons = read(icon_path)
    for key in ["offer", "reward"]:
        for category in ["fixed_items", "optional_items"]:
            for item in dialog[key][category]:
                item["icon"] = icons.get(str(item["model"]), 0)
    out = root / "NativeAcceptance" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    out.mkdir(parents=True)
    fixture = out / "reward.json"
    fixture.write_text(json.dumps({k: dict(token=k+"-a", dialog=dialog[k], pending=False) for k in ("offer", "reward")}))
    args = [str(engine / "Binaries/Win64/UnrealEditor-Cmd.exe"), str(project), "/Engine/Maps/Entry",
            "-game", "-DaocBridge", "-DaocBridgeReadOnly", "-DaocBridgePort=19739", "-DaocBridgeQuestRewardsTest="+str(fixture), "-nosound",
            "-unattended", "-nosplash", "-d3d11", "-RenderOffscreen", "-windowed", "-ResX=1280", "-ResY=720", "-abslog="+str(out / "engine.log")]
    for key, name in [("DisplaySettings","display.ini"), ("KeyConfiguration","keys.ini"), ("ControlsSettings","camera.json"), ("AudioSettings","audio.ini")]:
        args.append("-DaocBridge"+key+"="+str(out / name))
    with (out / "stdout.log").open("w", encoding="utf-8") as log:
        run = subprocess.run(args, stdout=log, stderr=subprocess.STDOUT, timeout=180, creationflags=subprocess.CREATE_NO_WINDOW)
    report = fixture.with_suffix(".json.native.json")
    assert run.returncode == 0 and report.is_file(), str(out)
    result = read(report)
    assert result["passed"] and not result["failures"], result
    assert digest(normal) == build["normal_binary_sha256"]
    shot = fixture.with_suffix(".json.png")
    assert shot.is_file()
    result.update(build_receipt_sha256=digest(build_receipt), wire_proof_sha256=digest(wire_proof), screenshot=str(shot), normal_installation_modified=False)
    path = out / "verified.json"
    path.write_text(json.dumps(result, indent=2))
    return dict(passed=True, checks=result["checks"], proof=str(path), screenshot=str(shot))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for key in ["workspace", "install", "engine", "wire-proof"]:
        parser.add_argument("--"+key, required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.workspace.resolve(), args.install.resolve(), args.engine.resolve(), args.wire_proof.resolve())))
