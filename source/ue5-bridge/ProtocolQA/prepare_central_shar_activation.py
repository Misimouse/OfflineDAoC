"""Prepare Shar-only eligibility against current installed rules; no normal writes."""
import argparse
import importlib.util
import json
from pathlib import Path
import sqlite3
from central_activation_receipts import verify_files
from install_review_expansion_delta import fingerprint
from prepare_combined_expansion_data import digest
from snapshot_world_database import snapshot


def prepare(workspace,install):
    verify_files(workspace)
    lab=workspace/'ExpansionRaceLab';output=lab/'CentralDelivery/SharActivation';output.mkdir(exist_ok=True)
    assert not (output/'installed.json').exists(),'Already delivered; preserve the historical plan'
    repo=Path(__file__).resolve().parents[3]
    spec=importlib.util.spec_from_file_location('shar_rules',repo/'source/new-client/pipeline/build_server_classes.py')
    rules=importlib.util.module_from_spec(spec);spec.loader.exec_module(rules)
    with snapshot(install/'runtime/data/opendaoc.sqlite3.db',lab/'TestTemp') as (db,metadata):
        before=fingerprint(db)
        properties=dict(db.execute("SELECT Key,Value FROM ServerProperty WHERE Key IN ('disabled_classes','disabled_races','start_as_base_class','enable_sluaghbinder')"))
        disabled=rules.id_set(properties['disabled_races'])
        assert 18 in disabled and 21 not in disabled
        assert {39,58}.isdisjoint(rules.id_set(properties['disabled_classes']))
        assert 62 in rules.id_set(properties['disabled_classes'])
        starts=[dict(zip([d[0] for d in cursor.description],row)) for cursor in [db.execute('SELECT * FROM StartupLocation WHERE RaceID=18 AND Region=200 AND ClientRegionID=0')] for row in cursor]
        assert len(starts)==3
        after=dict(properties,disabled_races=';'.join(map(str,sorted(disabled-{18}))))
    tiny=output/'properties.sqlite3.db'
    with sqlite3.connect(tiny) as db:
        db.execute('CREATE TABLE IF NOT EXISTS ServerProperty(Key TEXT PRIMARY KEY,Value TEXT)');db.execute('DELETE FROM ServerProperty')
        db.executemany('INSERT INTO ServerProperty VALUES (?,?)',after.items())
    rules.GS=lab/'CentralDelivery/MinotaurActivation/RulesSource';rules.DB=tiny;rules.OUT=output/'server_classes.json';rules.main()
    target=install/'new-client/godot/content/rules/server_classes.json'
    old=json.loads(target.read_text());new=json.loads(rules.OUT.read_text())
    assert {k:v for k,v in new.items() if k!='classes'}=={k:v for k,v in old.items() if k!='classes'}
    assert set(new['classes'])==set(old['classes'])
    admitted=[]
    for key,row in new['classes'].items():
        previous=old['classes'][key]
        assert {k:v for k,v in row.items() if k!='races'}=={k:v for k,v in previous.items() if k!='races'}
        assert [r for r in row['races'] if r!=18]==previous['races']
        if 18 in row['races']:admitted.append(int(key))
    assert set(admitted)=={42,43,44,45,50,58}
    plan={'passed':True,'installed':False,'normal_database_modified':False,'only_race_enabled':18,
        'properties_before':properties,'properties_after':after,'before_fingerprint':before,'snapshot':metadata,
        'rules':new,'rules_source':str(rules.OUT),'rules_target':str(target),'rules_before_sha256':digest(target),'rules_after_sha256':digest(rules.OUT),
        'admitted_classes':sorted(admitted),'original_shar_starts':starts,
        'candidate_receipt_sha256':digest(lab/'CombinedExpansionServerCandidate/build_receipt.json'),
        'predecessor_receipt_sha256':digest(lab/'CentralDelivery/SpellClassActivation/installed.json'),
        'scope':'Shar18 only; preserve current classes, original starts, progress and deferred world population; Connacht test map only'}
    (output/'plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
    return {'passed':True,'installed':False,'only_race_enabled':18,'classes':sorted(admitted),'original_starts':len(starts)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['workspace','install']:parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args();print(json.dumps(prepare(args.workspace.resolve(),args.install.resolve())))
