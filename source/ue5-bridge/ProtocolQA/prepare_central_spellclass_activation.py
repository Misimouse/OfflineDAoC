"""Prepare only Hibernian Bainshee/Vampiir eligibility; do not install or change the world."""
import argparse
import importlib.util
import json
from pathlib import Path
import sqlite3

from prepare_combined_expansion_data import digest
from install_review_expansion_delta import fingerprint
from snapshot_world_database import snapshot


def prepare(workspace, install):
    lab = workspace/'ExpansionRaceLab'
    output = lab/'CentralDelivery/SpellClassActivation'
    output.mkdir(exist_ok=True)
    data_receipt_path = lab/'CentralDelivery/installed_class_data.json'
    data_receipt = json.loads(data_receipt_path.read_text())
    assert data_receipt['installed'] and data_receipt['all_previous_rows_preserved']
    assert data_receipt['all_server_properties_preserved'] and not data_receipt['activation_included']
    minotaur_receipt = json.loads((lab/'CentralDelivery/MinotaurActivation/installed.json').read_text())
    assert minotaur_receipt['installed'] and minotaur_receipt['only_race_enabled'] == 21
    for row in minotaur_receipt['files']:
        assert digest(Path(row['target'])) == row['after_sha256']
    native_proof_path = workspace/'Reports/central_bainshee_forms/verified.json'
    native_proof = json.loads(native_proof_path.read_text())
    assert native_proof['passed'] and native_proof['installed_native_inputs_verified'] and len(native_proof['cases']) == 3
    repo = Path(__file__).resolve().parents[3]
    pipeline = repo/'source/new-client/pipeline/build_server_classes.py'
    spec = importlib.util.spec_from_file_location('spellclass_activation_rules', pipeline)
    rules = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rules)
    with snapshot(install/'runtime/data/opendaoc.sqlite3.db', lab/'TestTemp') as (db, metadata):
        before = fingerprint(db)
        properties = dict(db.execute("SELECT Key,Value FROM ServerProperty WHERE Key IN ('disabled_classes','disabled_races','start_as_base_class','enable_sluaghbinder')"))
        disabled = rules.id_set(properties['disabled_classes'])
        assert {39, 58, 62} <= disabled
        assert 21 not in rules.id_set(properties['disabled_races'])
        assert {16,17,18,19,20} <= rules.id_set(properties['disabled_races'])
        after = dict(properties, disabled_classes=';'.join(map(str,sorted(disabled-{39,58}))))
        memory = sqlite3.connect(':memory:')
        try:
            db.backup(memory)
            memory.execute("UPDATE ServerProperty SET Value=? WHERE Key='disabled_classes'",(after['disabled_classes'],))
            changed = fingerprint(memory)
            assert {k:v for k,v in changed.items() if k!='ServerProperty'} == {k:v for k,v in before.items() if k!='ServerProperty'}
            assert dict(memory.execute('SELECT Key,Value FROM ServerProperty')) == {**dict(db.execute('SELECT Key,Value FROM ServerProperty')),'disabled_classes':after['disabled_classes']}
        finally:
            memory.close()
    tiny = output/'properties.sqlite3.db'
    db = sqlite3.connect(tiny)
    try:
        db.execute('CREATE TABLE IF NOT EXISTS ServerProperty(Key TEXT PRIMARY KEY,Value TEXT)')
        db.execute('DELETE FROM ServerProperty')
        db.executemany('INSERT INTO ServerProperty VALUES (?,?)',after.items())
        db.commit()
    finally:
        db.close()
    rules.GS = lab/'CentralDelivery/MinotaurActivation/RulesSource'
    rules.DB, rules.OUT = tiny, output/'server_classes.json'
    rules.main()
    catalog = json.loads(rules.OUT.read_text())
    target = install/'new-client/godot/content/rules/server_classes.json'
    original = json.loads(target.read_text())
    assert set(catalog)-{'classes'} == set(original)-{'classes'}
    assert {k:v for k,v in catalog.items() if k not in ['classes','realms']} == {k:v for k,v in original.items() if k not in ['classes','realms']}
    assert set(catalog['realms']) == set(original['realms'])
    assert {key:[value for value in values if value not in [39,58]] for key,values in catalog['realms'].items()} == original['realms']
    assert set(catalog['classes'])-set(original['classes']) == {'39','58'}
    assert all(catalog['classes'][key] == value for key,value in original['classes'].items())
    assert catalog['classes']['39']['gender'] == 'female' and catalog['classes']['39']['races'] == [9,11,12]
    assert catalog['classes']['58']['races'] == [9,12]
    plan = {'passed':True,'installed':False,'normal_database_modified':False,'scope':'Classes39/58 only; existing races and classes preserved; no population/quests',
            'properties_before':properties,'properties_after':after,'before_fingerprint':before,'snapshot':metadata,
            'rules':catalog,'rules_source':str(rules.OUT),'rules_target':str(target),
            'rules_before_sha256':digest(target),'rules_after_sha256':digest(rules.OUT),
            'data_receipt_sha256':digest(data_receipt_path),'native_forms_proof_sha256':digest(native_proof_path),
            'candidate_receipt_sha256':digest(lab/'CombinedExpansionServerCandidate/build_receipt.json')}
    (output/'plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
    return {'passed':True,'installed':False,'classes_to_enable':[39,58],'races_changed':False,'old_eligibility_preserved':True,'mauler_still_disabled':62 in rules.id_set(after['disabled_classes'])}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ['workspace','install']:parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(prepare(args.workspace.resolve(),args.install.resolve())))
