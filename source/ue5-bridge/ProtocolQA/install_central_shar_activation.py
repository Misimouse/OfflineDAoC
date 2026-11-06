"""Enable only accepted Shar eligibility; preserve every current save and world row."""
import argparse
from contextlib import ExitStack, closing
from datetime import datetime
import json
from pathlib import Path
import shutil
import socket
import sqlite3
from central_activation_receipts import verify_files
from install_review_expansion_delta import fingerprint
from prepare_combined_expansion_data import digest


def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))


def install(workspace,game,apply=False):
    root=workspace/'ExpansionRaceLab/CentralDelivery';output=root/'SharActivation'
    receipt_path=output/'installed.json'
    if receipt_path.exists() and read(receipt_path).get('installed'):
        verify_files(workspace);return {'passed':True,'installed':True,'already_current':True}
    verify_files(workspace)
    plan_path=output/'plan.json';plan=read(plan_path)
    assert plan['passed'] and not plan['installed'] and plan['only_race_enabled']==18
    predecessor=root/'SpellClassActivation/installed.json'
    assert plan['predecessor_receipt_sha256']==digest(predecessor)
    evidence={}
    for name,count in [('creation',10),('vampiir',6),('gm_transfer',10)]:
        path=workspace/'Reports/central_shar_activation'/name/'real_protocol.json';proof=read(path)
        assert all(proof.get(k) for k in ['passed','normal_shutdown','database_restored','appearance_profile_restored','bridge_config_restored','candidate_files_restored'])
        assert not proof['errors'] and proof['central_shar_plan_sha256']==digest(plan_path)
        assert len(proof['cases'])==count and all(all(row[k] for k in ['created','existing_character_reentry','spell_list_complete','saved_return','appearance_retained']) for row in proof['cases'])
        assert proof['combined_choices_verified']=={'bainshee':3,'vampiir':6,'shar':12,'minotaur':4}
        if name=='gm_transfer':assert proof['server_authorized_gm_transfer'] and proof['original_spawn_and_bind_preserved_before_entry']
        evidence[str(path)]=digest(path)
    path=workspace/'Reports/central_shar_activation/native/verified.json';native=read(path)
    assert native['passed'] and native['installed_native_inputs'] and len(native['cases'])==4
    assert all(digest(Path(p))==sha for p,sha in native['inputs'].items())
    evidence[str(path)]=digest(path)
    source=Path(plan['rules_source']);target=Path(plan['rules_target'])
    assert source==output/'server_classes.json' and target==game/'new-client/godot/content/rules/server_classes.json'
    assert digest(source)==plan['rules_after_sha256'] and digest(target)==plan['rules_before_sha256']
    assert {k:v for k,v in plan['properties_after'].items() if k!='disabled_races'}=={k:v for k,v in plan['properties_before'].items() if k!='disabled_races'}
    assert set(plan['properties_before']['disabled_races'].split(';'))-set(plan['properties_after']['disabled_races'].split(';'))=={'18'}
    result={'passed':True,'installed':False,'only_race_enabled':18,'world_population_imported':False,'classes_changed':False}
    if not apply:return dict(result,dry_run=True)
    database=game/'runtime/data/opendaoc.sqlite3.db'
    with ExitStack() as stack:
        for kind,port in [(socket.SOCK_STREAM,10300),(socket.SOCK_DGRAM,10400),(socket.SOCK_STREAM,19727)]:
            guard=stack.enter_context(socket.socket(socket.AF_INET,kind));guard.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1);guard.bind(('127.0.0.1',port))
            if kind==socket.SOCK_STREAM:guard.listen(1)
        backup=workspace/'Backups'/('CentralSharActivation_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'));backup.mkdir()
        db=sqlite3.connect(database);db.row_factory=sqlite3.Row;copied=False;committed=False
        try:
            # Preserve the live baseline, including any progress made since the proposal.
            # Only eligibility must still equal the reviewed predecessor policy.
            before=fingerprint(db)
            assert dict(db.execute("SELECT Key,Value FROM ServerProperty WHERE Key IN ('disabled_classes','disabled_races','start_as_base_class','enable_sluaghbinder')"))==plan['properties_before']
            with closing(sqlite3.connect(backup/'before.sqlite3.db')) as dest:db.backup(dest);assert dest.execute('PRAGMA quick_check').fetchone()[0]=='ok'
            shutil.copy2(target,backup/'server_classes.json')
            db.execute('BEGIN IMMEDIATE');assert fingerprint(db)==before
            properties={row['Key']:dict(row) for row in db.execute('SELECT * FROM ServerProperty')}
            changed=db.execute("UPDATE ServerProperty SET Value=? WHERE Key='disabled_races' AND Value=?",(plan['properties_after']['disabled_races'],plan['properties_before']['disabled_races']));assert changed.rowcount==1
            after=fingerprint(db);assert {k:v for k,v in after.items() if k!='ServerProperty'}=={k:v for k,v in before.items() if k!='ServerProperty'}
            properties['disabled_races']['Value']=plan['properties_after']['disabled_races']
            assert {row['Key']:dict(row) for row in db.execute('SELECT * FROM ServerProperty')}==properties
            assert digest(target)==plan['rules_before_sha256'];copied=True;shutil.copy2(source,target);assert digest(target)==plan['rules_after_sha256']
            result.update(phase='transaction_pending',plan_sha256=digest(plan_path),predecessor_receipt_sha256=digest(predecessor),
                rules_target=str(target),rules_before_sha256=plan['rules_before_sha256'],rules_after_sha256=plan['rules_after_sha256'],
                all_previous_progress_preserved=True,existing_tables_verified=len(after),backup_directory=str(backup),evidence=evidence)
            receipt_path.write_text(json.dumps(result,indent=2),encoding='utf-8')
            db.commit();committed=True;result.update(installed=True,phase='complete');receipt_path.write_text(json.dumps(result,indent=2),encoding='utf-8')
        except BaseException:
            if not committed:
                db.rollback()
                if copied:shutil.copy2(backup/'server_classes.json',target)
                if receipt_path.exists():receipt_path.unlink()
            raise
        finally:db.close()
    verify_files(workspace)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['workspace','install']:parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    print(json.dumps(install(args.workspace.resolve(),args.install.resolve(),args.apply)))
