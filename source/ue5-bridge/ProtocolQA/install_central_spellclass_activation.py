"""Activate only accepted Bainshee/Vampiir choices, preserving every existing progress row."""
import argparse
from contextlib import ExitStack, closing
from datetime import datetime
import json
from pathlib import Path
import shutil
import socket
import sqlite3
import xml.etree.ElementTree as ET

from central_activation_receipts import verify_files
from prepare_combined_expansion_data import digest
from install_review_expansion_delta import fingerprint
from snapshot_world_database import snapshot


def install(workspace, game, apply=False):
    root=workspace/'ExpansionRaceLab/CentralDelivery'
    output=root/'SpellClassActivation'
    plan_path=output/'plan.json'
    plan=json.loads(plan_path.read_text())
    assert plan['passed'] and not plan['installed'] and not plan['normal_database_modified']
    assert plan['data_receipt_sha256']==digest(root/'installed_class_data.json')
    assert plan['native_forms_proof_sha256']==digest(workspace/'Reports/central_bainshee_forms/verified.json')
    native_proof=json.loads((workspace/'Reports/central_bainshee_forms/verified.json').read_text())
    assert native_proof['passed'] and native_proof['installed_native_inputs_verified']
    for case in native_proof['cases']:
        assert all(digest(Path(path))==sha for path,sha in case['native_inputs'].items())
    assert plan['candidate_receipt_sha256']==digest(workspace/'ExpansionRaceLab/CombinedExpansionServerCandidate/build_receipt.json')
    for name,count,selected in [('bainshee',3,39),('vampiir',4,58)]:
        proof=json.loads((workspace/'Reports/central_spellclass_activation'/name/'real_protocol.json').read_text())
        assert all(proof.get(k) for k in ['passed','normal_shutdown','database_restored','appearance_profile_restored','bridge_config_restored','candidate_files_restored'])
        assert proof['central_spellclass_plan_sha256']==digest(plan_path) and not proof['errors']
        assert len(proof['cases'])==count and all(r['selected_class']==selected and all(r[k] for k in ['created','existing_character_reentry','spell_list_complete','saved_return','appearance_retained']) for r in proof['cases'])
        assert proof['combined_choices_verified']=={'bainshee':3,'vampiir':4,'shar':0,'minotaur':4}
    verify_files(workspace)
    receipt_path=output/'installed.json'
    if receipt_path.exists():
        assert json.loads(receipt_path.read_text())['installed']
        return {'passed':True,'installed':True,'already_current':True}
    source,target=Path(plan['rules_source']).resolve(),Path(plan['rules_target']).resolve()
    assert source==output/'server_classes.json'
    assert target==game/'new-client/godot/content/rules/server_classes.json'
    assert digest(source)==plan['rules_after_sha256'] and digest(target)==plan['rules_before_sha256']
    assert all(plan['properties_before'][key]==value for key,value in plan['properties_after'].items() if key!='disabled_classes')
    database=game/'runtime/data/opendaoc.sqlite3.db'
    with snapshot(database,workspace/'ExpansionRaceLab/TestTemp') as (db,_):
        assert fingerprint(db)==plan['before_fingerprint'], 'Installed progress changed; prepare a fresh plan'
    result={'passed':True,'installed':False,'classes_enabled':[39,58],'races_changed':False,'world_population_imported':False}
    if not apply:return dict(result,dry_run=True)
    node=ET.parse(game/'runtime/server/config/serverconfig.xml').getroot().find('Server')
    with ExitStack() as stack:
        for kind,port in [(socket.SOCK_STREAM,int(node.findtext('Port'))),(socket.SOCK_DGRAM,int(node.findtext('UdpPort'))),(socket.SOCK_STREAM,19727)]:
            guard=stack.enter_context(socket.socket(socket.AF_INET,kind))
            guard.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
            guard.bind(('127.0.0.1',port))
            if kind==socket.SOCK_STREAM:guard.listen(1)
        backup=workspace/'Backups'/('CentralSpellClassActivation_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        backup.mkdir()
        assert backup.resolve().is_relative_to(workspace/'Backups')
        db=sqlite3.connect(database)
        db.row_factory=sqlite3.Row
        committed=False
        copied=False
        try:
            assert fingerprint(db)==plan['before_fingerprint']
            with closing(sqlite3.connect(backup/'before.sqlite3.db')) as destination:
                db.backup(destination)
                assert destination.execute('PRAGMA quick_check').fetchone()[0]=='ok'
            shutil.copy2(target,backup/'server_classes.json')
            assert digest(backup/'server_classes.json')==plan['rules_before_sha256']
            db.execute('BEGIN IMMEDIATE')
            assert fingerprint(db)==plan['before_fingerprint']
            properties={row['Key']:dict(row) for row in db.execute('SELECT * FROM ServerProperty')}
            changed=db.execute("UPDATE ServerProperty SET Value=? WHERE Key='disabled_classes' AND Value=?",(plan['properties_after']['disabled_classes'],plan['properties_before']['disabled_classes']))
            assert changed.rowcount==1
            after=fingerprint(db)
            assert {k:v for k,v in after.items() if k!='ServerProperty'}=={k:v for k,v in plan['before_fingerprint'].items() if k!='ServerProperty'}
            properties['disabled_classes']['Value']=plan['properties_after']['disabled_classes']
            assert {row['Key']:dict(row) for row in db.execute('SELECT * FROM ServerProperty')}==properties
            assert db.execute('PRAGMA quick_check').fetchone()[0]=='ok'
            assert digest(target)==plan['rules_before_sha256']
            copied=True
            shutil.copy2(source,target)
            assert digest(target)==plan['rules_after_sha256']
            result.update(phase='rules_verified_transaction_pending',backup_directory=str(backup),
                plan_sha256=digest(plan_path),minotaur_receipt_sha256=digest(root/'MinotaurActivation/installed.json'),
                rules_target=str(target),rules_before_sha256=plan['rules_before_sha256'],rules_after_sha256=plan['rules_after_sha256'],
                existing_tables_verified=len(after),all_previous_progress_preserved=True)
            receipt_path.write_text(json.dumps(result,indent=2),encoding='utf-8')
            db.commit()
            committed=True
            result.update(installed=True,phase='complete')
            receipt_path.write_text(json.dumps(result,indent=2),encoding='utf-8')
        except BaseException:
            if not committed:
                db.rollback()
                if copied:
                    shutil.copy2(backup/'server_classes.json',target)
                    assert digest(target)==plan['rules_before_sha256']
                receipt_path.unlink(missing_ok=True)
            raise
        finally:db.close()
    verify_files(workspace)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['workspace','install']:parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    print(json.dumps(install(args.workspace.resolve(),args.install.resolve(),args.apply)))
