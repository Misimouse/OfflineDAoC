"""Install accepted class-data additions only; never activate classes or import world population."""
import argparse
from contextlib import ExitStack, closing
from datetime import datetime
import json
from pathlib import Path
import socket
import sqlite3
import xml.etree.ElementTree as ET

from prepare_combined_expansion_data import digest
from prepare_review_expansion_delta import IDENTITIES, SURROGATES
from install_review_expansion_delta import fingerprint, insert_delta
from snapshot_world_database import snapshot


def install(workspace, game, apply=False):
    folder = workspace/'ExpansionRaceLab/CentralDelivery'
    preview_path = folder/'data_preview.json'
    preview = json.loads(preview_path.read_text())
    proposal_path = workspace/'Reports/combined_expansions/data_integration/proposal.json'
    proposal = json.loads(proposal_path.read_text())
    seal = json.loads((workspace/'ExpansionRaceLab/CombinedExpansionServerCandidate/verified_joint_creation.json').read_text())
    assert seal['passed'] and seal['preloaded_joint_data_accepted'] and seal['joint_class_behavior_cases'] == 7
    assert preview['passed'] and preview['proposal_only'] and not preview['activation_included']
    assert preview['source_proposal_sha256'] == digest(proposal_path)
    assert preview['memory_dry_run']['all_existing_rows_preserved'] and not preview['conflicts']
    rows = preview['insert_rows']
    assert set(rows) == set(IDENTITIES)
    for table, additions in rows.items():
        originals = {tuple(row[k] for k in IDENTITIES[table]): row for row in proposal['rows'][table]}
        for addition in additions:
            original = originals[tuple(addition[k] for k in IDENTITIES[table])]
            assert set(addition) == set(original)
            assert all(value == original[k] for k, value in addition.items() if k != SURROGATES.get(table))
    receipt_path = folder/'installed_class_data.json'
    database = game/'runtime/data/opendaoc.sqlite3.db'
    with snapshot(database, workspace/'ExpansionRaceLab/TestTemp') as (copy, _):
        if receipt_path.exists():
            installed = json.loads(receipt_path.read_text())
            assert installed['installed'] and installed['source_proposal_sha256'] == digest(proposal_path)
            # Later legitimate gameplay may change rows. Check additions individually,
            # without claiming that the historic progress fingerprint is still current.
            for table, additions in installed['insert_rows'].items():
                columns = [r['name'] for r in copy.execute('PRAGMA table_info('+table+')')]
                for addition in additions:
                    matches = copy.execute('SELECT * FROM '+table+' WHERE '+' AND '.join('"'+k+'"=?' for k in IDENTITIES[table]),
                                           [addition[k] for k in IDENTITIES[table]]).fetchall()
                    assert len(matches) == 1 and all(dict(zip(columns, matches[0]))[k] == v for k, v in addition.items())
            return {'passed': True, 'installed': True, 'already_current': True}
        assert fingerprint(copy) == preview['before_fingerprint'], 'Installed world changed; prepare a fresh preview'
    summary = {'passed': True, 'installed': False, 'dry_run': True,
               'added_rows': {k: len(v) for k, v in rows.items()}, 'activation_included': False,
               'world_population_imported': False, 'existing_tables_verified': len(preview['before_fingerprint'])}
    (folder/'class_data_dry_run.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    if not apply:
        return summary
    node = ET.parse(game/'runtime/server/config/serverconfig.xml').getroot().find('Server')
    ports = [(socket.SOCK_STREAM, int(node.findtext('Port'))),
             (socket.SOCK_DGRAM, int(node.findtext('UdpPort'))), (socket.SOCK_STREAM, 19727)]
    with ExitStack() as stack:
        for kind, port in ports:
            guard = stack.enter_context(socket.socket(socket.AF_INET, kind))
            guard.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            guard.bind(('127.0.0.1', port))
            if kind == socket.SOCK_STREAM:
                guard.listen(1)
        backup = workspace/'Backups'/('CentralClassData_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        backup.mkdir()
        assert backup.resolve().is_relative_to(workspace/'Backups')
        db = sqlite3.connect(database)
        committed = False
        try:
            assert fingerprint(db) == preview['before_fingerprint']
            with closing(sqlite3.connect(backup/'before.sqlite3.db')) as destination:
                db.backup(destination)
                assert destination.execute('PRAGMA quick_check').fetchone()[0] == 'ok'
            db.execute('BEGIN IMMEDIATE')
            assert fingerprint(db) == preview['before_fingerprint']
            insert_delta(db, rows)
            assert fingerprint(db, rows) == preview['before_fingerprint']
            assert db.execute('PRAGMA quick_check').fetchone()[0] == 'ok'
            receipt = dict(summary, installed=False, dry_run=False, phase='verified_transaction_pending',
                           preview_sha256=digest(preview_path), source_proposal_sha256=digest(proposal_path),
                           backup_directory=str(backup), insert_rows=rows,
                           all_previous_rows_preserved=True, all_server_properties_preserved=True)
            receipt_path.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
            db.commit()
            committed = True
            receipt.update(installed=True, phase='complete')
            receipt_path.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
        except BaseException:
            if not committed:
                db.rollback()
                receipt_path.unlink(missing_ok=True)
            raise
        finally:
            db.close()
    return {k: v for k, v in receipt.items() if k != 'insert_rows'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--install', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    print(json.dumps(install(args.workspace.resolve(), args.install.resolve(), args.apply)))
