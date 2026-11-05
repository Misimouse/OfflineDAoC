"""Exercise original starter-template import guards with world-only disposable tables."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile

from prepare_hibernia_starter_repair import prepare


def verify(reference, output):
    originals = [r for r in json.loads(reference.read_text(encoding='utf-8-sig')) if r['Id_nb'].startswith('leaf_tacuil_')]
    assert originals
    columns = list(originals[0]) + ['SalvageExtension']
    checks = []
    with tempfile.TemporaryDirectory(prefix='starter-guards-', dir=output.parent) as folder:
        database = Path(folder) / 'world.sqlite3'
        with closing(sqlite3.connect(database)) as db:
            db.execute('CREATE TABLE ItemTemplate (' + ','.join('"' + c + '"' for c in columns) + ')')
            db.execute('CREATE TABLE StarterEquipment (TemplateID TEXT, Class TEXT)')
            for suffix in ['gauntlets', 'boots', 'sleeves', 'leggings', 'vest', 'helm']:
                db.execute('INSERT INTO StarterEquipment VALUES (?,?)', ('leaf_tacuil_' + suffix, '52;44;43;45;'))
            db.commit()
        before = hashlib.sha256(database.read_bytes()).hexdigest()
        proposal = prepare(reference, database)
        assert len(proposal['insert_rows']) == 6 and hashlib.sha256(database.read_bytes()).hexdigest() == before
        checks.append('Read-only proposal supplies exactly six verified original templates')
        with closing(sqlite3.connect(database)) as db:
            for row in proposal['insert_rows']:
                db.execute('INSERT INTO ItemTemplate (' + ','.join('"' + k + '"' for k in row) + ') VALUES (' + ','.join('?' for k in row) + ')', list(row.values()))
            db.commit()
        repeated = prepare(reference, database)
        assert not repeated['insert_rows'] and len(repeated['preserved_existing']) == 6
        checks.append('Repeated proposal preserves all existing identities and values')
        with closing(sqlite3.connect(database)) as db:
            db.execute('UPDATE ItemTemplate SET Id_nb=? WHERE Id_nb=?', ('private-existing-item', 'leaf_tacuil_vest'))
            db.commit()
        try:
            prepare(reference, database)
        except AssertionError as error:
            assert 'identity' in str(error)
            checks.append('Occupied original GUID is rejected without overwriting another item')
        else:
            raise AssertionError('Identity collision accepted')
        altered = Path(folder) / 'tampered.json'
        altered.write_text('[]', encoding='utf-8')
        try:
            prepare(altered, database)
        except AssertionError as error:
            assert 'Git blob' in str(error)
            checks.append('Altered upstream reference is rejected')
        else:
            raise AssertionError('Tampered reference accepted')
    result = {'passed': True, 'checks': checks, 'played_database_modified': False}
    output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['reference', 'output']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    print(json.dumps(verify(args.reference, args.output)))
