"""Exercise startup proposal preservation guards in a tiny, disposable world-only database."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile

from audit_expansion_race_rules import verified_source
from prepare_shar_startup_proposal import SOURCE_BLOB, prepare


def verify(source, folder):
    original = json.loads(verified_source(source, SOURCE_BLOB))
    rows = [row for row in original if row['RaceID'] == 18 and row['Region'] == 200 and row['ClientRegionID'] == 0]
    assert len(rows) == 3
    with tempfile.TemporaryDirectory(prefix='shar-startup-', dir=folder) as temporary:
        assert Path(temporary).resolve().is_relative_to(folder.resolve()) and Path(temporary).resolve() != folder.resolve()
        database = Path(temporary) / 'world-only.sqlite3'
        occupied = dict(rows[0], RaceID=9)
        keys = list(occupied)
        with closing(sqlite3.connect(database)) as db, db:
            definitions = ['"' + key + '" ' + ('TEXT' if isinstance(occupied[key], str) else 'INTEGER')
                           + (' PRIMARY KEY' if key == 'StartupLoc_ID' else '') for key in keys]
            db.execute('CREATE TABLE StartupLocation (' + ','.join(definitions) + ')')
            db.execute('CREATE TABLE Zones (RegionID INTEGER)')
            db.execute('INSERT INTO Zones VALUES (200)')
            insert = 'INSERT INTO StartupLocation (' + ','.join('"' + key + '"' for key in keys) + ') VALUES (' + ','.join('?' for key in keys) + ')'
            db.execute(insert, [occupied[key] for key in keys])
        before = hashlib.sha256(database.read_bytes()).hexdigest()
        proposal = prepare(source, database)
        assert len(proposal['insert_rows']) == 3
        assert hashlib.sha256(database.read_bytes()).hexdigest() == before
        ids = [row['StartupLoc_ID'] for row in proposal['insert_rows']]
        assert len(set(ids)) == 3 and occupied['StartupLoc_ID'] not in ids
        with closing(sqlite3.connect(database)) as db, db:
            for row in proposal['insert_rows']:
                db.execute(insert, [row[key] for key in keys])
            assert db.execute('SELECT RaceID FROM StartupLocation WHERE StartupLoc_ID=?', (occupied['StartupLoc_ID'],)).fetchone()[0] == 9
        assert not prepare(source, database)['insert_rows']
        with closing(sqlite3.connect(database)) as db, db:
            db.execute('UPDATE StartupLocation SET XPos=XPos+1 WHERE RaceID=18 AND ClassID=51')
        try:
            prepare(source, database)
        except AssertionError as error:
            assert 'Preserve conflicting installed start' in str(error)
        else:
            raise AssertionError('A conflicting existing start must never be silently replaced')
        tampered = Path(temporary) / 'tampered.json'
        tampered.write_text('{"tampered":true}', encoding='utf-8')
        try:
            prepare(tampered, database)
        except AssertionError as error:
            assert 'Pinned upstream Git blob mismatch' in str(error)
        else:
            raise AssertionError('Modified reference must be rejected')
    return {'passed': True, 'database_read_only_during_proposal': True,
        'occupied_ids_preserved': True, 'repeat_import_empty': True,
        'conflicting_coordinates_rejected': True, 'modified_reference_rejected': True,
        'played_database_accessed': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['source', 'folder', 'output']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    args.folder.mkdir(parents=True, exist_ok=True)
    report = verify(args.source, args.folder)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report))
