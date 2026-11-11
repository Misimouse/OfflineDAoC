"""Measure Connacht NPC model coverage in the active client and pinned DOL world data."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sqlite3

from prepare_combined_expansion_data import digest


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def audit(workspace, install, reference, installed_batch=0, after_figures=False, after_templates=False):
    game = install / "new-client/godot"
    content = workspace / "Client/Plugins/DAoCVisualBridge/Content"
    zone_path = game / "content/zones/zones_index.json"
    monsters_path = game / "content/monsters/monsters.json"
    catalog_path = workspace / "models.json"
    receipt_path = reference / "downloaded_tables.json"
    receipt = read(receipt_path)
    assert receipt["passed"] and receipt["repository"] == "Dawn-of-Light/db-public"
    assert receipt["commit"] == "b5b29c2ada7695414b94f5fa110eb505a477d007"
    sources = {str(path): digest(path) for path in (zone_path, monsters_path, catalog_path, receipt_path)}
    zone = read(zone_path)["207"]
    region = int(zone["region"])
    x, y = int(zone["x"]) * 8192, int(zone["y"]) * 8192
    right, bottom = x + int(zone["w"]) * 8192, y + int(zone["h"]) * 8192

    database = install / "runtime/data/opendaoc.sqlite3.db"
    wal = database.with_name(database.name + "-wal")
    assert not wal.exists() or not wal.stat().st_size, "The active database has outstanding WAL changes"
    sources[str(database)] = digest(database)
    with sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        active_rows = db.execute(
            "SELECT Model, Name, COUNT(*) FROM Mob WHERE Region=? AND X>=? AND X<? AND Y>=? AND Y<? GROUP BY Model,Name",
            (region, x, right, y, bottom),
        ).fetchall()
    active = Counter()
    examples = {}
    for model, name, count in active_rows:
        key = str(model)
        active[key] += count
        if len(examples.setdefault(key, [])) < 4:
            examples[key].append(name)
    upstream = Counter()
    tables = {row["name"]: row for row in receipt["tables"] if row["name"].startswith("Mob.")}
    assert set(tables) == {f"Mob.{index}.json" for index in range(5)}
    for name, row in sorted(tables.items()):
        path = reference / name
        sources[str(path)] = digest(path)
        assert sources[str(path)] == row["sha256"], f"Pinned DOL table changed: {name}"
        for mob in read(path):
            if int(mob["Region"]) == region and x <= int(mob["X"]) < right and y <= int(mob["Y"]) < bottom:
                upstream[str(mob["Model"])] += 1

    catalog = read(catalog_path)
    monsters = read(monsters_path)
    models = []
    for model in sorted(active.keys() | upstream.keys(), key=lambda key: (-active[key], -upstream[key], int(key))):
        original = monsters.get(model, {})
        imported = catalog.get(model, {})
        gltf = original.get("gltf", "")
        race = original.get("race", "")
        source = game / gltf.removeprefix("res://") if gltf.startswith("res://") else None
        if race:
            source = game / "content/characters/races" / race / "figure.json"
        asset = imported.get("asset", "")
        package = asset.split(".", 1)[0]
        asset_file = content / (package.removeprefix("/DAoCVisualBridge/") + ".uasset")
        kind = imported.get("type", "")
        if kind in ("hidden", "effect_body"):
            status = kind
        elif imported:
            status = "imported" if package.startswith("/DAoCVisualBridge/") and asset_file.is_file() else "catalogue_asset_missing"
        elif str(original.get("figure", "")).casefold() == "invisible":
            status = "original_invisible"
        elif source and source.is_file():
            if race:
                status = "original_figure_available"
            else:
                status = "original_mesh_available" if read(source).get("meshes") else "original_body_missing"
        else:
            status = "original_source_missing"
        models.append(dict(model_id=int(model), active_spawns=active[model], dol_reference_spawns=upstream[model],
                           names=examples.get(model, []), original_name=original.get("name", ""), status=status,
                           original_source=str(source) if source else None, imported_asset=asset or None))
    counts = Counter()
    for row in models:
        counts[row["status"]] += row["active_spawns"]
    assert not wal.exists() or not wal.stat().st_size
    assert all(digest(Path(path)) == sha for path, sha in sources.items())
    proof = dict(passed=True, zone=207, region=region, active_spawn_count=sum(active.values()),
                 active_unique_models=len(active), dol_reference_spawn_count=sum(upstream.values()),
                 dol_reference_unique_models=len(upstream), active_spawns_by_status=dict(counts),
                 sources=sources, models=models, database_modified=False)
    name = f"audit_after_batch{installed_batch}.json" if installed_batch else "audit.json"
    if after_figures:
        name = "audit_after_figures.json"
    if after_templates:
        name = "audit_after_templates.json"
    target = workspace / "ConnachtNpcCoverageLab" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(proof, indent=2), encoding="utf-8")
    return {key: value for key, value in proof.items() if key not in ("sources", "models")} | {"proof": str(target)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for key in ("workspace", "install", "reference"):
        parser.add_argument("--" + key, type=Path, required=True)
    parser.add_argument("--after-install", type=int, nargs="?", const=1, default=0)
    parser.add_argument("--after-figures", action="store_true")
    parser.add_argument("--after-templates", action="store_true")
    args = parser.parse_args()
    print(json.dumps(audit(args.workspace.resolve(), args.install.resolve(), args.reference.resolve(), args.after_install, args.after_figures, args.after_templates)))
