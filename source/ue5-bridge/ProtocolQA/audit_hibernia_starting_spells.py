"""Compare DOL and installed level-one base spell data without changing characters."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3


def baseline_spells(class_id, careers, lines, links, spells, level=1):
    specs = {r['SpecKeyName'] for r in careers if int(r['ClassID']) == class_id and int(r['LevelAcquired']) <= level}
    selected = []
    for spec in sorted(specs):
        candidates = [r for r in lines if r['Spec'] == spec and int(r['IsBaseLine'])]
        hinted = [r for r in candidates if int(r['ClassIDHint']) == class_id]
        selected.extend(hinted or [r for r in candidates if int(r['ClassIDHint']) == 0])
    names = {r['KeyName'] for r in selected}
    entries = []
    missing = []
    for row in links:
        if row['LineName'] not in names or int(row['Level']) > level:
            continue
        sid = int(row['SpellID'])
        if sid not in spells:
            missing.append(sid)
        else:
            entries.append({'line': row['LineName'], 'id': sid, 'name': spells[sid]['Name'], 'type': spells[sid]['Type'], 'effect': spells[sid]['ClientEffect']})
    return {'specs': sorted(specs), 'lines': sorted(names), 'spells': sorted(entries, key=lambda r: (r['line'], r['id'])), 'missing_spell_definitions': sorted(set(missing))}


def audit(reference, database, workspace, output, shar_level_five=False):
    reference, database, workspace, output = (p.resolve() for p in (reference, database, workspace, output))
    assert output.is_relative_to(workspace) and database.is_file() and output != database
    files = {}
    def load(relative):
        path = reference / relative
        raw = path.read_bytes()
        files[relative] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw.decode('utf-8-sig'))
    manifest = load('Skills/downloaded_tables.json')
    assert manifest['passed'] and manifest['repository'] == 'Dawn-of-Light/db-public'
    for row in manifest['tables']:
        path = reference / 'Skills' / row['name']
        raw = path.read_bytes()
        assert len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256']
    dol_careers = load('ClassXSpecialization.json.normalized')
    dol_lines = load('Skills/SpellLine.json')
    dol_links = load('LineXSpell.json')
    dol_spells = {int(r['SpellID']): r for r in load('Spell.json')}
    with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA query_only=ON')
        def table(name):
            assert name in ['ClassXSpecialization', 'SpellLine', 'LineXSpell', 'Spell']
            return [dict(r) for r in db.execute('SELECT * FROM "' + name + '"')]
        careers, lines, links = (table(n) for n in ['ClassXSpecialization', 'SpellLine', 'LineXSpell'])
        spells = {int(r['SpellID']): r for r in table('Spell')}
        progression = db.execute("SELECT Value FROM ServerProperty WHERE Key='start_as_base_class'").fetchone()[0]
    result = {'passed': False, 'read_only': True, 'database_written': False, 'personal_tables_read': False,
              'source_commit': manifest['commit'], 'reference_sha256': files,
              'start_as_base_class': progression, 'classes': [],
              'scope': 'Level-one baseline spell data for the five initial Hibernian classes. Does not simulate career abilities, trained specializations, higher ranks, effects rendering or promotions.'}
    classes=[(51, 'Magician'), (52, 'Guardian'), (53, 'Naturalist'), (54, 'Stalker'), (57, 'Forester')]
    level=1
    if shar_level_five:
        classes=[(42,'Mentalist'),(43,'Blademaster'),(44,'Hero'),(45,'Champion'),(50,'Ranger')]
        level=5
        result['scope']='Level-five baseline spell data for five Shar-compatible classes; not trained specialization spells, career abilities or native visual acceptance.'
    result['level']=level
    for cid, name in classes:
        dol = baseline_spells(cid, dol_careers, dol_lines, dol_links, dol_spells,level)
        installed = baseline_spells(cid, careers, lines, links, spells,level)
        expected = {r['name'] for r in dol['spells']}
        actual = {r['name'] for r in installed['spells']}
        original_by_id = {r['id']: r for r in dol['spells']}
        current_by_id = {r['id']: r for r in installed['spells']}
        differences = [{'id': sid, 'field': key, 'dol': original_by_id[sid][key], 'installed': current_by_id[sid][key]}
                       for sid in sorted(original_by_id.keys() & current_by_id.keys())
                       for key in ['name', 'type', 'effect'] if original_by_id[sid][key] != current_by_id[sid][key]]
        identity_matches = original_by_id.keys() == current_by_id.keys() and all(
            d['field'] == 'type' and d['dol'] == 'ArmorFactorBuff' and d['installed'] == 'BaseArmorFactorBuff'
            for d in differences)
        result['classes'].append({'id': cid, 'name': name, 'dol': dol, 'installed': installed,
                                  'missing_names': sorted(expected - actual), 'additional_names': sorted(actual - expected),
                                  'names_match': expected == actual, 'spell_ids_names_and_effects_match': identity_matches,
                                  'definition_differences': differences})
    result['handler_note'] = 'Type differences remain explicit: this fork uses concrete BaseArmorFactorBuff for the original abstract ArmorFactorBuff data. Do not overwrite working handler mappings with raw upstream rows.'
    result['passed'] = all(r['names_match'] and r['spell_ids_names_and_effects_match'] and not r['dol']['missing_spell_definitions'] and not r['installed']['missing_spell_definitions'] for r in result['classes'])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['reference', 'database', 'workspace', 'output']:
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--shar-level-five',action='store_true')
    args = parser.parse_args()
    result = audit(args.reference, args.database, args.workspace, args.output,args.shar_level_five)
    print(json.dumps({'passed': result['passed'], 'classes': [{'id': r['id'], 'names_match': r['names_match'], 'missing': r['missing_names'], 'additional': r['additional_names']} for r in result['classes']]}))
