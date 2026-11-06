"""Compare accepted class data with the installed world using a disposable read-only snapshot."""
import argparse
import json
from pathlib import Path
import sqlite3

from prepare_combined_expansion_data import digest
from prepare_review_expansion_delta import IDENTITIES, SURROGATES
from install_review_expansion_delta import fingerprint, insert_delta
from snapshot_world_database import snapshot


def prepare(workspace, install):
    package_path = workspace/'Reports/combined_expansions/data_integration/proposal.json'
    package = json.loads(package_path.read_text())
    seal = json.loads((workspace/'ExpansionRaceLab/CombinedExpansionServerCandidate/verified_joint_creation.json').read_text())
    assert seal['passed'] and seal['preloaded_joint_data_accepted'] and seal['joint_class_behavior_cases'] == 7
    assert package['passed'] and package['proposal_only'] and not package['activation_included']
    inserts, preserved, conflicts = {key: [] for key in IDENTITIES}, {}, []
    with snapshot(install/'runtime/data/opendaoc.sqlite3.db', workspace/'ExpansionRaceLab/TestTemp') as (source, metadata):
        for table, originals in package['rows'].items():
            assert table in IDENTITIES
            schema = list(source.execute('PRAGMA table_info('+table+')'))
            allowed = {r['name'] for r in schema}
            primary = next(r['name'] for r in schema if r['pk'])
            used = {r[0] for r in source.execute('SELECT "'+primary+'" FROM '+table)}
            next_id = max([int(value) for value in used], default=0)+1 if table in ['SpecXAbility', 'StartupLocation'] else None
            preserved[table] = 0
            for original in originals:
                assert set(original) <= allowed
                keys = IDENTITIES[table]
                matches = source.execute('SELECT * FROM '+table+' WHERE '+' AND '.join('"'+k+'"=?' for k in keys),
                                         [original[k] for k in keys]).fetchall()
                if len(matches) > 1:
                    conflicts.append({'table': table, 'reason': 'duplicate natural identity',
                                      'identity': {k: original[k] for k in keys}})
                    continue
                if matches:
                    ignored = {'LastTimeRowUpdated', SURROGATES.get(table, '')}
                    differences = [k for k, value in original.items() if k not in ignored and matches[0][k] != value]
                    if differences:
                        conflicts.append({'table': table, 'identity': {k: original[k] for k in keys}, 'different_fields': differences})
                    else:
                        preserved[table] += 1
                    continue
                row = dict(original)
                if next_id is not None:
                    row[primary] = next_id
                    next_id += 1
                elif row[primary] in used:
                    conflicts.append({'table': table, 'reason': 'primary identity collision',
                                      'identity': {k: row[k] for k in keys}})
                    continue
                used.add(row[primary])
                inserts[table].append(row)
        dry_run = {'passed': False, 'existing_tables_verified': 0}
        if not conflicts:
            memory = sqlite3.connect(':memory:')
            try:
                source.backup(memory)
                before = fingerprint(memory)
                insert_delta(memory, inserts)
                assert fingerprint(memory, inserts) == before
                dry_run = {'passed': True, 'existing_tables_verified': len(before), 'all_existing_rows_preserved': True}
            finally:
                memory.close()
    result = {'passed': not conflicts and dry_run['passed'], 'proposal_only': True,
              'normal_database_modified': False, 'activation_included': False,
              'source_proposal_sha256': digest(package_path), 'snapshot': metadata,
              'insert_rows': inserts, 'preserved_rows': preserved, 'conflicts': conflicts,
              'memory_dry_run': dry_run,
              'scope': 'Six class-data tables only. No account, character, inventory, quest, region, mob or world population writes.'}
    if dry_run['passed']:
        result['before_fingerprint'] = before
    output = workspace/'ExpansionRaceLab/CentralDelivery/data_preview.json'
    output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'passed': result['passed'], 'missing_rows': {k: len(v) for k, v in inserts.items()},
                      'preserved_rows': preserved, 'conflicts': len(conflicts), 'dry_run': dry_run}))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--install', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.workspace.resolve(), args.install.resolve())
