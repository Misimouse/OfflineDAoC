"""One-file original ModelChange size semantics; no native/server/map replacement."""
import json
from pathlib import Path
from prepare_combined_expansion_data import digest

def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))

def validate(workspace,data,check_target=True):
    root=workspace/'RemoteModelRoundtripLab'
    assert data['installed'] and data['phase']=='complete'
    assert not any(data[k] for k in ['database_modified','native_modified','server_rules_modified','map_modified'])
    predecessor=workspace/'CharacterInventorySwitchLab/installed.json'
    assert digest(predecessor)==data['predecessor_sha256'] and read(predecessor)['installed']
    assert read(predecessor)['native_sha256']==data['native_sha256']
    native=workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    from remote_model_equipment_receipts import verify as verify_equipment
    successor,replacements=verify_equipment(workspace)
    replacement=replacements.get(str(native))
    if replacement:
        from player_trade_receipts import verify as verify_trade, predecessor_hash
        _,trade_rows=verify_trade(workspace)
        assert predecessor_hash(native,trade_rows)==replacement['after_sha256'] and replacement['before_sha256']==data['native_sha256']
    else:assert digest(native)==data['native_sha256']
    assert len(data['files'])==1
    row=data['files'][0];source=Path(__file__).resolve().parents[1]/'Godot/decoded_world_adapter.gd'
    assert row['source']==str(source) and row['target']==str(workspace/'Godot/decoded_world_adapter.gd')
    assert row['before_sha256']!=row['after_sha256']
    red=Path(data['red_proof']);green=Path(data['state_proof'])
    assert all(p.resolve().is_relative_to(root.resolve()) for p in [red,green])
    assert set(data['evidence'])=={str(red),str(green)}
    assert all(digest(Path(p))==sha for p,sha in data['evidence'].items())
    old=read(red);new=read(green)
    assert not old['passed'] and old['reports'][0]['failures']
    assert old['source_inputs'][str(source)]==row['before_sha256']
    assert digest(red.parent/'Project/decoded_world_adapter.gd')==row['before_sha256']
    assert new['passed'] and sum(r['checks'] for r in new['reports'])>=105
    assert all(r['passed'] and not r['failures'] and r['exit_code']==0 for r in new['reports'])
    assert not new['server_started'] and not new['normal_installation_modified']
    assert new['source_inputs'][str(source)]==row['after_sha256']
    assert digest(green.parent/'Project/decoded_world_adapter.gd')==row['after_sha256']
    if check_target:assert digest(Path(row['target']))==row['after_sha256']
    return data

def verify(workspace):
    path=workspace/'RemoteModelRoundtripLab/installed.json'
    if not path.exists():return None,{}
    data=read(path)
    return (validate(workspace,data),{r['target']:r for r in data['files']}) if data.get('installed') else (None,{})
