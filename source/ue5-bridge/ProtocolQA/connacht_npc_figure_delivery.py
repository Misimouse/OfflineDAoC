"""Install the verified original humanoid figures and appearance consumer."""
import argparse
import json
from pathlib import Path
import shutil

from inventory_quantity_receipts import compose, latest
from quest_reward_delivery import BINARIES, NATIVE, SOURCE, apply_delivery, current, digest, read, write

CHANGED = {
    "Private/DAoCBridgeAppearance.cpp",
    "Private/DAoCBridgeAppearance.h",
    "Private/DAoCBridgeEntityAcceptance.cpp",
    "Private/DAoCBridgeEquipment.cpp",
}
ROOT = "ConnachtNpcCoverageLab/Figures"


def expected(workspace):
    root = workspace / ROOT
    build_path = root / "native_build.json"
    build = read(build_path)
    prior = read(workspace / "QuestMapLab/native_build.json")
    before, after = [{Path(k).as_posix(): v for k, v in item["source_sha256"].items()} for item in (prior, build)]
    assert before.keys() == after.keys()
    assert {key for key in after if before[key] != after[key]} == {"DAoCVisualBridge/" + name for name in CHANGED}
    assert build["passed"] and build["normal_binary_sha256"] == prior["binaries_sha256"][BINARIES[0]]
    candidate = read(root / "candidate_verified.json")
    catalog = root / "candidate_catalog.json"
    assert candidate["passed"] and digest(catalog) == candidate["candidate_sha256"]
    native = read(root / "appearance_replay.json.native.json")
    assert native["passed"] and not native["failures"] and native["native_actor_consumer"]
    fixture = read(root / "appearance_replay.json")
    ids = {row["model"] for row in candidate["verified_models"]}
    assert len(fixture["cases"]) == 5 and len(ids) == 37 and native["checks"] == 24 + 20 * len(ids)
    assert all({row["model_id"] for row in case["snapshot"]["entities"] if row.get("expected_face_texture")} == ids
               for case in fixture["cases"][:-1])
    normal = workspace / "Client/Plugins/DAoCVisualBridge"
    compiled = Path(build["project"]).parent / "Plugins/DAoCVisualBridge"
    assert compiled.resolve().is_relative_to(root)
    rows = []
    for name in BINARIES:
        rel = Path("Binaries/Win64") / name
        rows.append((compiled / rel, normal / rel, prior["binaries_sha256"][name], build["binaries_sha256"][name]))
    for name in sorted(CHANGED):
        rel = "DAoCVisualBridge/" + name
        rows.append((root / "CandidateSource" / rel, normal / "Source" / rel, before[rel], after[rel]))
    catalog_before = candidate["inputs"][str(workspace / "models.json")]
    rows.append((catalog, workspace / "models.json", catalog_before, candidate["candidate_sha256"]))
    return rows


def validate(workspace, plan, after=False, successors=None):
    successors = successors or {}
    assert plan["predecessor"] == digest(workspace / "ConnachtNpcCoverageLab/Batch3/installed.json")
    assert all(digest(Path(path)) == sha for path, sha in plan["proofs"].items())
    rows = {}
    for src, dst, old, new in expected(workspace):
        row = dict(source=str(src), target=str(dst), before_sha256=old, after_sha256=new)
        expected_hash = latest(successors, row, new) if after else old
        assert digest(src) == new and current(dst) == expected_hash, str(dst)
        rows[str(dst)] = row
    assert list(rows.values()) == plan["files"]
    return rows


def prepare(workspace):
    from central_activation_receipts import verify_files
    assert verify_files(workspace)["connacht_npc_batch_installed"]
    root = workspace / ROOT
    for name in CHANGED:
        rel = Path("DAoCVisualBridge") / name
        target = root / "CandidateSource" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SOURCE / NATIVE / rel, target)
    proof_names = ("native_build.json", "candidate_verified.json", "appearance_replay.json", "appearance_replay.json.native.json")
    plan = dict(
        predecessor=digest(workspace / "ConnachtNpcCoverageLab/Batch3/installed.json"),
        proofs={str(root / name): digest(root / name) for name in proof_names},
        files=[dict(source=str(src), target=str(dst), before_sha256=old, after_sha256=new)
               for src, dst, old, new in expected(workspace)],
    )
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
    from connacht_npc_model_flag_delivery import verify_installed as verify_flags
    successors = verify_flags(workspace)
    return compose(validate(workspace, read(plan), after=True, successors=successors), successors)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    root = workspace / ROOT
    if args.apply:
        from central_activation_receipts import verify_files
        assert verify_files(workspace)["connacht_npc_batch_installed"]
        plan = read(root / "delivery-plan.json")
        validate(workspace, plan)
        result = apply_delivery(workspace, root, "ConnachtNpcFigures", plan, "connacht_npc_figures_installed")
    else:
        result = prepare(workspace)
    print(json.dumps(result))
