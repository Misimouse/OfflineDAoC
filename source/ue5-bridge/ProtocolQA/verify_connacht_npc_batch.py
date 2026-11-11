"""Import and replay the Connacht creature candidate in an isolated Unreal project."""
import argparse
import json
import math
import os
from pathlib import Path
import shutil
import subprocess

from prepare_combined_expansion_data import digest


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def snapshot(sequence, rows):
    return dict(type="snapshot", protocol="daoc-visual-bridge", version=1, session="entity-acceptance",
                seq=sequence, zone_id=207, origin_m=[1364,130,1263], entities=rows)


def verify(workspace, engine, batch=1):
    assert batch > 0
    root = workspace / "ConnachtNpcCoverageLab" / f"Batch{batch}"
    export_path = root / "export_verified.json"
    export = read(export_path)
    ids = list(export["models"])
    assert export["passed"] and ids
    assert all(digest(Path(path)) == sha for path, sha in export["inputs"].items())
    assert all(digest(Path(row["file"])) == row["sha256"] for row in export["models"].values())
    assert digest(root / "SourceModels/exported.json") == export["exported_sha256"]
    catalog = workspace / "models.json"
    baseline = read(catalog)
    before_catalog = digest(catalog)
    normal = workspace / "Client/Plugins/DAoCVisualBridge"
    host = root / "AssetHost"
    plugin = host / "Plugins/DAoCVisualBridge"
    namespace = f"ConnachtNpcBatch{batch}_v01"
    normal_assets = normal / "Content" / namespace
    assert not normal_assets.exists(), "Batch is already active"
    content = plugin / "Content" / namespace
    content.mkdir(parents=True, exist_ok=True)
    assert content.resolve().is_relative_to(root.resolve()) and not content.is_junction()
    binary = plugin / "Binaries/Win64"
    binary.mkdir(parents=True, exist_ok=True)
    shutil.copy2(normal / "DAoCVisualBridge.uplugin", plugin / "DAoCVisualBridge.uplugin")
    binary_inputs = {}
    for name in ("UnrealEditor-DAoCVisualBridge.dll", "UnrealEditor.modules"):
        path = normal / "Binaries/Win64" / name
        binary_inputs[str(path)] = digest(path)
        shutil.copy2(path, binary / name)
    project = host / "ConnachtNpcBatch.uproject"
    project.write_text(json.dumps(dict(FileVersion=3, EngineAssociation="5.8", Plugins=[
        dict(Name=name, Enabled=True) for name in ("DAoCVisualBridge", "PythonScriptPlugin", "EditorScriptingUtilities")
    ])), encoding="utf-8")
    config = root / "import_config.json"
    config.write_text(json.dumps(dict(catalog=str(catalog), model_ids=ids, batch=batch)), encoding="utf-8")
    script = Path(__file__).resolve().parents[1] / "import_connacht_missing_unreal.py"
    command = [str(engine / "Binaries/Win64/UnrealEditor-Cmd.exe"), str(project)]
    flags = ["-nullrhi", "-unattended", "-nosound", "-nosplash"]
    with (root / "import_stdout.log").open("w", encoding="utf-8") as log:
        run = subprocess.run(command + ["-run=pythonscript", "-script="+str(script),
                             "-abslog="+str(root/"import_engine.log")] + flags,
                             env=dict(os.environ, DAOC_CONNACHT_IMPORT_CONFIG=str(config)), stdout=log,
                             stderr=subprocess.STDOUT, timeout=300, creationflags=subprocess.CREATE_NO_WINDOW)
    assert run.returncode == 0, str(root / "import_engine.log")
    imported = read(root / "import.json")
    candidate = root / "candidate_catalog.json"
    merged = read(candidate)
    assert imported["passed"] and set(imported["models"]) == set(ids)
    assert all(merged[key] == value for key, value in baseline.items())
    assert set(merged).difference(baseline) == set(ids)
    for ident in ids:
        record = imported["models"][ident]
        assert record["clips"] == record["source_clips"] and record["material_count"] > 0 and record["textures"]
        assert merged[ident]["type"] == "skeletal" and {"idle", "walk"}.issubset(merged[ident])

    cases = []
    for seq, state in enumerate(("idle", "walk", "dead", "idle"), 1):
        rows = []
        for index, ident in enumerate(ids):
            heading = index * 700
            angle = -heading * math.tau / 4096
            rows.append(dict(id=f"npc:{index+500}", kind="npc", model_id=int(ident), name=merged[ident]["name"],
                             size=50, health=0 if state=="dead" else 1, position_m=[1364+index*4,130,1263],
                             forward_xz=[math.sin(angle), math.cos(angle)], heading_4096=heading, state=state))
        cases.append(dict(label=state, snapshot=snapshot(seq, rows)))
    cases.append(dict(label="cleanup", snapshot=snapshot(5, [])))
    fixture = root / "entity_replay.json"
    fixture.write_text(json.dumps(dict(cases=cases)), encoding="utf-8")
    report = Path(str(fixture)+".native.json")
    report.unlink(missing_ok=True)
    with (root / "native_stdout.log").open("w", encoding="utf-8") as log:
        run = subprocess.run(command + ["/Engine/Maps/Entry", "-game", "-DaocBridge", "-DaocBridgeReadOnly",
                             "-DaocBridgePort=19739", "-DaocBridgeCatalog="+str(candidate),
                             "-DaocBridgeEntityTest="+str(fixture), "-abslog="+str(root/"native_engine.log")] + flags,
                             stdout=log, stderr=subprocess.STDOUT, timeout=150, creationflags=subprocess.CREATE_NO_WINDOW)
    assert run.returncode == 0 and report.is_file(), str(root / "native_engine.log")
    replay = read(report)
    assert replay["passed"] and replay["native_actor_consumer"] and replay["checks"] == 24 + 16 * len(ids)
    errors = [line for line in (root/"native_engine.log").read_text(encoding="utf-8", errors="replace").splitlines()
              if namespace in line and any(word in line for word in ("Failed to load", "Couldn't find", "Can't find file"))]
    assert not errors, errors
    assert all(digest(Path(path)) == sha for path, sha in binary_inputs.items())
    assert digest(catalog) == before_catalog and not normal_assets.exists()
    assets = {path.relative_to(content).as_posix():digest(path) for path in content.rglob("*.uasset")}
    assert assets
    receipt = dict(passed=True, model_ids=ids, assets=assets, checks=replay["checks"],
                   export_sha256=digest(export_path), native_sha256=digest(report), catalog_before_sha256=before_catalog,
                   candidate_sha256=digest(candidate), installed=False)
    (root / "verified.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return dict(passed=True, model_ids=ids, checks=replay["checks"], assets=len(assets), installed=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for key in ("workspace", "engine"):
        parser.add_argument("--" + key, type=Path, required=True)
    parser.add_argument("--batch", type=int, default=1)
    args = parser.parse_args()
    print(json.dumps(verify(args.workspace.resolve(), args.engine.resolve(), args.batch)))
