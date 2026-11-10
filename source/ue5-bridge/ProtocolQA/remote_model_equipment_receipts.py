"""Exact native remote-form attachment successor; no gameplay data or art edits."""
import json
from pathlib import Path
from prepare_combined_expansion_data import digest

def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))

def inventory(workspace):
    root=workspace/'RemoteModelEquipmentLab';build=read(root/'native_build.json');candidate=Path(build['project']).parent/'Plugins/DAoCVisualBridge';normal=workspace/'Client/Plugins/DAoCVisualBridge'
    producer=Path(__file__).resolve().parents[1]/'UnrealPlugin/DAoCVisualBridge'
    return [(candidate/'Binaries/Win64'/n,normal/'Binaries/Win64'/n) for n in ['UnrealEditor-DAoCVisualBridge.dll','UnrealEditor.modules']]+[(producer/'Source/DAoCVisualBridge/Private/DAoCBridgeEquipment.cpp',normal/'Source/DAoCVisualBridge/Private/DAoCBridgeEquipment.cpp')]

def validate(workspace,data,check_target=True,successor_rows=None):
    root=workspace/'RemoteModelEquipmentLab';predecessor=workspace/'RemoteModelRoundtripLab/installed.json'
    assert data['installed'] and data['phase']=='complete'
    assert not any(data[k] for k in ['database_modified','server_rules_modified','map_modified','art_modified'])
    assert digest(predecessor)==data['predecessor_sha256'] and read(predecessor)['installed']
    old=read(workspace/'RealmWarKeysLab/native_build.json');build=read(root/'native_build.json')
    assert build['passed'] and build['normal_binary_sha256']==read(predecessor)['native_sha256']==data['native_before_sha256']
    changed={k for k in build['source_sha256'] if build['source_sha256'][k]!=old['source_sha256'].get(k)}
    key=str(Path('DAoCVisualBridge/Private/DAoCBridgeEquipment.cpp'))
    assert changed=={key} and old['source_sha256'].keys()==build['source_sha256'].keys()
    assert data['native_after_sha256']==build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll']!=data['native_before_sha256']
    expected=inventory(workspace);rows={r['target']:r for r in data['files']};assert len(rows)==len(data['files'])==3 and set(rows)=={str(t) for _,t in expected}
    for source,target in expected:
        row=rows[str(target)];assert row['source']==str(source)
        after=build['source_sha256'][key] if source.suffix=='.cpp' else build['binaries_sha256'][source.name]
        before=old['source_sha256'][key] if source.suffix=='.cpp' else old['binaries_sha256'][source.name]
        assert row['after_sha256']==after and row['before_sha256']==before
        if check_target:
            from player_trade_receipts import predecessor_hash
            assert predecessor_hash(target,successor_rows or {})==after
    paths=[Path(data['proofs'][k]) for k in ['red','candidate','regression']]+[root/'native_build.json']
    assert all(p.resolve().is_relative_to(root.resolve()) for p in paths)
    assert set(data['evidence'])=={str(p) for p in paths} and all(digest(Path(p))==h for p,h in data['evidence'].items())
    red=read(paths[0]);candidate=read(paths[1]);regression=read(paths[2])
    assert red['passed'] and red['morph_has_visible_weapon_bindings'] and red['original_count']==red['restored_count']==2
    assert candidate['passed'] and candidate['candidate'] and not candidate['morph_has_visible_weapon_bindings']
    assert candidate['source_inputs'][str(root/'native_build.json')]==digest(root/'native_build.json')
    assert all(candidate['observations'][label]['remote_visible_count']==0 for label in ['transformed','form_1884','form_1885'])
    assert all(candidate['observations'][label]['remote_visible_count']==2 for label in ['original','restored','npc_form_control'])
    assert regression['passed'] and regression['checks']>=80 and not regression['normal_runtime_modified']
    return data

def verify(workspace,successor_rows=None):
    if successor_rows is None:
        from player_trade_receipts import verify as verify_trade
        _,successor_rows=verify_trade(workspace)
    path=workspace/'RemoteModelEquipmentLab/installed.json'
    if not path.exists():return None,{}
    data=read(path)
    return (validate(workspace,data,successor_rows=successor_rows),{r['target']:r for r in data['files']}) if data.get('installed') else (None,{})
