"""Audit possible NPC models after OfflineDAoC applies replacing templates."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sqlite3

from audit_connacht_npc_models import read
from prepare_combined_expansion_data import digest


def template_models(value, fallback):
    """Mirror the semicolon list and numeric ranges used by GameNPC.HandleModel."""
    options = set()
    for item in (value or "").split(";"):
        if not item:
            continue
        fields = item.split("-")
        try:
            if len(fields) == 1:
                model = int(fields[0])
                options.add(model if 0 <= model <= 65535 else fallback)
                continue
            start, end = sorted(map(int, fields[:2]))
        except ValueError:
            if len(fields) == 1:
                options.add(fallback)
            continue
        options.update(range(max(0, start), min(65535, end) + 1))
        if start < 0 or end > 65535:
            options.add(fallback)
    return options or {fallback}


def audit(workspace, install):
    lab = workspace / "ConnachtNpcCoverageLab"
    audit_path = lab / "audit_after_figures.json"
    prior = read(audit_path)
    assert prior["passed"] and not prior["database_modified"]
    database = install / "runtime/data/opendaoc.sqlite3.db"
    wal = database.with_name(database.name + "-wal")
    assert not wal.exists() or not wal.stat().st_size
    catalog = workspace / "models.json"
    zones = install / "new-client/godot/content/zones/zones_index.json"
    game = install / "new-client/godot"
    definitions = game / "content/monsters/monsters.json"
    inputs = {str(path): digest(path) for path in (audit_path, catalog, database, zones, definitions)}
    assert all(prior["sources"][str(path)] == inputs[str(path)] for path in (catalog, database, zones))
    zone = read(zones)[str(prior["zone"])]
    x, y = int(zone["x"]) * 8192, int(zone["y"]) * 8192
    with sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True) as conn:
        placements = conn.execute(
            """SELECT Name, Model, NPCTemplateID, COUNT(*) FROM Mob
               WHERE Region=? AND X>=? AND X<? AND Y>=? AND Y<?
               GROUP BY Name, Model, NPCTemplateID""",
            (prior["region"], x, x + int(zone["w"]) * 8192, y, y + int(zone["h"]) * 8192),
        ).fetchall()
        templates = defaultdict(list)
        for key, model, replace in conn.execute("SELECT TemplateId, Model, ReplaceMobValues FROM NpcTemplate"):
            templates[key].append((model, replace))
    statuses = {row["model_id"]: row["status"] for row in prior["models"]}
    models, original = read(catalog), read(definitions)
    content = workspace / "Client/Plugins/DAoCVisualBridge/Content"

    def model_status(model):
        entry = models.get(str(model), {})
        kind = entry.get("type")
        if kind in {"hidden", "effect_body"}:
            return kind
        package = entry.get("asset", "").partition(".")[0]
        if package.startswith("/DAoCVisualBridge/"):
            path = content / (package.removeprefix("/DAoCVisualBridge/") + ".uasset")
            return "imported" if path.is_file() else "catalogue_asset_missing"
        if model in statuses:
            return statuses[model]
        info = original.get(str(model), {})
        if info.get("race"):
            return "original_figure_available"
        gltf = info.get("gltf", "")
        if gltf.startswith("res://"):
            path = game / gltf.removeprefix("res://")
            if path.is_file():
                return "original_mesh_available" if read(path).get("meshes") else "original_body_missing"
        return "original_source_missing"

    supported = {"imported", "effect_body", "hidden"}
    tagged = Counter()
    original_coverage = Counter()
    coverage = Counter()
    remaining = Counter()
    overrides = []
    for name, stored, template_id, count in placements:
        possible = set()
        for value, replace in templates.get(template_id, [(None, False)]):
            possible.update(template_models(value, stored) if replace else {stored})
        def summarize(options):
            values = {model_status(model) for model in options}
            if values <= supported:
                return "covered"
            return next(iter(values)) if len(values) == 1 else "mixed"

        status = summarize(possible)
        original_coverage[summarize({model & 0x7FFF for model in possible})] += count
        for model in possible:
            if model & 0x8000:
                tagged[model] += count
        coverage[status] += count
        if status != "covered":
            for model in possible:
                if model_status(model) not in supported:
                    remaining[model] += count
        if possible != {stored}:
            overrides.append(dict(name=name, spawns=count, template=template_id, stored=stored,
                                  possible=sorted(possible), coverage=status))
    assert sum(coverage.values()) == prior["active_spawn_count"]
    assert not wal.exists() or not wal.stat().st_size
    assert all(digest(Path(path)) == expected for path, expected in inputs.items())
    result = dict(passed=True, scope="persisted Mob placements and database template options",
                  counts=dict(coverage), original_client_mask_counts=dict(original_coverage), high_bit_model_options=dict(tagged),
                  unresolved_model_possible_spawns=dict(remaining),
                  template_overrides=overrides, inputs=inputs, database_modified=False)
    target = lab / "audit_server_template_models.json"
    target.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return {key: result[key] for key in ("passed", "scope", "counts", "original_client_mask_counts", "high_bit_model_options", "unresolved_model_possible_spawns")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("workspace", "install"):
        parser.add_argument("--" + key, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.workspace.resolve(), args.install.resolve())))
