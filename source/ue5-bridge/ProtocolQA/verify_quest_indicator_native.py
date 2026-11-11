"""Exercise the original quest colors and map markers in a private Unreal viewport."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import shutil
import subprocess

from prepare_combined_expansion_data import digest
from player_trade_delivery_plan import read


def verify(workspace, engine):
    root = workspace / "QuestIndicatorLab"
    build_receipt = root / "native_build.json"
    build = read(build_receipt)
    assert build["passed"]
    normal = workspace / "Client/Plugins/DAoCVisualBridge"
    binary_name = "UnrealEditor-DAoCVisualBridge.dll"
    assert digest(normal / "Binaries/Win64" / binary_name) == build["normal_binary_sha256"]
    compiled = Path(build["project"]).parent / "Plugins/DAoCVisualBridge"
    host = root / "InterfaceHost"
    plugin = host / "Plugins/DAoCVisualBridge"
    (plugin / "Binaries/Win64").mkdir(parents=True, exist_ok=True)
    shutil.copy2(compiled / "DAoCVisualBridge.uplugin", plugin / "DAoCVisualBridge.uplugin")
    for name, sha in build["binaries_sha256"].items():
        dst = plugin / "Binaries/Win64" / name
        shutil.copy2(compiled / "Binaries/Win64" / name, dst)
        assert digest(dst) == sha

    def psquote(path):
        return "'" + str(path).replace("'", "''") + "'"

    for folder in ("ClassicUI", "InterfaceFonts", "SpellVisuals_v01"):
        dst = plugin / "Content" / folder
        src = normal / "Content" / folder
        dst.parent.mkdir(exist_ok=True)
        if not dst.exists():
            subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                            "New-Item -ItemType Junction -Path "+psquote(dst)+" -Target "+psquote(src)+" | Out-Null"],
                           check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        assert dst.is_junction() and dst.resolve() == src.resolve()
    project = host / "QuestIndicators.uproject"
    shutil.copy2(build["project"], project)
    output = root / "Acceptance" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    output.mkdir(parents=True)
    result_file = output / "indicators"
    args = [str(engine / "Binaries/Win64/UnrealEditor-Cmd.exe"), str(project), "/Engine/Maps/Entry",
            "-game", "-DaocBridge", "-DaocBridgeReadOnly", "-DaocBridgePort=19739",
            "-DaocBridgeQuestIndicatorTest="+str(result_file), "-nosound", "-unattended", "-nosplash",
            "-d3d11", "-RenderOffscreen", "-windowed", "-ResX=1280", "-ResY=720", "-abslog="+str(output/"engine.log")]
    for key, name in [("DisplaySettings","display.ini"), ("KeyConfiguration","keys.ini"), ("ControlsSettings","camera.json"), ("AudioSettings","audio.ini")]:
        args.append("-DaocBridge"+key+"="+str(output / name))
    with (output / "stdout.log").open("w", encoding="utf-8") as log:
        run = subprocess.run(args, stdout=log, stderr=subprocess.STDOUT, timeout=180, creationflags=subprocess.CREATE_NO_WINDOW)
    assert run.returncode == 0 and result_file.with_suffix(".json").is_file(), str(output)
    result = read(result_file.with_suffix(".json"))
    assert result["passed"] and result["checks"] == 8, result
    captures = {kind: output / f"indicators-{kind}.png" for kind in ("rings", "map")}
    assert all(path.is_file() for path in captures.values()), str(output)
    assert digest(normal / "Binaries/Win64" / binary_name) == build["normal_binary_sha256"]
    result.update(build_sha256=digest(build_receipt), screenshots={key:str(value) for key,value in captures.items()})
    (output / "verified.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return dict(passed=True, checks=result["checks"], proof=str(output / "verified.json"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("workspace","engine"):
        parser.add_argument("--"+name, required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.workspace.resolve(), args.engine.resolve())))
