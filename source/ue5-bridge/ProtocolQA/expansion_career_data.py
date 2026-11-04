"""Prepare or apply original career associations only to explicitly marked QA data."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
from prepare_bainshee_probe_data import COMMIT

SOURCES = {
    'SpecXAbility.json': ('09d8fb515bb89a3beec138cdbd3b4d6a1bca9c8db6267e600665206645650e04', '6cc555ef61761fa27a39af8ae1c0c96372523352'),
    'Ability.json': ('97f172a7fe27333a679404475d9ef8f691308621986ec68252e801c4f19b6bd8', '9c11af5afa8c0943ad94a3a4ed50edcaf3cdea70'),
    'Spell.json': ('5f1e64c65f1da9f9b8a200192157ecd7ed642010c862dda270e5b316ae975232', '55984d36348c5ebcd0da26c63e439fc44be5b188'),
}
CAREERS = {58: {'VampiirCareer'}, 62: {'MaulerCareer', 'MaulerHibCareer'}}


def digest(row):
    return hashlib.sha256(json.dumps(dict(row), sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def checked(db, run_id):
    assert db.execute('SELECT RunId FROM CodexQaIsolationMarker').fetchone()[0] == run_id


def prepare(root, class_id, reserve_paths=()):
    prepared = json.loads((root / 'Reports/protocol_qa/prepared.json').read_text())
    run, database = Path(prepared['root']).resolve(), Path(prepared['database']).resolve()
    assert run.is_relative_to(root / 'ProtocolQA') and database.is_relative_to(run)
    refs = root / 'References' / ('DOLPublic_' + COMMIT[:12])
    source = {}
    for name, (sha, blob) in SOURCES.items():
        raw = (refs / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == sha, name
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == blob, name
        source[name] = json.loads(raw)
    links = [r for r in source['SpecXAbility.json'] if r['Spec'] in CAREERS[class_id]]
    assert len(links) == {58: 19, 62: 9}[class_id]
    assert all(r['ClassId'] == 0 for r in links)
    keys = {r['AbilityKey'] for r in links}
    report = {'proposal_only': True, 'source_commit': COMMIT, 'sources': SOURCES, 'class_id': class_id,
              'careers': sorted(CAREERS[class_id]), 'rows': {'Ability': [], 'SpecXAbility': [], 'Spell': []},
              'preserved_abilities': {}, 'reserved_association_ids': [], 'not_creation_enablement': True}
    reserved = set()
    for path in reserve_paths:
        assert path.resolve().is_relative_to(root / 'Reports')
        other = json.loads(path.read_text())
        assert other['proposal_only'] and other['source_commit'] == COMMIT and other['class_id'] != class_id
        reserved.update(int(row['SpecXabilityID']) for row in other['rows']['SpecXAbility'])
    report['reserved_association_ids'] = sorted(reserved)
    with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        checked(db, run.name)
        careers = {r[0] for r in db.execute('SELECT SpecKeyName FROM ClassXSpecialization WHERE ClassID=?', (class_id,))}
        assert CAREERS[class_id] <= careers
        for career in CAREERS[class_id]:
            assert db.execute('SELECT COUNT(*) FROM SpecXAbility WHERE Spec=?', (career,)).fetchone()[0] == 0
        definitions = {r['KeyName']: r for r in source['Ability.json']}
        for key in sorted(keys):
            original = definitions[key]
            row = db.execute('SELECT * FROM Ability WHERE KeyName=?', (key,)).fetchone()
            if row is not None:
                assert dict(row) == original, 'Existing ability differs: ' + key
                report['preserved_abilities'][key] = digest(row)
            else:
                assert class_id == 58 and key in {'Vampiir Strength', 'Vampiir Constitution', 'Vampiir Dexterity', 'Vampiir Quickness'}
                assert not db.execute('SELECT 1 FROM Ability WHERE AbilityID=? OR InternalID=?', (original['AbilityID'], original['InternalID'])).fetchone()
                report['rows']['Ability'].append(original)
        # Only the surrogate association key changes; career/rank/ability data stays original.
        next_id = db.execute('SELECT COALESCE(MAX(SpecXabilityID),0)+1 FROM SpecXAbility').fetchone()[0]
        for original in links:
            while next_id in reserved:
                next_id += 1
            row = dict(original)
            row['SpecXabilityID'] = next_id
            next_id += 1
            report['rows']['SpecXAbility'].append(row)
        if class_id == 58:
            # The original VampiirBoltAbilityHandler addresses 13200 + ability.Level.
            bolts = [r for r in source['Spell.json'] if 13200 <= int(r['SpellID']) <= 13207]
            assert len(bolts) == 8 and all(r['Type'] == 'VampiirBolt' for r in bolts)
            columns = {r['name'] for r in db.execute('PRAGMA table_info(Spell)')}
            for original in bolts:
                assert not db.execute('SELECT 1 FROM Spell WHERE SpellID=?', (original['SpellID'],)).fetchone()
                row = {k: v for k, v in original.items() if k in columns}
                row['Spell_ID'] = 'daoc_bridge_vampiir_bolt_' + str(row['SpellID'])
                report['rows']['Spell'].append(row)
    return report


def install(db, path, run_id, class_id):
    checked(db, run_id)
    proposal = json.loads(path.read_text())
    assert proposal['proposal_only'] and proposal['source_commit'] == COMMIT
    assert proposal['class_id'] == class_id and class_id in CAREERS
    assert set(proposal['careers']) == CAREERS[class_id]
    assert {k: len(v) for k, v in proposal['rows'].items()} == ({'Ability': 4, 'SpecXAbility': 19, 'Spell': 8} if class_id == 58 else {'Ability': 0, 'SpecXAbility': 9, 'Spell': 0})
    assert all(row['Spec'] in CAREERS[class_id] and row['ClassId'] == 0 and 1 <= row['SpecLevel'] <= 50 for row in proposal['rows']['SpecXAbility'])
    if class_id == 58:
        assert {row['KeyName'] for row in proposal['rows']['Ability']} == {'Vampiir Strength', 'Vampiir Constitution', 'Vampiir Dexterity', 'Vampiir Quickness'}
        assert {row['SpellID'] for row in proposal['rows']['Spell']} == set(range(13200, 13208))
        assert all(row['Type'] == 'VampiirBolt' for row in proposal['rows']['Spell'])
    for key, expected in proposal['preserved_abilities'].items():
        assert digest(db.execute('SELECT * FROM Ability WHERE KeyName=?', (key,)).fetchone()) == expected
    for career in CAREERS[class_id]:
        assert db.execute('SELECT COUNT(*) FROM SpecXAbility WHERE Spec=?', (career,)).fetchone()[0] == 0
    # Validate every row and collision before performing any insertion.
    for table, rows in proposal['rows'].items():
        columns = {r['name'] for r in db.execute('PRAGMA table_info(' + table + ')')}
        primary = {'Ability': 'AbilityID', 'SpecXAbility': 'SpecXabilityID', 'Spell': 'SpellID'}[table]
        assert len({row[primary] for row in rows}) == len(rows)
        for row in rows:
            assert set(row) <= columns
            assert not db.execute('SELECT 1 FROM ' + table + ' WHERE ' + primary + '=?', (row[primary],)).fetchone()
            if table == 'Ability':
                assert not db.execute('SELECT 1 FROM Ability WHERE KeyName=? OR InternalID=?', (row['KeyName'], row['InternalID'])).fetchone()
            if table == 'Spell':
                assert not db.execute('SELECT 1 FROM Spell WHERE Spell_ID=?', (row['Spell_ID'],)).fetchone()
    for table, rows in proposal['rows'].items():
        for row in rows:
            columns = list(row)
            db.execute('INSERT INTO ' + table + ' (' + ','.join(columns) + ') VALUES (' + ','.join('?' for _ in columns) + ')', [row[k] for k in columns])
    return {'class_id': class_id, 'added': {k: len(v) for k, v in proposal['rows'].items()}, 'disposable_only': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--class-id', type=int, choices=[58, 62], required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reserve-proposal', type=Path, action='append', default=[])
    args = parser.parse_args()
    root = args.workspace.resolve()
    assert args.output.resolve().is_relative_to(root / 'Reports')
    report = prepare(root, args.class_id, args.reserve_proposal)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'proposal_only': True, 'class_id': args.class_id, 'rows': {k: len(v) for k, v in report['rows'].items()}}))
