"""Replay both original tagged NPC models without a live server."""
import argparse
import json
import math
from pathlib import Path
import subprocess

from build_spell_audio_native import build
from prepare_combined_expansion_data import digest
from verify_connacht_npc_batch import read, snapshot


def verify(workspace, engine):
    root = workspace / "ConnachtNpcCoverageLab/ModelFlags"
    built = build(workspace, engine, "ConnachtNpcCoverageLab/ModelFlags")
    models = (96, 670)
    heading = 1024
    angle = -heading * math.tau / 4096
    cases = []
    for sequence, tag in enumerate((0, 0x8000, 0), 1):
        entities = [
            dict(id=f"npc:{index+20}", kind="npc", model_id=model | tag, expected_model_id=model,
                 name="Model variant", size=50, health=1, state="idle",
                 position_m=[1364 + index * 4, 130, 1263], heading_4096=heading,
                 forward_xz=[math.sin(angle), math.cos(angle)])
            for index, model in enumerate(models)
        ]
        cases.append(dict(label=f"tag transition {sequence}", snapshot=snapshot(sequence, entities)))
    cases.append(dict(label="cleanup", snapshot=snapshot(4, [])))
    fixture = root / "entity_replay.json"
    fixture.write_text(json.dumps(dict(cases=cases)), encoding="utf-8")
    report = Path(str(fixture) + ".native.json")
    report.unlink(missing_ok=True)
    catalog = workspace / "models.json"
    command = [
        str(engine / "Binaries/Win64/UnrealEditor-Cmd.exe"), built["project"], "/Engine/Maps/Entry",
        "-game", "-DaocBridge", "-DaocBridgeReadOnly", "-DaocBridgePort=19739",
        "-DaocBridgeCatalog=" + str(catalog), "-DaocBridgeEntityTest=" + str(fixture),
        "-abslog=" + str(root / "native_engine.log"), "-nullrhi", "-nosound", "-unattended", "-nosplash",
    ]
    with (root / "native_stdout.log").open("w", encoding="utf-8") as log:
        run = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=180,
                             creationflags=subprocess.CREATE_NO_WINDOW)
    assert run.returncode == 0 and report.is_file()
    native = read(report)
    assert native["passed"] and native["native_actor_consumer"] and native["checks"] == 60, native
    normal = workspace / "Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll"
    assert digest(normal) == built["normal_binary_sha256"]
    proof = dict(passed=True, checks=native["checks"], models=list(models), installed=False,
                 evidence={str(path): digest(path) for path in (root / "native_build.json", fixture, report, catalog)})
    (root / "verified.json").write_text(json.dumps(proof, indent=2), encoding="utf-8")
    return proof


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("workspace", "engine"):
        parser.add_argument("--" + option, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.workspace.resolve(), args.engine.resolve())))
