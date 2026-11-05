"""Verify late-collision rollback using in-memory copies of a marked QA backup."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile

from prepare_combined_expansion_data import apply_marked, digest


def verify(workspace, backup):
    workspace, backup = workspace.resolve(), backup.resolve()
    assert backup.is_relative_to(workspace/'Backups') and backup.name == 'before.sqlite3.db'
    prepared = json.loads((workspace/'Reports/protocol_qa/prepared.json').read_text())
    run_id = Path(prepared['root']).name
    proposal = workspace/'Reports/combined_expansions/data_integration/proposal.json'
    rows = json.loads(proposal.read_text())['rows']
    source_hash = digest(backup)
    checks = []

    temporary_root = workspace/'ExpansionRaceLab/TestTemp'
    temporary_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='combined_data_guard_', dir=temporary_root) as temporary:
        temporary = Path(temporary).resolve()
        assert temporary.is_relative_to(temporary_root.resolve())
        other = temporary/'review_like.sqlite3.db'
        with closing(sqlite3.connect(other)) as db:
            db.execute('CREATE TABLE CodexQaIsolationMarker (RunId TEXT)')
            db.execute('INSERT INTO CodexQaIsolationMarker VALUES (?)', (run_id,))
            db.commit()
            other_hash = digest(other)
            try:
                apply_marked(db, proposal, run_id, workspace)
            except AssertionError:
                pass
            else:
                raise AssertionError('A matching marker outside the QA directory was accepted')
            assert digest(other) == other_hash
        checks.append('matching_marker_outside_qa_directory_rejected')

    def memory():
        db = sqlite3.connect(':memory:')
        with closing(sqlite3.connect(backup.as_uri()+'?mode=ro', uri=True)) as source:
            assert source.execute('SELECT RunId FROM CodexQaIsolationMarker').fetchone()[0] == run_id
            source.backup(db)
        db.row_factory = sqlite3.Row
        return db

    def counts(db):
        return {table: db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in rows}

    with closing(memory()) as db:
        before = counts(db)
        try:
            apply_marked(db, proposal, run_id+'-wrong', workspace)
        except AssertionError:
            pass
        else:
            raise AssertionError('Wrong isolation marker was accepted')
        assert counts(db) == before
        checks.append('wrong_marker_rejected_without_changes')

    with closing(memory()) as db:
        # Startup records are deliberately inserted last. This collision must
        # roll back all spells, abilities and templates already inserted.
        sentinel = rows['StartupLocation'][0]
        columns = list(sentinel)
        db.execute('INSERT INTO StartupLocation ('+','.join('"'+k+'"' for k in columns)+') VALUES ('+
                   ','.join('?' for _ in columns)+')', [sentinel[k] for k in columns])
        before = counts(db)
        try:
            apply_marked(db, proposal, run_id, workspace)
        except sqlite3.IntegrityError:
            pass
        else:
            raise AssertionError('Late identity collision was accepted')
        assert counts(db) == before
        current = db.execute('SELECT * FROM StartupLocation WHERE StartupLoc_ID=?',
                             (sentinel['StartupLoc_ID'],)).fetchone()
        assert all(current[key] == value for key, value in sentinel.items())
        checks.append('late_collision_rolls_back_all_prior_tables_and_preserves_existing_row')

    with closing(memory()) as db:
        apply_marked(db, proposal, run_id, workspace)
        before = counts(db)
        try:
            apply_marked(db, proposal, run_id, workspace)
        except sqlite3.IntegrityError:
            pass
        else:
            raise AssertionError('Duplicate insertion was accepted')
        assert counts(db) == before
        checks.append('duplicate_package_refused_without_replacing_data')

    assert digest(backup) == source_hash
    result = {'passed': True, 'checks': checks, 'in_memory_only': True,
              'source_backup_unchanged': True, 'proposal_sha256': digest(proposal)}
    output = workspace/'Reports/combined_expansions/data_integration/rollback_checks.json'
    output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--backup', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.workspace, args.backup)))
