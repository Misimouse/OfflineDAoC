"""Reversible data/server update of the stopped private Minotaur review only."""
import argparse
from contextlib import closing
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import socket
import sqlite3

from prepare_combined_expansion_data import digest
from prepare_review_expansion_delta import IDENTITIES


def fingerprint(db, inserted=None):
    """Hash every existing row, excluding only explicitly inserted identities."""
    inserted = inserted or {}
    result = {}
    tables = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    for table in sorted(tables):
        quoted = '"'+table.replace('"', '""')+'"'
        schema = list(db.execute('PRAGMA table_info('+quoted+')'))
        columns = [row[1] for row in schema]
        primary = next((row[1] for row in schema if row[5]), None)
        exclude = {row[primary] for row in inserted.get(table, [])} if primary else set()
        records = []
        for row in db.execute('SELECT * FROM '+quoted):
            record = dict(zip(columns, row))
            if primary and record[primary] in exclude:
                continue
            raw = json.dumps(record, sort_keys=True, separators=(',', ':'),
                             default=lambda value: {'bytes_hex': value.hex()}).encode()
            records.append(hashlib.sha256(raw).hexdigest())
        result[table] = {'rows': len(records), 'sha256': hashlib.sha256(''.join(sorted(records)).encode()).hexdigest()}
    return result


def insert_delta(db, rows):
    assert set(rows) == set(IDENTITIES)
    for table, values in rows.items():
        allowed = {row[1] for row in db.execute('PRAGMA table_info('+table+')')}
        for row in values:
            assert row and set(row) <= allowed
            columns = list(row)
            db.execute('INSERT INTO '+table+' ('+','.join('"'+k+'"' for k in columns)+') VALUES ('+
                       ','.join('?' for _ in columns)+')', [row[k] for k in columns])
    assert db.execute('PRAGMA quick_check').fetchone()[0] == 'ok'


