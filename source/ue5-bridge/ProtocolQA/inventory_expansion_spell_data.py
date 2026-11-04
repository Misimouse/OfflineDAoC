"""Inventory original expansion spell data against marked QA; never enable or insert a class."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from prepare_bainshee_probe_data import COMMIT, HASHES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--server-source', required=True, type=Path, help='GameServer source folder')
    parser.add_argument('--class-id', required=True, type=int, choices=[58, 62])
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    root = args.workspace.resolve()
    assert args.output.resolve().is_relative_to(root / 'Reports')
    prepared = json.loads((root / 'Reports/protocol_qa/prepared.json').read_text())
    run = Path(prepared['root']).resolve()
    database = Path(prepared['database']).resolve()
    assert run.is_relative_to(root / 'ProtocolQA') and database.is_relative_to(run)
    reference = root / 'References' / ('DOLPublic_' + COMMIT[:12])
    source = {}
    for name, expected in HASHES.items():
        raw = (reference / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == expected, name
        source[name] = json.loads(raw)
    spells = {int(row['SpellID']): row for row in source['Spell.json']}
    with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as db:
        assert db.execute('SELECT RunId FROM CodexQaIsolationMarker').fetchone()[0] == run.name
        lines = [{'name': name, 'spec': spec, 'current_links': count} for name, spec, count in db.execute(
            'SELECT l.KeyName,l.Spec,COUNT(x.SpellID) FROM SpellLine l LEFT JOIN LineXSpell x ON x.LineName=l.KeyName '
            'WHERE l.Spec IN (SELECT SpecKeyName FROM ClassXSpecialization WHERE ClassID=?) '
            'GROUP BY l.KeyName ORDER BY l.KeyName', (args.class_id,))]
        assert len(lines) == 3, 'Review changed career structure'
        names = {line['name'] for line in lines}
        links = [row for row in source['LineXSpell.json'] if row['LineName'] in names]
        ids = sorted({int(row['SpellID']) for row in links})
        assert ids and all(spell_id in spells for spell_id in ids)
        existing = {int(row[0]) for row in db.execute('SELECT SpellID FROM Spell')}
    handlers = {}
    pattern = re.compile(r'\[SpellHandler\(eSpellType\.(\w+)\)\]\s*(?:public|internal)\s+(?:(abstract|sealed)\s+)?class\s+(\w+)', re.S)
    for path in (args.server_source / 'spells').rglob('*.cs'):
        for kind, modifier, name in pattern.findall(path.read_text(encoding='utf-8-sig')):
            handlers.setdefault(kind, []).append({'class': name, 'abstract': modifier == 'abstract',
                                                 'source': str(path.relative_to(args.server_source))})
    types = sorted({spells[spell_id]['Type'] for spell_id in ids})
    coverage = {kind: [entry for entry in handlers.get(kind, []) if not entry['abstract']] for kind in types}
    catalog = json.loads((root / 'Client/Plugins/DAoCVisualBridge/Content/SpellVisuals_v01/catalog.json').read_text())
    effects = sorted({int(spells[spell_id]['ClientEffect']) for spell_id in ids if int(spells[spell_id]['ClientEffect']) > 0})
    missing_effects = []
    resources = set()
    for effect_id in effects:
        definition = catalog['effects'].get(str(effect_id))
        if definition is None:
            missing_effects.append(effect_id)
            continue
        resources.update(int(value) for value in definition.get('gather', []) + definition.get('cast_fx', []) if int(value) > 0)
        resources.update(int(definition[key]) for key in ['projectile', 'target', 'buildup', 'pulse', 'resist'] if int(definition.get(key, 0)) > 0)
    for line in lines:
        line['reference_links'] = len([row for row in links if row['LineName'] == line['name']])
    report = {'read_only': True, 'class_enabled': False, 'database_modified': False, 'class_id': args.class_id,
              'source_commit': COMMIT, 'source_hashes': HASHES, 'lines': lines,
              'reference_spells': len(ids), 'reference_links': len(links), 'spell_types': types,
              'existing_spell_ids_requiring_comparison': sorted(set(ids) & existing),
              'concrete_handler_source_coverage': coverage,
              'types_without_concrete_source_handler': [kind for kind, entries in coverage.items() if not entries],
              'missing_effect_definitions': missing_effects,
              'referenced_fx_resources': len(resources),
              'missing_fx_resources': sorted(value for value in resources if str(value) not in catalog['fx']),
              'not_certified': ['runtime handler registration', 'spell semantics', 'race eligibility',
                                'starting class and training', 'native appearance', 'owner visual acceptance']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({key: report[key] for key in ['class_id', 'read_only', 'reference_spells', 'reference_links',
                                                   'types_without_concrete_source_handler', 'missing_effect_definitions', 'missing_fx_resources']}))


if __name__ == '__main__':
    main()
