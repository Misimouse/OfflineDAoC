"""Prepare original modular bodies for missing Connacht NPCs in a private candidate."""
import argparse
from collections import Counter
import json
from pathlib import Path

from audit_connacht_npc_models import read
from prepare_combined_expansion_data import digest
from prepare_npc_visual_catalog import classification


def package_path(content, reference):
    mount = "/DAoCVisualBridge/"
    assert reference.startswith(mount), reference
    package = reference.removeprefix(mount).split(".", 1)[0]
    path = (content / (package + ".uasset")).resolve()
    assert path.is_relative_to(content) and path.is_file(), reference
    return path


def prepare(workspace, install):
    lab = workspace / "ConnachtNpcCoverageLab"
    plugin = workspace / "Client/Plugins/DAoCVisualBridge/Content"
    catalog_path = workspace / "models.json"
    audit_path = lab / "audit_after_batch3.json"
    source = install / "new-client/godot/content/monsters/monsters.json"
    appearance_path = plugin / "ClassicUI/Pregame/appearance_catalog.json"
    equipment_path = workspace / "equipment_catalog_v01.json"
    inputs = {str(path): digest(path) for path in (catalog_path, audit_path, source, appearance_path, equipment_path)}
    audit = read(audit_path)
    assert audit["passed"] and not audit["database_modified"]
    for path in (catalog_path, source):
        assert audit["sources"][str(path)] == inputs[str(path)]
    models, original = read(catalog_path), read(source)
    armour = read(equipment_path)["armour"]["figures"]
    appearance = read(appearance_path)["figures"]
    bases = {entry["meta"]["prefix"]: key for key, entry in appearance.items() if key in models}
    candidate = dict(models)
    proof_rows = []
    unresolved = Counter()
    for row in audit["models"]:
        if row["status"] != "original_figure_available" or not row["active_spawns"]:
            continue
        key = str(row["model_id"])
        assert key not in models
        info = original[key]
        race = info["race"]
        base_id = bases.get(race)
        if base_id is None:
            unresolved[race] += row["active_spawns"]
            continue
        reference = original[base_id]
        assert reference["race"] == race and reference["figure"].casefold() == info["figure"].casefold(), (key, base_id)
        base = models[base_id]
        assert base["type"] == "skeletal" and base["asset"] in armour
        assert base["scale"] == 1.0 and armour[base["asset"]]["base_id"] == base_id
        # The original NPC loader uses the already sized race figure, then
        # multiplies by the size in NPCCreate. Applying monsters.json scale
        # here as well would shrink Lurikeens and enlarge Firbolgs twice.
        for field in ("asset", "idle", "walk", "run", "death"):
            path = package_path(plugin, base[field])
            inputs[str(path)] = digest(path)
        entry = dict(base, name=info["name"], npc_appearance_model=int(base_id),
                     ghost_render=classification(info))
        candidate[key] = entry
        proof_rows.append(dict(model=int(key), race=race, appearance_model=int(base_id),
                               spawns=row["active_spawns"]))
    assert sum(row["spawns"] for row in proof_rows) + sum(unresolved.values()) == audit["active_spawns_by_status"]["original_figure_available"]
    assert all(candidate[key] == value for key, value in models.items())
    assert all(digest(Path(path)) == expected for path, expected in inputs.items())
    target = lab / "Figures"
    target.mkdir(exist_ok=True)
    catalogue = target / "candidate_catalog.json"
    catalogue.write_text(json.dumps(candidate, indent=2), encoding="utf-8")
    proof = dict(passed=True, installed=False, verified_models=proof_rows, unresolved_races=dict(unresolved),
                 candidate_sha256=digest(catalogue), inputs=inputs)
    (target / "candidate_verified.json").write_text(json.dumps(proof, indent=2), encoding="utf-8")
    return dict(passed=True, candidate_models=len(proof_rows), candidate_spawns=sum(row["spawns"] for row in proof_rows),
                unresolved_races=dict(unresolved), catalogue=str(catalogue))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("workspace", "install"):
        parser.add_argument("--" + option, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.workspace.resolve(), args.install.resolve())))
