"""Read-only delta for the existing private review; never replace its database."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3

from prepare_combined_expansion_data import digest


IDENTITIES = {
    'Spell': ['SpellID'], 'LineXSpell': ['LineName', 'SpellID', 'Level'],
    'Ability': ['KeyName'], 'SpecXAbility': ['Spec', 'SpecLevel', 'AbilityKey', 'AbilityLevel', 'ClassId'],
    'ItemTemplate': ['Id_nb'],
    'StartupLocation': ['RaceID', 'ClassID', 'RealmID', 'Region', 'ClientRegionID', 'MinVersion']}
SURROGATES = {'LineXSpell': 'LineXSpell_ID', 'SpecXAbility': 'SpecXabilityID',
              'StartupLocation': 'StartupLoc_ID'}


def prepare(workspace):
    workspace = workspace.resolve()
    review = workspace/'ExpansionRaceLab/MinotaurOwnerReview'
    database = review/'runtime/data/review.sqlite3.db'
    assert database.resolve().is_relative_to(review.resolve())
    proof = json.loads((workspace/'ExpansionRaceLab/CombinedExpansionServerCandidate/verified_joint_creation.json').read_text())
    assert proof['passed'] and proof['preloaded_joint_data_accepted'] and proof['preloaded_joint_data_cases'] == 17
    source = workspace/'Reports/combined_expansions/data_integration/proposal.json'
    package = json.loads(source.read_text())
    assert package['passed'] and package['proposal_only'] and not package['activation_included']
    assert set(package['rows']) == set(IDENTITIES)
    before_hash = digest(database)
    inserts, preserved, conflicts, allocations = {k: [] for k in IDENTITIES}, {}, [], []
    with closing(sqlite3.connect(database.resolve().as_uri()+'?mode=ro', uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA query_only=ON')
        marker = db.execute('SELECT RunId FROM CodexQaIsolationMarker').fetchone()[0]
        assert marker.startswith('run-')
        for table, values in package['rows'].items():
            preserved[table] = 0
            schema = [dict(row) for row in db.execute('PRAGMA table_info('+table+')')]
            columns = {row['name'] for row in schema}
            primary = next(row['name'] for row in schema if row['pk'])
            used = {row[0] for row in db.execute('SELECT "'+primary+'" FROM '+table)}
            next_id = max(int(value) for value in used)+1 if table in ['SpecXAbility', 'StartupLocation'] else None
            for original in values:
                assert set(original) <= columns
                identity = IDENTITIES[table]
                found = db.execute('SELECT * FROM '+table+' WHERE '+' AND '.join('"'+k+'"=?' for k in identity),
                                   [original[k] for k in identity]).fetchall()
                assert len(found) <= 1
                ignored = {'LastTimeRowUpdated', SURROGATES.get(table, '')}
                if found:
                    differences = [k for k, value in original.items() if k not in ignored and found[0][k] != value]
                    if differences:
                        conflicts.append({'table': table, 'identity': {k: original[k] for k in identity}, 'different_fields': differences})
                    else:
                        preserved[table] += 1
                    continue
                row = dict(original)
                if next_id is not None:
                    old_id = row[primary]
                    row[primary] = next_id
                    allocations.append({'table': table, 'source_id': old_id, 'review_id': next_id})
                    next_id += 1
                elif row[primary] in used:
                    conflicts.append({'table': table, 'reason': 'primary identity collision', 'identity': {k: row[k] for k in identity}})
                    continue
                used.add(row[primary])
                inserts[table].append(row)
    assert digest(database) == before_hash, 'Review changed during read-only preparation'
    result = {'passed': not conflicts, 'proposal_only': True, 'review_database_modified': False,
              'normal_database_modified': False, 'database_replacement': False, 'activation_included': False,
              'source_proposal_sha256': digest(source), 'review_before_sha256': before_hash,
              'insert_rows': inserts, 'preserved_existing_rows': preserved,
              'surrogate_allocations': allocations, 'conflicts': conflicts,
              'scope': 'Data delta only. No character, account, inventory, quest or progress records are included.'}
    output = workspace/'ExpansionRaceLab/CombinedExpansionReviewMigration/preview.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    return {'passed': result['passed'], 'review_database_modified': False,
            'missing_rows': {k: len(v) for k, v in inserts.items()},
            'preserved_rows': preserved, 'conflicts': conflicts, 'proposal': str(output)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    print(json.dumps(prepare(parser.parse_args().workspace)))
