"""Propose six missing original Hibernian starter templates without altering existing items."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3

SOURCE_COMMIT = 'b5b29c2ada7695414b94f5fa110eb505a477d007'
SOURCE_BLOB = 'f70bb323d72c5a9fe4ea2d780064ec10bc4dec1d'
EXPECTED = {'leaf_tacuil_gauntlets': (22, 386), 'leaf_tacuil_boots': (23, 387),
    'leaf_tacuil_sleeves': (28, 385), 'leaf_tacuil_leggings': (27, 384),
    'leaf_tacuil_vest': (25, 383), 'leaf_tacuil_helm': (21, 835)}


def prepare(reference, database):
    digest = hashlib.sha1()
    digest.update(b'blob ' + str(reference.stat().st_size).encode() + b'\0')
    with reference.open('rb') as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b''):
            digest.update(chunk)
    assert digest.hexdigest() == SOURCE_BLOB, 'Pinned DOL ItemTemplate Git blob changed'
    originals = {row['Id_nb']: row for row in json.loads(reference.read_text(encoding='utf-8-sig'))
                 if row.get('Id_nb') in EXPECTED}
    assert set(originals) == set(EXPECTED)
    inserts, existing, references = [], [], []
    with closing(sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True)) as db:
        db.execute('PRAGMA query_only=ON')
        db.row_factory = sqlite3.Row
        columns = {row[1] for row in db.execute('PRAGMA table_info(ItemTemplate)')}
        starters = [dict(row) for row in db.execute('SELECT * FROM StarterEquipment')]
        for ident, source in sorted(originals.items()):
            slot, model = EXPECTED[ident]
            assert (source['Item_Type'], source['Model']) == (slot, model)
            assert (source['Object_Type'], source['Realm'], source['Level'], source['DPS_AF'], source['SPD_ABS']) == (37, 3, 2, 4, 19)
            assert source['AllowedClasses'] == '0' and source['LevelRequirement'] == 0
            assert not any(source[key] for key in ['Bonus', 'SpellID', 'SpellID1', 'ProcSpellID', 'ProcSpellID1'])
            matching = [row for row in starters if row['TemplateID'] == ident]
            assert len(matching) == 1 and set(matching[0]['Class'].strip(';').split(';')) == {'52', '43', '44', '45'}
            references += matching
            found = db.execute('SELECT * FROM ItemTemplate WHERE Id_nb=?', (ident,)).fetchone()
            if found:
                existing.append({'Id_nb': ident, 'sha256': hashlib.sha256(json.dumps(dict(found), sort_keys=True).encode()).hexdigest()})
                continue
            assert not db.execute('SELECT 1 FROM ItemTemplate WHERE ItemTemplate_ID=?', (source['ItemTemplate_ID'],)).fetchone(), 'Existing object identity must never be replaced'
            assert set(source) <= columns, ('Unmapped original fields', sorted(set(source) - columns))
            row = dict(source)
            if 'SalvageExtension' in columns:
                row['SalvageExtension'] = 0  # Additional fork byte property defaults to zero.
            inserts.append(row)
    return {'passed': True, 'installed': False, 'database_modified': False,
        'reference': {'repository': 'Dawn-of-Light/db-public', 'commit': SOURCE_COMMIT,
            'path': 'src/data/ItemTemplate.json', 'git_blob': SOURCE_BLOB},
        'insert_rows': inserts, 'preserved_existing': existing,
        'starter_references': references,
        'scope': 'Restore missing original templates only. No inventory grants, starter-reference edits, renamed-item replacement or race activation.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['reference', 'database', 'output']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    report = prepare(args.reference, args.database)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'passed': report['passed'], 'missing_original_templates': len(report['insert_rows']), 'installed': False}))
