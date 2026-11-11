"""Install the verified native NPC model flag handling with exact rollback."""
import argparse
import json
from pathlib import Path
import shutil

from quest_reward_delivery import BINARIES, NATIVE, SOURCE, apply_delivery, current, digest, read, write

ROOT = "ConnachtNpcCoverageLab/ModelFlags"
CHANGED = ("Private/DAoCBridgeEntityAcceptance.cpp", "Private/DAoCBridgeSubsystem.cpp")


def expected(workspace):
    root = workspace / ROOT
    proof = read(root / "verified.json")
    assert proof["passed"] and proof["checks"] == 60 and proof["models"] == [96, 670]
    for path, sha in proof["evidence"].items():
        src = Path(path)
        checked = root / "catalog_tested.json" if src == workspace / "models.json" else src
        assert checked.is_relative_to(root) and digest(checked) == sha
    build = read(root / "native_build.json")
    prior = read(workspace / "ConnachtNpcCoverageLab/Figures/native_build.json")
    assert build["passed"] and build["normal_binary_sha256"] == prior["binaries_sha256"][BINARIES[0]]
    before, after = [{Path(k).as_posix(): v for k, v in item["source_sha256"].items()} for item in (prior, build)]
    assert before.keys() == after.keys()
    assert {key for key in after if before[key] != after[key]} == {"DAoCVisualBridge/" + name for name in CHANGED}
    normal = workspace / "Client/Plugins/DAoCVisualBridge"
    compiled = Path(build["project"]).parent / "Plugins/DAoCVisualBridge"
    assert compiled.resolve().is_relative_to(root)
    for name in BINARIES:
        rel = Path("Binaries/Win64") / name
        yield compiled / rel, normal / rel, prior["binaries_sha256"][name], build["binaries_sha256"][name]
    for name in CHANGED:
        rel = "DAoCVisualBridge/" + name
        yield root / "CandidateSource" / rel, normal / "Source" / rel, before[rel], after[rel]
        if name.endswith("/DAoCBridgeSubsystem.cpp"):
            yield root / "CandidateSource" / rel, SOURCE / NATIVE / rel, before[rel], after[rel]


def validate(workspace, plan, after=False):
    root = workspace / ROOT
    assert plan["predecessor"] == digest(workspace / "ConnachtNpcCoverageLab/Figures/installed.json")
    assert plan["verification"] == digest(root / "verified.json")
    rows = {}
    for src, dst, old, new in expected(workspace):
        assert digest(src) == new and current(dst) == (new if after else old), str(dst)
        rows[str(dst)] = dict(source=str(src), target=str(dst), before_sha256=old, after_sha256=new)
    assert list(rows.values()) == plan["files"]
    return rows


def prepare(workspace):
    root = workspace / ROOT
    shutil.copy2(workspace / "models.json", root / "catalog_tested.json")
    plan = dict(predecessor=digest(workspace / "ConnachtNpcCoverageLab/Figures/installed.json"),
                verification=digest(root / "verified.json"),
                files=[dict(source=str(src), target=str(dst), before_sha256=old, after_sha256=new)
                       for src, dst, old, new in expected(workspace)])
    validate(workspace, plan)
    write(root / "delivery-plan.json", plan)
    return dict(passed=True, files=len(plan["files"]))


def verify_installed(workspace):
    root = workspace / ROOT
    path = root / "installed.json"
    if not path.is_file() or not read(path).get("installed"):
        return {}
    receipt = read(path)
    plan = root / "delivery-plan.json"
    assert receipt["phase"] == "complete" and receipt["plan_sha256"] == digest(plan)
    return validate(workspace, read(plan), after=True)


if __name__ == "__main__":
    from central_activation_receipts import verify_files
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    assert verify_files(workspace)["connacht_npc_figures_installed"]
    root = workspace / ROOT
    if args.apply:
        plan = read(root / "delivery-plan.json")
        validate(workspace, plan)
        result = apply_delivery(workspace, root, "ConnachtModelFlags", plan, "connacht_npc_model_flags_installed")
    else:
        result = prepare(workspace)
    print(json.dumps(result))
