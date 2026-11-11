"""Find missing NPC equipment references in the persisted Connacht world."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sqlite3

from audit_connacht_npc_models import read
from audit_connacht_runtime_models import template_models
from prepare_combined_expansion_data import digest

BODY_SLOTS = {22: "gloves", 23: "boots", 25: "body", 26: "cloak", 27: "legs", 28: "arms"}


def audit(workspace, install):
    lab = workspace / "ConnachtNpcCoverageLab"
    zone_path = install / "new-client/godot/content/zones/zones_index.json"
    db_path = install / "runtime/data/opendaoc.sqlite3.db"
    wal = db_path.with_name(db_path.name + "-wal")
    assert not wal.exists() or not wal.stat().st_size
    game = install / "new-client/godot/content"
    original_models = game / "monsters/monsters.json"
    original_armour = game / "characters/armor.json"
    original_helms = game / "helms/helms.json"
    catalogue = workspace / "models.json"
    equipment_path = workspace / "equipment_catalog_v01.json"
    inputs = {str(path): digest(path) for path in (zone_path, db_path, catalogue, equipment_path, original_models, original_armour, original_helms)}
    zone = read(zone_path)["207"]
    x, y = int(zone["x"]) * 8192, int(zone["y"]) * 8192
    with sqlite3.connect(db_path.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        placed = db.execute(
            """SELECT Name, Model, EquipmentTemplateID, NPCTemplateID, COUNT(*) FROM Mob
               WHERE Region=? AND X>=? AND X<? AND Y>=? AND Y<?
               GROUP BY Name, Model, EquipmentTemplateID, NPCTemplateID""",
            (zone["region"], x, x + int(zone["w"]) * 8192, y, y + int(zone["h"]) * 8192),
        ).fetchall()
        templates = defaultdict(list)
        for template, model, gear, replace in db.execute(
            "SELECT TemplateId, Model, EquipmentTemplateID, ReplaceMobValues FROM NpcTemplate"
        ):
            templates[template].append((model, gear, replace))
        gear_rows = defaultdict(set)
        for template, slot, model in db.execute("SELECT TemplateID, Slot, Model FROM NPCEquipment"):
            gear_rows[template].add((slot, model))
    models = read(catalogue)
    definitions = read(original_models)
    source_armour = read(original_armour)["models"]
    source_helms = read(original_helms)["models"]
    equipment = read(equipment_path)
    armour = equipment["armour"]
    content = workspace / "Client/Plugins/DAoCVisualBridge/Content"

    def has_asset(entry):
        package = entry.get("asset", "").partition(".")[0]
        if not package.startswith("/DAoCVisualBridge/"):
            return False
        return (content / (package.removeprefix("/DAoCVisualBridge/") + ".uasset")).is_file()

    def item_gap(figure_id, figure, slot, model):
        key = str(model)
        if 10 <= slot <= 13:
            return "" if has_asset(equipment["models"].get(key, {})) else "weapon_asset_missing"
        race = definitions.get(str(figure_id), {}).get("race", "")
        if not race or (slot not in BODY_SLOTS and slot != 21):
            return ""
        gender = "f" if race.endswith("_f") else "m"
        if slot == 21:
            if race not in source_helms.get(key, {}):
                return ""
        elif BODY_SLOTS[slot] not in source_armour.get(key, {}).get(gender, {}):
            return ""
        body = armour["figures"].get(figure.get("asset"))
        if not body:
            return "body_equipment_not_modular"
        if slot == 21:
            helmet = armour["helmets"].get(body["base_id"], {}).get(key, {})
            return "" if has_asset(helmet) else "helmet_asset_missing"
        part = BODY_SLOTS[slot]
        piece = armour["models"].get(key, {}).get(body["gender"], {}).get(part)
        if not piece:
            return "armour_descriptor_missing"
        variant, texture = piece[:2]
        supported = bool(body.get("cloaks")) if slot == 26 else int(variant) in body["variants"].get(part, [])
        if not supported:
            return "armour_variant_missing"
        return "" if has_asset({"asset": armour["textures"].get(texture, "")}) else "armour_texture_missing"

    placed_count = Counter()
    gaps = Counter()
    examples = defaultdict(set)
    for name, model, direct, template, count in placed:
        choices = set()
        for alternate_model, alternate_gear, replace in templates.get(template, [(None, None, False)]):
            model_options = template_models(alternate_model, model) if replace else {model}
            if replace and alternate_gear:
                assert ":" not in alternate_gear, "This dataset contains inline equipment templates"
                gear_ids = [entry for entry in alternate_gear.split(";") if entry]
            else:
                gear_ids = [direct]
            for option in model_options:
                for gear_id in gear_ids:
                    choices.add((option & 0x7FFF, gear_id if gear_id in gear_rows else direct))
        if not any(gear_rows.get(g) for _, g in choices):
            placed_count["without_equipment_rows"] += count
            continue
        found = set()
        for option, gear in choices:
            figure = models[str(option)]
            for slot, item in gear_rows.get(gear, ()):
                if gap := item_gap(option, figure, slot, item):
                    found.add((gap, option, slot, item))
        placed_count["equipment_gap_possible" if found else "equipment_references_available"] += count
        for gap in found:
            gaps[gap] += count
            examples[gap].add(name)
    assert sum(placed_count.values()) == sum(row[4] for row in placed)
    assert not wal.exists() or not wal.stat().st_size
    assert all(digest(Path(path)) == sha for path, sha in inputs.items())
    report = dict(passed=True, counts=dict(placed_count), inputs=inputs, database_modified=False,
                  gaps=[dict(reason=reason, figure=figure, slot=slot, item=item, possible_spawns=count,
                             examples=sorted(examples[(reason, figure, slot, item)])[:4])
                        for (reason, figure, slot, item), count in gaps.most_common()])
    path = lab / "npc_equipment_audit.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return dict(passed=True, counts=report["counts"], gap_classes=dict(Counter(row["reason"] for row in report["gaps"])), report=str(path))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("workspace", "install"):
        parser.add_argument("--" + key, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.workspace.resolve(), args.install.resolve())))
