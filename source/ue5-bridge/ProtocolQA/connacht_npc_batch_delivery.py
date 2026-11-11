"""Activate the verified Connacht creature packages and additive catalogue."""
import argparse
import json
from pathlib import Path
import shutil

from inventory_quantity_receipts import compose
from quest_reward_delivery import apply_delivery, current, digest, read, write


def lab_root(workspace, batch):
    assert batch > 0
    return workspace / "ConnachtNpcCoverageLab" / f"Batch{batch}"


def pairs(workspace, root, proof):
    relative = Path("Plugins/DAoCVisualBridge/Content") / f"ConnachtNpc{root.name}_v01"
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


def validate(workspace, plan, batch=1, after=False, successors=None):
    root = lab_root(workspace, batch)
    successors = successors or {}
    if batch > 1:
        previous = lab_root(workspace, batch-1) / "installed.json"
        assert read(previous)["installed"] and plan["predecessor_sha256"] == digest(previous)
    proof_path = root / "verified.json"
    assert plan["proof_sha256"] == digest(proof_path)
    proof = read(proof_path)
    assert proof["passed"] and proof["model_ids"] and proof["checks"] == 24 + 16 * len(proof["model_ids"])
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
        expected_hash = row["after_sha256" if after else "before_sha256"]
        successor = successors.get(str(dst))
        if successor:
            assert after and successor["before_sha256"] == expected_hash
            expected_hash = successor["after_sha256"]
        assert current(dst) == expected_hash, str(dst)
    return rows


def prepare(workspace, batch):
    from central_activation_receipts import verify_files

    assert verify_files(workspace)["quest_map_installed"]
    root = lab_root(workspace, batch)
    proof_path = root / "verified.json"
    proof = read(proof_path)
    shutil.copy2(workspace / "models.json", root / "catalog_before.json")
    plan = dict(phase="prepared", proof_sha256=digest(proof_path),
                files=[dict(source=str(src), target=str(dst), before_sha256=current(dst), after_sha256=digest(src))
                       for src, dst in pairs(workspace, root, proof)])
    if batch > 1:
        plan["predecessor_sha256"] = digest(lab_root(workspace, batch-1) / "installed.json")
    validate(workspace, plan, batch)
    write(root / "delivery-plan.json", plan)
    return dict(passed=True, files=len(plan["files"]), model_ids=proof["model_ids"])


def verify_installed(workspace):
    plans = []
    batch = 1
    while True:
        root = lab_root(workspace, batch)
        receipt = root / "installed.json"
        if not receipt.is_file():
            break
        result = read(receipt)
        if not result.get("installed"):
            break
        plan = root / "delivery-plan.json"
        assert result["phase"] == "complete" and result["plan_sha256"] == digest(plan)
        plans.append((batch, read(plan)))
        batch += 1
    from connacht_npc_figure_delivery import verify_installed as verify_figures
    figure_rows = verify_figures(workspace)
    catalog = str(workspace / "models.json")
    rows = {catalog: figure_rows[catalog]} if catalog in figure_rows else {}
    for batch, plan in reversed(plans):
        rows = compose(validate(workspace, plan, batch, after=True, successors=rows), rows)
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--batch", type=int, default=1)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    if args.apply:
        from central_activation_receipts import verify_files
        assert verify_files(workspace)["quest_map_installed"]
        root = lab_root(workspace, args.batch)
        plan = read(root / "delivery-plan.json")
        validate(workspace, plan, args.batch)
        result = apply_delivery(workspace, root, f"ConnachtNpcBatch{args.batch}", plan, "connacht_npc_batch_installed")
    else:
        result = prepare(workspace, args.batch)
    print(json.dumps(result))
