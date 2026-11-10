"""Exact single-file trainer budget delivery; no native, map or DB replacement."""
import json
from pathlib import Path
from prepare_combined_expansion_data import digest

def read(path):return json.loads(path.read_text(encoding='utf-8'))

def validate(workspace,data,check_target=True):
    assert data['phase']=='complete' and data['installed']
    assert not any(data[k] for k in ['database_modified','native_modified','server_rules_modified','map_modified'])
    assert digest(workspace/'RealmWarKeysLab/installed.json')==data['predecessor_sha256']
    native=workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    assert read(workspace/'RealmWarKeysLab/installed.json')['native_after_sha256']==data['native_sha256']
    assert len(data['files'])==1
    row=data['files'][0];target=workspace/'Godot/trainer_state.gd'
    source=Path(__file__).resolve().parents[1]/'Godot/trainer_state.gd'
    assert row['target']==str(target) and row['source']==str(source)
    base=read(workspace/'TrainerAffordabilityLab/runtime_baseline.json')
    assert row['before_sha256']==base['trainer_before_sha256']!=row['after_sha256']
    assert digest(Path(base['red_test_original']))==base['red_test_original_sha256']==row['before_sha256']
    proof_paths=[Path(data['proofs'][k]) for k in ['state','real']]
    assert all(p.resolve().is_relative_to((workspace/'TrainerAffordabilityLab').resolve()) for p in proof_paths)
    assert set(data['evidence'])=={str(p) for p in proof_paths+[workspace/'TrainerAffordabilityLab/runtime_baseline.json']}
    assert all(digest(Path(p))==h for p,h in data['evidence'].items())
    state=read(Path(data['proofs']['state']));real=read(Path(data['proofs']['real']))
    assert state['passed'] and sum(r['checks'] for r in state['reports'])>=89
    assert real['passed'] and len(real['checks'])>=19 and all(real['checks'].values())
    assert real['database_restored'] and real['normal_shutdown'] and real['normal_runtime_unchanged']
    assert state['source_inputs'][str(source)]==real['source_inputs'][str(source)]==row['after_sha256']
    if check_target:assert digest(target)==row['after_sha256']
    return data

def verify(workspace):
    path=workspace/'TrainerAffordabilityLab/installed.json'
    if not path.exists():return None
    data=read(path)
    return validate(workspace,data) if data.get('installed') else None
