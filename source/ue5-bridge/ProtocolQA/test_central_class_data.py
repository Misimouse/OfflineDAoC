"""Exercise transactional class delivery on synthetic databases, including injected failure."""
import argparse
from contextlib import contextmanager
import json
from pathlib import Path
import socket
import sqlite3
import tempfile
from unittest.mock import patch

import install_central_class_data as delivery
from prepare_combined_expansion_data import digest
from prepare_review_expansion_delta import IDENTITIES
from install_review_expansion_delta import fingerprint


@contextmanager
def connection(path, **kwargs):
    db = sqlite3.connect(path, **kwargs)
    try:
        with db:
            yield db
    finally:
        db.close()


def run(workspace):
    package = json.loads((workspace/'Reports/combined_expansions/data_integration/proposal.json').read_text())
    schema_path = workspace/'ProtocolQA/run-20261102-053353/runtime/data/protocol-qa.sqlite3.db'
    with connection(schema_path.as_uri()+'?mode=ro', uri=True) as schema:
        schemas = {table: schema.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()[0] for table in IDENTITIES}
    root = workspace/'ExpansionRaceLab/ClassDataInstallerTests'
    root.mkdir(exist_ok=True)
    cases = []
    with tempfile.TemporaryDirectory(prefix='synthetic_', dir=root) as temporary:
        temp = Path(temporary).resolve()
        assert temp.is_relative_to(root.resolve())

        def fixture(name):
            base = temp/name
            game = base/'game'
            (game/'runtime/data').mkdir(parents=True)
            (game/'runtime/server/config').mkdir(parents=True)
            (base/'Backups').mkdir()
            (game/'runtime/server/config/serverconfig.xml').write_text('<Root><Server><Port>0</Port><UdpPort>0</UdpPort></Server></Root>')
            dbpath = game/'runtime/data/opendaoc.sqlite3.db'
            with connection(dbpath) as db:
                for sql in schemas.values():
                    db.execute(sql)
                db.execute('CREATE TABLE SyntheticPlayerProgress(Id TEXT PRIMARY KEY,Value INTEGER)')
                db.execute("INSERT INTO SyntheticPlayerProgress VALUES ('synthetic-player',123)")
                db.execute('CREATE TABLE ServerProperty(Key TEXT PRIMARY KEY,Value TEXT)')
                db.execute("INSERT INTO ServerProperty VALUES ('disabled_classes','39;58;62')")
                db.commit()
                before = fingerprint(db)
            rows = {table: originals[:1] for table, originals in package['rows'].items()}
            source = base/'Reports/combined_expansions/data_integration/proposal.json'
            source.parent.mkdir(parents=True)
            source.write_text(json.dumps({'rows': rows}))
            seal = base/'ExpansionRaceLab/CombinedExpansionServerCandidate/verified_joint_creation.json'
            seal.parent.mkdir(parents=True)
            seal.write_text(json.dumps({'passed': True,'preloaded_joint_data_accepted': True,'joint_class_behavior_cases': 7}))
            folder = base/'ExpansionRaceLab/CentralDelivery'
            folder.mkdir()
            (folder/'data_preview.json').write_text(json.dumps({'passed':True,'proposal_only':True,'activation_included':False,
                'source_proposal_sha256':digest(source),'memory_dry_run':{'all_existing_rows_preserved':True},
                'conflicts':[],'insert_rows':rows,'before_fingerprint':before}))
            return base, game, dbpath, before, rows

        base, game, dbpath, before, rows = fixture('success')
        assert delivery.install(base, game)['dry_run']
        assert delivery.install(base, game, True)['installed']
        with connection(dbpath) as db:
            assert fingerprint(db, rows) == before
        assert delivery.install(base, game, True)['already_current']
        cases.append('six-table application preserves every existing row; repeat is idempotent')

        base, game, dbpath, before, rows = fixture('rollback')
        def fail_after_first_insert(db, additions):
            partial = {table: (values if table == 'Spell' else []) for table, values in additions.items()}
            delivery.insert_delta_original(db, partial)
            raise RuntimeError('Injected write failure')
        with patch.object(delivery, 'insert_delta_original', delivery.insert_delta, create=True):
            with patch.object(delivery, 'insert_delta', fail_after_first_insert):
                try:
                    delivery.install(base, game, True)
                    raise AssertionError('Injected failure was not propagated')
                except RuntimeError as error:
                    assert str(error) == 'Injected write failure'
        with connection(dbpath) as db:
            assert fingerprint(db) == before
        assert not (base/'ExpansionRaceLab/CentralDelivery/installed_class_data.json').exists()
        cases.append('mid-transaction failure rolls back additions and preserves progress')

        base, game, dbpath, before, rows = fixture('stale')
        with connection(dbpath) as db:
            db.execute('UPDATE SyntheticPlayerProgress SET Value=456')
        try:
            delivery.install(base, game, True)
            raise RuntimeError('Stale progress was accepted')
        except AssertionError as error:
            assert 'world changed' in str(error)
        with connection(dbpath) as db:
            assert db.execute('SELECT Value FROM SyntheticPlayerProgress').fetchone()[0] == 456
            assert db.execute('SELECT COUNT(*) FROM Spell').fetchone()[0] == 0
        cases.append('changed player progress rejects stale preview without writes')

        base, game, dbpath, before, rows = fixture('occupied')
        with socket.socket() as occupied:
            occupied.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
            occupied.bind(('127.0.0.1',19727))
            try:
                delivery.install(base, game, True)
                raise AssertionError('Occupied bridge port was accepted')
            except OSError as error:
                assert error.winerror == 10048
        with connection(dbpath) as db:
            assert fingerprint(db) == before
        cases.append('occupied bridge port refuses installation before writes')
    result = {'passed':True,'synthetic_only':True,'cases':cases,'normal_database_modified':False}
    (root/'verified.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(run(args.workspace.resolve())))
