"""Propose the three original DOL Shar base-class starts; no database writes."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3

from audit_expansion_race_rules import verified_source

SOURCE_BLOB = '4e5333469deb2fa98ca3bb4c54ec4f9093bce414'
SOURCE_COMMIT = 'b5b29c2ada7695414b94f5fa110eb505a477d007'


def prepare(source, database):
    reference = json.loads(verified_source(source, SOURCE_BLOB))
    rows = [row for row in reference if row['RaceID'] == 18 and row['Region'] == 200
            and row['ClientRegionID'] == 0 and row['ClassID'] in [51, 52, 54]]
    assert len(rows) == 3 and {row['ClassID'] for row in rows} == {51, 52, 54}
    assert all(row['MinVersion'] == 168 and row['RealmID'] == 0
               and all(row[key] != 0 for key in ['XPos', 'YPos', 'ZPos']) for row in rows)
    with closing(sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True)) as db:
        db.execute('PRAGMA query_only=ON')
        db.row_factory = sqlite3.Row
        existing = [dict(row) for row in db.execute('SELECT * FROM StartupLocation WHERE RaceID=18')]
        ids = {row[0] for row in db.execute('SELECT StartupLoc_ID FROM StartupLocation')}
        next_id = max(int(value) for value in ids) + 1
        assert db.execute('SELECT 1 FROM Zones WHERE RegionID=200 LIMIT 1').fetchone()
    proposed = []
    identity = ['RaceID', 'ClassID', 'RealmID', 'Region', 'ClientRegionID', 'MinVersion']
    for row in rows:
        found = [value for value in existing if all(value[key] == row[key] for key in identity)]
        assert len(found) <= 1
        if found:
            assert all(found[0][key] == row[key] for key in ['XPos', 'YPos', 'ZPos', 'Heading']), 'Preserve conflicting installed start'
            continue
        value = dict(row)
        if value['StartupLoc_ID'] in ids:
            value['StartupLoc_ID'] = next_id
            next_id += 1
        ids.add(value['StartupLoc_ID'])
        proposed.append(value)
    return {'passed': True, 'installed': False, 'database_modified': False,
        'reference': {'repository': 'Dawn-of-Light/db-public', 'commit': SOURCE_COMMIT,
            'path': 'src/data/StartupLocation.json', 'git_blob': SOURCE_BLOB},
        'original_rows': rows, 'insert_rows': proposed,
        'existing_shar_rows_sha256': hashlib.sha256(json.dumps(existing, sort_keys=True).encode()).hexdigest(),
        'scope': 'Original region200 starts for Shar Magician, Guardian and Stalker; no Catacombs-region import or invented coordinates.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['source', 'database', 'output']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    report = prepare(args.source, args.database)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'passed': report['passed'], 'insert_rows': len(report['insert_rows']), 'installed': False}))
