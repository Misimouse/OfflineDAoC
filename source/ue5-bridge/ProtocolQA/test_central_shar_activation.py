"""Exercise Shar's real SQLite transaction and file rollback on synthetic saves only."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
from unittest.mock import patch
import install_central_shar_activation as delivery
from install_review_expansion_delta import fingerprint
from prepare_combined_expansion_data import digest


def put(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value),encoding='utf-8')


def verify(workspace):
    root=workspace/'ExpansionRaceLab/TestTemp';root.mkdir(exist_ok=True)
    checks=0
    for mode in ['success','copy_failure','stale_eligibility']:
        with tempfile.TemporaryDirectory(dir=root,prefix='shar_transaction_') as temporary:
            folder=Path(temporary).resolve();assert folder.is_relative_to(root.resolve())
            w=folder/'bridge';game=folder/'game';out=w/'ExpansionRaceLab/CentralDelivery/SharActivation'
            target=game/'new-client/godot/content/rules/server_classes.json';put(target,{'old':True})
            source=out/'server_classes.json';put(source,{'shar':True})
            properties={'disabled_races':'16;17;18;19;20','disabled_classes':'62','start_as_base_class':'True','enable_sluaghbinder':'False'}
            after=dict(properties,disabled_races='16;17;19;20')
            previous=out.parent/'SpellClassActivation/installed.json';put(previous,{'synthetic':True})
            plan_path=out/'plan.json';plan={'passed':True,'installed':False,'only_race_enabled':18,
                'predecessor_receipt_sha256':digest(previous),'properties_before':properties,'properties_after':after,
                'rules_source':str(source),'rules_target':str(target),'rules_before_sha256':digest(target),'rules_after_sha256':digest(source)}
            put(plan_path,plan)
            for name,count in [('creation',10),('vampiir',6),('gm_transfer',10)]:
                row={k:True for k in ['passed','normal_shutdown','database_restored','appearance_profile_restored','bridge_config_restored','candidate_files_restored','server_authorized_gm_transfer','original_spawn_and_bind_preserved_before_entry']}
                row.update(errors=[],central_shar_plan_sha256=digest(plan_path),combined_choices_verified={'bainshee':3,'vampiir':6,'shar':12,'minotaur':4},
                    cases=[{k:True for k in ['created','existing_character_reentry','spell_list_complete','saved_return','appearance_retained']} for _ in range(count)])
                put(w/'Reports/central_shar_activation'/name/'real_protocol.json',row)
            put(w/'Reports/central_shar_activation/native/verified.json',{'passed':True,'installed_native_inputs':True,'cases':dict.fromkeys(range(4),{}),'inputs':{str(source):digest(source)}})
            database=game/'runtime/data/opendaoc.sqlite3.db';database.parent.mkdir(parents=True)
            with closing(sqlite3.connect(database)) as db:
                db.execute('CREATE TABLE ServerProperty(Key TEXT PRIMARY KEY,Value TEXT)');db.executemany('INSERT INTO ServerProperty VALUES (?,?)',properties.items())
                db.execute('CREATE TABLE DOLCharacters(Name TEXT PRIMARY KEY,Level INTEGER)');db.execute("INSERT INTO DOLCharacters VALUES ('SyntheticOwner',27)")
                db.execute('CREATE TABLE Mob(Id TEXT PRIMARY KEY,Model INTEGER)');db.execute("INSERT INTO Mob VALUES ('preserved',1075)")
                db.commit();before=fingerprint(db)
            (w/'Backups').mkdir()
            original_copy=delivery.shutil.copy2
            def copy(src,dest,*args,**kwargs):
                result=original_copy(src,dest,*args,**kwargs)
                if mode=='copy_failure' and Path(src)==source:raise OSError('Synthetic failure after copying rules')
                return result
            if mode=='stale_eligibility':
                with closing(sqlite3.connect(database)) as db:db.execute("UPDATE ServerProperty SET Value='16;18' WHERE Key='disabled_races'");db.commit();before=fingerprint(db)
            # Keep proof validation and real SQL/file operations; only the outer
            # previously-tested receipt chain is synthetic in this unit fixture.
            with patch.object(delivery,'verify_files',return_value={'passed':True}),patch.object(delivery.shutil,'copy2',side_effect=copy):
                try:result=delivery.install(w,game,True)
                except (OSError,AssertionError):assert mode!='success'
                else:assert mode=='success' and result['installed']
            with closing(sqlite3.connect(database)) as db:
                current=fingerprint(db)
                if mode=='success':
                    assert {k:v for k,v in current.items() if k!='ServerProperty'}=={k:v for k,v in before.items() if k!='ServerProperty'}
                    assert dict(db.execute('SELECT Key,Value FROM ServerProperty'))==after
                    assert digest(target)==plan['rules_after_sha256'];checks+=1
                else:
                    assert current==before and digest(target)==plan['rules_before_sha256'];checks+=1
    return {'passed':True,'checks':checks,'synthetic_database_only':True}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--workspace',type=Path,required=True)
    print(json.dumps(verify(parser.parse_args().workspace.resolve())))
