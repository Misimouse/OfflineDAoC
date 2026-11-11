"""Deliver Connacht's remaining template-driven NPC representations."""
import argparse
import json
from pathlib import Path
import shutil

from quest_reward_delivery import apply_delivery, current, digest, read, write

LAB = "ConnachtNpcCoverageLab"
PACKAGE = "Figures/UnimportedRaces/NativeCandidate"
FIGURES = {"10", "34", "156"}
CREATURES = {"446", "128", "413", "447", "450"}
CATALOGUES = {
    "models.json": "models",
    "equipment_catalog_v01.json": "equipment",
    "Client/Plugins/DAoCVisualBridge/Content/ClassicUI/Pregame/appearance_catalog.json": "appearance",
}


def evidence(lab):
    package = lab / PACKAGE
    return [
        lab / "ModelFlags/installed.json", lab / "audit_server_template_models.json",
        lab / "Batch4/verified.json", lab / "Batch4/entity_replay.json.native.json",
        package / "native_import.json", package / "native_outfit_import.json",
        package / "Reports/appearance/import_parts.json", package / "textures_verified.json",
        package / "native_replay.json.native.json",
    ]


def expected(workspace, root):
    lab = workspace / LAB
    package = lab / PACKAGE
    plugin = Path("Plugins/DAoCVisualBridge/Content")
    before = {key: read(root / f"{key}_before.json") for key in CATALOGUES.values()}
    catalog = read(lab / "Batch4/candidate_catalog.json")
    figures = read(package / "models_combined.json")
    assert catalog.keys() - before["models"].keys() == CREATURES
    assert figures.keys() - before["models"].keys() == FIGURES
    assert all(catalog[k] == figures[k] == value for k, value in before["models"].items())
    assert digest(lab / "Batch4/candidate_catalog.json") == read(lab / "Batch4/verified.json")["candidate_sha256"]
    models = dict(catalog, **{key: figures[key] for key in sorted(FIGURES)})
    models["665"] = {"type": "hidden", "ghost_render": {"known": True, "race_figure": False, "effect_only": False}}
    equipment = read(package / "equipment_combined.json")
    armour = equipment["armour"]
    old_armour = before["equipment"]["armour"]
    assert {k: v for k, v in equipment.items() if k != "armour"} == {k: v for k, v in before["equipment"].items() if k != "armour"}
    assert {k: v for k, v in armour.items() if k not in ("figures", "textures")} == {
        k: v for k, v in old_armour.items() if k not in ("figures", "textures")
    }
    assert set(armour["figures"]) - set(old_armour["figures"]) == {models[k]["asset"] for k in ("34", "156")}
    appearance = read(package / "appearance_combined.json")
    assert set(appearance["figures"]) - set(before["appearance"]["figures"]) == {"34", "156"}
    assert {k: v for k, v in appearance.items() if k not in ("figures", "textures")} == {
        k: v for k, v in before["appearance"].items() if k not in ("figures", "textures")
    }
    for original, amended in ((old_armour, armour), (before["appearance"], appearance)):
        for key in ("figures", "textures"):
            assert all(amended[key][name] == entry for name, entry in original[key].items())
    payloads = {"models": models, "equipment": equipment, "appearance": appearance}
    for rel, key in CATALOGUES.items():
        payload = root / f"{key}_candidate.json"
        assert read(payload) == payloads[key]
        yield payload, workspace / rel, digest(root / f"{key}_before.json")
    batch = lab / "Batch4/AssetHost" / plugin / "ConnachtNpcBatch4_v01"
    proof = read(lab / "Batch4/verified.json")
    assert proof["passed"] and proof["checks"] == 104 and set(proof["model_ids"]) == CREATURES
    for name, sha in sorted(proof["assets"].items()):
        asset = (batch / name).resolve()
        assert asset.is_relative_to(batch) and asset.suffix == ".uasset" and digest(asset) == sha
        yield asset, workspace / "Client" / plugin / batch.name / name, None
    source = lab / "Figures/UnimportedRaces/NativeHost" / plugin
    for namespace in ("ExpansionRaces_v01", "ExpansionOutfits_v01", "ConnachtNpcExtraAppearance_v01"):
        folder = source / namespace
        assert folder.is_dir() and folder.resolve().is_relative_to(source)
        for asset in sorted(folder.rglob("*.uasset")):
            assert asset.resolve().is_relative_to(folder)
            yield asset, workspace / "Client" / plugin / asset.relative_to(source), None


def validate(workspace, plan, installed=False):
    lab = workspace / LAB
    root = lab / "FinalCoverage"
    assert plan["evidence"] == {str(p): digest(p) for p in evidence(lab)}
    package = lab / PACKAGE
    for path in evidence(lab):
        if path.suffix == ".json" and path.name != "installed.json":
            assert read(path)["passed"], path
    assert read(package / "native_replay.json.native.json")["checks"] == 117
    rows = {}
    for src, dst, before in expected(workspace, root):
        after = digest(src)
        assert current(dst) == (after if installed else before), str(dst)
        rows[str(dst)] = dict(source=str(src), target=str(dst), before_sha256=before, after_sha256=after)
    assert list(rows.values()) == plan["files"]
    return rows


def prepare(workspace):
    lab = workspace / LAB
    root = lab / "FinalCoverage"
    assert not (root / "installed.json").exists()
    root.mkdir(exist_ok=True)
    for rel, key in CATALOGUES.items():
        shutil.copy2(workspace / rel, root / f"{key}_before.json")
    package = lab / PACKAGE
    models = read(lab / "Batch4/candidate_catalog.json")
    models.update({k: read(package / "models_combined.json")[k] for k in sorted(FIGURES)})
    models["665"] = {"type": "hidden", "ghost_render": {"known": True, "race_figure": False, "effect_only": False}}
    write(root / "models_candidate.json", models)
    for key in ("appearance", "equipment"):
        shutil.copy2(package / f"{key}_combined.json", root / f"{key}_candidate.json")
    plan = dict(evidence={str(p): digest(p) for p in evidence(lab)},
                files=[dict(source=str(src), target=str(dst), before_sha256=before, after_sha256=digest(src))
                       for src, dst, before in expected(workspace, root)])
    validate(workspace, plan)
    write(root / "delivery-plan.json", plan)
    return dict(passed=True, files=len(plan["files"]))


def verify_installed(workspace):
    root = workspace / LAB / "FinalCoverage"
    path = root / "installed.json"
    if not path.is_file() or not read(path).get("installed"):
        return {}
    receipt = read(path)
    plan = root / "delivery-plan.json"
    assert receipt["phase"] == "complete" and receipt["plan_sha256"] == digest(plan)
    return validate(workspace, read(plan), installed=True)


if __name__ == "__main__":
    from central_activation_receipts import verify_files
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    assert verify_files(workspace)["connacht_npc_model_flags_installed"]
    root = workspace / LAB / "FinalCoverage"
    if args.apply:
        plan = read(root / "delivery-plan.json")
        validate(workspace, plan)
        result = apply_delivery(workspace, root, "ConnachtTemplateModels", plan, "connacht_npc_templates_installed")
    else:
        result = prepare(workspace)
    print(json.dumps(result))
