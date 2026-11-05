"""Compare pinned public world definitions with a disposable read-only installed snapshot."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

from audit_expansion_race_rules import verified_source
from snapshot_world_database import snapshot


def audit(workspace, install):
    refs = workspace/'References/DOLPublic_b5b29c2ada76'
    manifest = json.loads((refs/'catacombs_audit_manifest.json').read_text())
    assert manifest['commit'] == 'b5b29c2ada7695414b94f5fa110eb505a477d007'
    entries = {r['name']: r for r in manifest['tables']}

    def public(name):
        compressed = refs/(name+'.gz')
        if compressed.exists():
            raw = gzip.decompress(compressed.read_bytes())
            expected = entries[name]
            assert len(raw) == expected['bytes']
            assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() == expected['git_blob']
            return json.loads(raw.decode('utf-8-sig'))
        path = refs/(name+'.fetched')
        if not path.exists():
            path = refs/name
        return json.loads(verified_source(path, entries[name]['git_blob']))

    regions = {int(r['RegionID']): r for r in public('Regions.json')}
    cat = {rid for rid, r in regions.items() if int(r['Expansion']) == 3}
    counts, models, mob_ids = Counter(), set(), set()
    cat_mobs = []
    total = 0
    for index in range(5):
        rows = public(f'Mob.{index}.json')
        total += len(rows)
        for row in rows:
            if int(row['Region']) in cat:
                counts[int(row['Region'])] += 1
                models.add(int(row['Model']))
                mob_ids.add(row['Mob_ID'])
                cat_mobs.append(row)
    items = public('ItemTemplate.json')
    templates = public('NpcTemplate.json')
    equipment = public('NPCEquipment.json')
    instances = public('InstanceXElement.json')
    quests = public('DataQuest.json')
    assert 'Character_ID' in public('Quest.json')[0]  # Progress, never quest definitions.
    with snapshot(install/'runtime/data/opendaoc.sqlite3.db', workspace/'ExpansionRaceLab/TestTemp') as (db, evidence):
        table_counts = {t: db.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
                        for t in ['Regions', 'Mob', 'ItemTemplate', 'NpcTemplate', 'NPCEquipment', 'DataQuest', 'InstanceXElement']}
        installed_counts = dict(db.execute('SELECT Region,COUNT(*) FROM Mob GROUP BY Region').fetchall())
        installed_mob_ids = {r[0] for r in db.execute('SELECT Mob_ID FROM Mob')}
        installed_items = {r[0] for r in db.execute('SELECT Id_nb FROM ItemTemplate')}
        installed_templates = {str(r[0]) for r in db.execute('SELECT TemplateId FROM NpcTemplate')}
        installed_equipment = {str(r[0]) for r in db.execute('SELECT DISTINCT TemplateID FROM NPCEquipment')}
        installed_cat = {int(r[0]) for r in db.execute('SELECT RegionID FROM Regions WHERE Expansion=3')}
        installed_cat_mobs = sum(installed_counts.get(rid, 0) for rid in installed_cat)
    catalogue = json.loads((install/'new-client/godot/content/monsters/monsters.json').read_text(encoding='utf-8-sig'))
    direct_models = {int(k) for k in catalogue if str(k).isdigit()}
    native_catalogue = json.loads((workspace/'models.json').read_text(encoding='utf-8-sig'))
    native_models = {int(k) for k in native_catalogue if str(k).isdigit()}
    zone_index = json.loads((install/'new-client/godot/content/zones/zones_index.json').read_text(encoding='utf-8-sig'))
    cat_zones = {k: r for k, r in zone_index.items() if int(r['region']) in cat}
    referenced_templates = {str(r['NPCTemplateID']) for r in cat_mobs if r.get('NPCTemplateID') not in (None, '', 0, '0', -1, '-1')}
    public_templates = {str(r['TemplateId']): r for r in templates}
    referenced_equipment = {str(r['EquipmentTemplateID']) for r in cat_mobs if r.get('EquipmentTemplateID')}
    template_inventory = [str(public_templates[k]['EquipmentTemplateID']) for k in referenced_templates
                          if k in public_templates and public_templates[k].get('EquipmentTemplateID')]
    # GameNPC.HandleInventory: semicolon-separated template alternatives, or inline slot:model lists.
    referenced_equipment.update(part for value in template_inventory if ':' not in value
                                for part in value.split(';') if part)
    available_equipment = {str(r['TemplateID']) for r in equipment}
    # Identity overlap is a candidate inventory, not permission to overwrite matching content.
    region_report = [{'region_id': rid, 'name': regions[rid]['Description'],
                      'dol_mobs': counts[rid], 'installed_mobs': installed_counts.get(rid, 0)} for rid in sorted(cat)]
    result = {'passed': True, 'read_only': True, 'installed_version_165_confirmed': False,
              'reference': {'repository': manifest['repository'], 'commit': manifest['commit'], 'git_blobs_verified': True},
              'snapshot': evidence, 'installed_counts': table_counts,
              'dol_counts': {'Mob': total, 'ItemTemplate': len(items), 'NpcTemplate': len(templates),
                             'NPCEquipment': len(equipment), 'DataQuest': len(quests), 'InstanceXElement': len(instances)},
              'catacombs': {'dol_regions_declared': len(cat), 'dol_regions_populated': len(counts),
                            'dol_mobs': sum(counts.values()), 'dol_model_ids': len(models),
                            'installed_regions_declared': len(installed_cat), 'installed_mobs': installed_cat_mobs,
                            'installed_regions_populated': sum(installed_counts.get(rid, 0)>0 for rid in installed_cat),
                            'dol_spawn_ids_absent_installed': len(mob_ids-installed_mob_ids),
                            'direct_godot_model_entries': len(models & direct_models),
                            'direct_native_model_entries': len(models & native_models),
                            'indexed_godot_zones': len(cat_zones),
                            'indexed_godot_zones_marked_built': sum(bool(r.get('built')) for r in cat_zones.values()),
                            'without_direct_godot_model_entry': sorted(models-direct_models)},
              'catacombs_spawn_dependencies': {
                  'npc_template_ids_referenced': len(referenced_templates),
                  'npc_template_ids_absent_installed': sorted(referenced_templates-installed_templates),
                  'npc_template_ids_absent_public_reference': sorted(referenced_templates-set(public_templates)),
                  'equipment_template_ids_referenced': len(referenced_equipment),
                  'inline_inventory_definitions': sum(':' in value for value in template_inventory),
                  'equipment_template_ids_absent_installed': sorted(referenced_equipment-installed_equipment),
                  'equipment_template_ids_absent_public_reference': sorted(referenced_equipment-available_equipment)},
              'all_expansions_identity_comparison': {
                  'dol_item_ids_absent_installed': sum(r['Id_nb'] not in installed_items for r in items),
                  'dol_npc_template_ids_absent_installed': sum(str(r['TemplateId']) not in installed_templates for r in templates)},
              'instance_classes': dict(Counter(r['ClassType'] for r in instances)),
              'regions': region_report,
              'limitations': ['Expansion=3 is the DB Catacombs marker; metadata is not a historical client version certificate.',
                  'Missing direct model entries require checking human aliases and original assets; they do not prove absent art.',
                  'Public DOL data spans multiple expansions and is not a complete Catacombs package.',
                  'Armor Model IDs are not interchangeable with standalone weapon or monster mesh IDs.',
                  'Quest.json contains character progress and is excluded from migration candidates.',
                  'No records imported, class rules changed, or player progress modified.']}
    output = workspace/'Reports/catacombs_content_audit'
    output.mkdir(parents=True, exist_ok=True)
    (output/'comparison.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({k: result[k] for k in ['passed', 'dol_counts', 'catacombs', 'all_expansions_identity_comparison']}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--install', type=Path, required=True)
    args = parser.parse_args()
    audit(args.workspace.resolve(), args.install.resolve())
