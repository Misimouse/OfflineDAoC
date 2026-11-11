"""Activate the verified Connacht creature packages and additive catalogue."""
import argparse
import json
from pathlib import Path
import shutil

from quest_reward_delivery import apply_delivery, current, digest, read, write


NAMESPACE = "ConnachtNpcBatch1_v01"


def pairs(workspace, root, proof):
    relative = Path("Plugins/DAoCVisualBridge/Content") / NAMESPACE
    candidate = root / "AssetHost" / relative
    target = workspace / "Client" / relative
    for name, sha in proof["assets"].items():
        path = Path(name)
        assert not path.drive and not path.is_absolute() and ".." not in path.parts
        assert len(path.parts) >= 2 and path.suffix == ".uasset"
        assert path.parts[0] in {"Model_"+model for model in proof["model_ids"]}
        source = candidate / path
        assert source.resolve().is_relative_to(candidate) and digest(source) == sha
        assert (target / path).resolve().is_relative_to(target)
        yield source, target / path
    yield root / "candidate_catalog.json", workspace / "models.json"


def validate(workspace, plan, after=False):
    root = workspace / "ConnachtNpcCoverageLab/Batch1"
    proof_path = root / "verified.json"
    assert plan["proof_sha256"] == digest(proof_path)
    proof = read(proof_path)
    assert proof["passed"] and proof["checks"] >= 60 and len(proof["model_ids"]) == 3
    assert proof["export_sha256"] == digest(root / "export_verified.json")
    assert proof["native_sha256"] == digest(root / "entity_replay.json.native.json")
    assert proof["catalog_before_sha256"] == digest(root / "catalog_before.json")
    assert proof["candidate_sha256"] == digest(root / "candidate_catalog.json")
    before = read(root / "catalog_before.json")
    candidate = read(root / "candidate_catalog.json")
    assert set(candidate).difference(before) == set(proof["model_ids"])
    assert all(candidate.get(key) == value for key, value in before.items())
    expected = list(pairs(workspace, root, proof))
    rows = {row["target"]: row for row in plan["files"]}
    assert len(rows) == len(expected) == len(plan["files"]) and set(rows) == {str(dst) for _, dst in expected}
    for src, dst in expected:
        row = rows[str(dst)]
        assert row["source"] == str(src) and row["after_sha256"] == digest(src)
        original = proof["catalog_before_sha256"] if dst.name == "models.json" else None
        assert row["before_sha256"] == original
        assert current(dst) == row["after_sha256" if after else "before_sha256"], str(dst)
    return rows


def prepare(workspace):
    from central_activation_receipts import verify_files

    assert verify_files(workspace)["quest_map_installed"]
    root = workspace / "ConnachtNpcCoverageLab/Batch1"
    proof_path = root / "verified.json"
    proof = read(proof_path)
    shutil.copy2(workspace / "models.json", root / "catalog_before.json")
    plan = dict(phase="prepared", proof_sha256=digest(proof_path),
                files=[dict(source=str(src), target=str(dst), before_sha256=current(dst), after_sha256=digest(src))
                       for src, dst in pairs(workspace, root, proof)])
    validate(workspace, plan)
    write(root / "delivery-plan.json", plan)
    return dict(passed=True, files=len(plan["files"]), model_ids=proof["model_ids"])


def verify_installed(workspace):
    root = workspace / "ConnachtNpcCoverageLab/Batch1"
    path = root / "installed.json"
    if not path.is_file() or not read(path).get("installed"):
        return {}
    result = read(path)
    plan = root / "delivery-plan.json"
    assert result["phase"] == "complete" and result["plan_sha256"] == digest(plan)
    return validate(workspace, read(plan), after=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    if args.apply:
        from central_activation_receipts import verify_files
        assert verify_files(workspace)["quest_map_installed"]
        root = workspace / "ConnachtNpcCoverageLab/Batch1"
        plan = read(root / "delivery-plan.json")
        validate(workspace, plan)
        result = apply_delivery(workspace, root, "ConnachtNpcBatch1", plan, "connacht_npc_batch_installed")
    else:
        result = prepare(workspace)
    print(json.dumps(result))