def run(workspace, apply=False):
    workspace = workspace.resolve()
    review = workspace/'ExpansionRaceLab/MinotaurOwnerReview'
    database = (review/'runtime/data/review.sqlite3.db').resolve()
    assert database.is_relative_to(review.resolve()) and database.name == 'review.sqlite3.db'
    migration = workspace/'ExpansionRaceLab/CombinedExpansionReviewMigration'
    preview_path = migration/'preview.json'
    preview = json.loads(preview_path.read_text())
    assert preview['passed'] and preview['proposal_only'] and not preview['conflicts']
    assert not preview['database_replacement'] and not preview['activation_included']
    assert preview['source_proposal_sha256'] == digest(workspace/'Reports/combined_expansions/data_integration/proposal.json')
    assert set(preview['insert_rows']) == set(IDENTITIES)
    receipt_path = review/'joint_integration.json'
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
        assert receipt['installed'] and receipt['review_only']
        assert all(digest(Path(path)) == value for path, value in receipt['installed_files'].items())
        return receipt
    assert digest(database) == preview['review_before_sha256'], 'Review changed; prepare a fresh read-only delta'

    # Test the actual existing review in memory, including every progress row.
    with closing(sqlite3.connect(database.as_uri()+'?mode=ro', uri=True)) as source, closing(sqlite3.connect(':memory:')) as memory:
        assert source.execute('SELECT RunId FROM CodexQaIsolationMarker').fetchone()[0].startswith('run-')
        source.backup(memory)
        before = fingerprint(memory)
        insert_delta(memory, preview['insert_rows'])
        assert fingerprint(memory, preview['insert_rows']) == before
        memory.rollback()
    dry = {'passed': True, 'dry_run': True, 'review_database_modified': False,
           'preview_sha256': digest(preview_path), 'existing_tables_verified': len(before),
           'all_existing_rows_preserved': True,
           'added_rows': {table: len(values) for table, values in preview['insert_rows'].items()}}
    assert digest(database) == preview['review_before_sha256']
    (migration/'dry_run.json').write_text(json.dumps(dry, indent=2), encoding='utf-8')
    if not apply:
        return dry

    candidate = workspace/'ExpansionRaceLab/CombinedExpansionServerCandidate'
    build = json.loads((candidate/'build_receipt.json').read_text())
    acceptance = json.loads((candidate/'verified_joint_creation.json').read_text())
    assert build['passed'] and not build['installed'] and build['compiled_bridge_overlay_verified']
    assert set(build['candidate_features']) == {'vampiir_creation', 'minotaur_creation'}
    assert acceptance['passed'] and acceptance['preloaded_joint_data_accepted']
    libraries = Path(build['libraries']).resolve()
    assert libraries.is_relative_to(candidate.resolve())
    assert set(build['binaries_sha256']) == {'GameServer.dll', 'CoreBase.dll', 'CoreDatabase.dll'}
    for name, value in build['binaries_sha256'].items():
        assert digest(libraries/name) == value
    targets = []
    for folder in [review/'runtime/server', review/'runtime/server/lib', review/'runtime/server/win-x64']:
        for name in build['binaries_sha256']:
            target = folder/name
            if folder != review/'runtime/server' and not target.exists():
                continue
            assert target.exists() and target.resolve().is_relative_to(review.resolve())
            targets.append((target, libraries/name))
    assert len(targets) >= 3
    reservations = []
    backups = None
    database_committed = False
    try:
        for port, kind in [(10361, socket.SOCK_STREAM), (19747, socket.SOCK_STREAM), (10461, socket.SOCK_DGRAM)]:
            guard = socket.socket(socket.AF_INET, kind)
            reservations.append(guard)
            guard.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            guard.bind(('127.0.0.1', port))
        assert digest(database) == preview['review_before_sha256']
        backups = migration/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        backups.mkdir(parents=True)
        backup_database = backups/'review_before.sqlite3.db'
        # SQLite backup includes committed WAL content; copying the main file
        # alone could omit the owner's most recent saved progress.
        with closing(sqlite3.connect(database.as_uri()+'?mode=ro', uri=True)) as source, closing(sqlite3.connect(backup_database)) as target:
            source.backup(target)
        file_backups = {}
        for target, new in targets:
            saved = backups/'files'/target.relative_to(review)
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, saved)
            file_backups[str(target)] = str(saved)
        (backups/'rollback.json').write_text(json.dumps({'database': str(database),
            'backup_database': str(backup_database), 'files': file_backups}, indent=2), encoding='utf-8')
        for target, new in targets:
            shutil.copy2(new, target)
            assert digest(target) == build['binaries_sha256'][target.name]
        with closing(sqlite3.connect(database)) as db:
            try:
                db.execute('BEGIN IMMEDIATE')
                assert fingerprint(db) == before, 'Existing review state changed before installation'
                insert_delta(db, preview['insert_rows'])
                assert fingerprint(db, preview['insert_rows']) == before
                db.commit()
                database_committed = True
            except Exception:
                db.rollback()
                raise
        receipt = {'installed': True, 'review_only': True, 'normal_installation_modified': False,
                   'review_database_replaced': False, 'all_existing_rows_preserved': True,
                   'existing_tables_verified': len(before), 'added_rows': dry['added_rows'],
                   'preview_sha256': digest(preview_path), 'server_build_receipt_sha256': digest(candidate/'build_receipt.json'),
                   'installed_files': {str(target): digest(target) for target, new in targets},
                   'backup_directory': str(backups), 'creation_scope': 'minotaur_only',
                   'race_class_activation_changed': False, 'launcher_changed': False}
        receipt_path.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
        return receipt
    except Exception:
        if backups is not None and (backups/'rollback.json').exists():
            rollback = json.loads((backups/'rollback.json').read_text())
            if database_committed:
                with closing(sqlite3.connect(rollback['backup_database'])) as source, closing(sqlite3.connect(database)) as target:
                    source.backup(target)
            for target, saved in rollback['files'].items():
                shutil.copy2(saved, target)
        raise
    finally:
        for guard in reservations:
            guard.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    print(json.dumps(run(args.workspace, args.apply)))
