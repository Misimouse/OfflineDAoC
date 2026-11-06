"""Activate only the accepted Hibernian Minotaur profile, with transactional progress preservation."""
import argparse
from contextlib import ExitStack
from datetime import datetime
import json
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import xml.etree.ElementTree as ET

from prepare_combined_expansion_data import digest
from install_review_expansion_delta import fingerprint
from snapshot_world_database import snapshot


def preserved(before, after):
    return {k: v for k, v in before.items() if k != 'ServerProperty'} == {k: v for k, v in after.items() if k != 'ServerProperty'}


def install(workspace, game, apply=False):
    output = workspace/'ExpansionRaceLab/CentralDelivery/MinotaurActivation'
    plan_path, extra_path = output/'plan.json', output/'godot_resources.json'
    plan, extra = json.loads(plan_path.read_text()), json.loads(extra_path.read_text())
    assert plan['passed'] and not plan['installed'] and extra['passed']
    assert extra['plan_sha256'] == digest(plan_path)
    assert plan['all_existing_rows_preserved_except_disabled_races_value']
    proof_path = workspace/'Reports/central_minotaur_activation/real_protocol.json'
    proof = json.loads(proof_path.read_text())
    assert all(proof.get(k) for k in ['passed', 'database_restored', 'appearance_profile_restored',
               'bridge_config_restored', 'candidate_files_restored', 'normal_shutdown'])
    assert proof['central_activation_plan_sha256'] == digest(plan_path)
    assert len(proof['cases']) == 4 and {r['selected_class'] for r in proof['cases']} == {43, 44, 45, 46}
    assert all(r['created'] and r['existing_character_reentry'] and r['original_spawn_and_bind_retained'] for r in proof['cases'])
    assert plan['properties_before']['disabled_classes'] == plan['properties_after']['disabled_classes']
    assert plan['properties_before']['enable_sluaghbinder'] == plan['properties_after']['enable_sluaghbinder']
    files = plan['files']+extra['files']
    assert len({row['target'] for row in files}) == len(files)
    receipt_path = output/'installed.json'
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
        assert receipt['installed'] and receipt['plan_sha256'] == digest(plan_path)
        assert all(digest(Path(row['target'])) == row['after_sha256'] for row in files)
        return {'passed': True, 'installed': True, 'already_current': True}
    for row in files:
        source, target = Path(row['source']).resolve(), Path(row['target']).resolve()
        assert source.is_relative_to(workspace.parent)
        assert target.is_relative_to(workspace) or target.is_relative_to(game/'new-client') or target.is_relative_to(game/'runtime/server')
        assert digest(source) == row['after_sha256']
        assert (digest(target) if target.exists() else None) == row['before_sha256'], ('Target changed since preparation', str(target))
    database = game/'runtime/data/opendaoc.sqlite3.db'
    with snapshot(database, workspace/'ExpansionRaceLab/TestTemp') as (copy, _):
        assert fingerprint(copy) == plan['before_fingerprint'], 'World/progress changed; prepare fresh activation evidence'
    summary = {'passed': True, 'dry_run': True, 'only_race_enabled': 21,
               'startup_rows': len(plan['startup_insert_rows']), 'files': len(files),
               'existing_tables_preserved': plan['existing_tables_verified'], 'other_restrictions_preserved': True}
    (output/'activation_dry_run.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    if not apply:
        return summary
    # Refuse running games/editors rather than replacing loaded libraries.
    check = subprocess.run(['powershell.exe', '-NoProfile', '-Command',
                            "@(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue).Count"],
                           capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
    assert check.stdout.strip() == '0', 'An editor/game is running; leave the pending activation intact'
    node = ET.parse(game/'runtime/server/config/serverconfig.xml').getroot().find('Server')
    ports = [(socket.SOCK_STREAM, int(node.findtext('Port'))),
             (socket.SOCK_DGRAM, int(node.findtext('UdpPort'))), (socket.SOCK_STREAM, 19727)]
    backup = workspace/'Backups'/('CentralMinotaurActivation_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    backup.mkdir(parents=True)
    assert backup.resolve().is_relative_to(workspace/'Backups')
    changed, saved = [], []
    committed = False
    with ExitStack() as stack:
        for kind, port in ports:
            guard = stack.enter_context(socket.socket(socket.AF_INET, kind))
            guard.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            guard.bind(('127.0.0.1', port))
            if kind == socket.SOCK_STREAM:
                guard.listen(1)
        db = sqlite3.connect(database)
        db.row_factory = sqlite3.Row
        try:
            assert fingerprint(db) == plan['before_fingerprint']
            destination = sqlite3.connect(backup/'before.sqlite3.db')
            try:
                db.backup(destination)
            finally:
                destination.close()
            for index, row in enumerate(files):
                item = dict(row)
                target = Path(row['target'])
                if target.exists():
                    saved_path = backup/(str(index)+'_'+target.name)
                    shutil.copy2(target, saved_path)
                    item['backup'] = str(saved_path)
                    assert digest(saved_path) == row['before_sha256']
                else:
                    item['backup'] = None
                saved.append(item)
            (backup/'rollback.json').write_text(json.dumps(saved, indent=2), encoding='utf-8')
            db.execute('BEGIN IMMEDIATE')
            assert fingerprint(db) == plan['before_fingerprint']
            original_properties = {row['Key']: dict(row) for row in db.execute('SELECT * FROM ServerProperty')}
            for row in plan['startup_insert_rows']:
                assert row['RaceID'] == 21 and row['ClassID'] in [52, 53]
                columns = list(row)
                db.execute('INSERT INTO StartupLocation ('+','.join('"'+k+'"' for k in columns)+') VALUES ('+','.join('?' for _ in columns)+')', list(row.values()))
            changed_property = db.execute("UPDATE ServerProperty SET Value=? WHERE Key='disabled_races' AND Value=?",
                                          (plan['properties_after']['disabled_races'], plan['properties_before']['disabled_races']))
            assert changed_property.rowcount == 1
            after = fingerprint(db, {'StartupLocation': plan['startup_insert_rows']})
            assert preserved(plan['before_fingerprint'], after)
            expected_properties = {key: dict(value) for key, value in original_properties.items()}
            expected_properties['disabled_races']['Value'] = plan['properties_after']['disabled_races']
            assert {row['Key']: dict(row) for row in db.execute('SELECT * FROM ServerProperty')} == expected_properties
            assert db.execute('PRAGMA quick_check').fetchone()[0] == 'ok'
            for row in saved:
                target = Path(row['target'])
                assert (digest(target) if target.exists() else None) == row['before_sha256']
                target.parent.mkdir(parents=True, exist_ok=True)
                changed.append(row)
                shutil.copy2(row['source'], target)
                assert digest(target) == row['after_sha256']
            receipt = {'installed': False, 'phase': 'files_verified_database_pending', 'plan_sha256': digest(plan_path),
                       'backup_directory': str(backup), 'only_race_enabled': 21, 'world_population_imported': False,
                       'existing_tables_verified': len(after), 'all_existing_progress_rows_preserved': True,
                       'source_build_profile': 'Canonical bridge overlay + joint candidate; runtime retains disabled classes39/58/62 and races16-20.',
                       'original_start_zone': 207, 'startup_rows_added': len(plan['startup_insert_rows']), 'files': saved}
            receipt_path.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
            db.commit()
            committed = True
            receipt.update(installed=True, phase='complete')
            receipt_path.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
        except BaseException:
            if not committed:
                db.rollback()
                for row in reversed(changed):
                    target = Path(row['target']).resolve()
                    assert target.is_relative_to(workspace) or target.is_relative_to(game/'new-client') or target.is_relative_to(game/'runtime/server')
                    if row['backup']:
                        shutil.copy2(row['backup'], target)
                        assert digest(target) == row['before_sha256']
                    else:
                        target.unlink(missing_ok=True)
                receipt_path.unlink(missing_ok=True)
            raise
        finally:
            db.close()
    return {key: value for key, value in receipt.items() if key != 'files'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--install', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    print(json.dumps(install(args.workspace.resolve(), args.install.resolve(), args.apply)))
