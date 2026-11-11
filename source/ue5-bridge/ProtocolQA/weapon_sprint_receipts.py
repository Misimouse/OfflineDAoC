"""Exact eight-file original weapon/sprint controls successor."""
from pathlib import Path
from npc_ghost_receipts import read
from prepare_combined_expansion_data import digest

NATIVE_TARGETS = ['Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll','Binaries/Win64/UnrealEditor.modules'] + [
    'Source/DAoCVisualBridge/Private/'+name for name in ['DAoCBridgeKeyConfiguration.cpp',
        'DAoCBridgeKeyConfigurationAcceptance.cpp','DAoCBridgePlayerStatus.cpp']]
GODOT_TARGETS = ['live_gateway.gd','visual_bridge.gd','weapon_sprint_state.gd']


def expected_files(workspace,proofs,verify_sources=True,successor_rows=None):
    from player_trade_receipts import predecessor_hash

    lab = workspace/'OriginalControlsLab'
    build = read(lab/'native_build.json')
    old = read(workspace/'NpcEffectsLab/native_build.json')
    state,gateway = read(lab/'state_tests.json'),read(lab/'gateway_tests.json')
    native,ui,real = [read(Path(proofs[k])) for k in ['native','ui','real']]
    assert build['passed'] and build['normal_binary_sha256'] == old['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll']
    assert state['passed'] and state['checks'] >= 58 and state['original_switch_weapon_executed']
    assert gateway['passed'] and {r['test']:r['checks'] for r in gateway['reports']} == {
        'test_weapon_sprint_gateway.gd':8,'test_personal_torch_gateway.gd':261,
        'test_live_riding_gateway.gd':8,'test_remote_player_state.gd':69}
    assert native['passed'] and native['checks'] >= 292 and native['build_receipt_sha256'] == digest(lab/'native_build.json')
    assert ui['passed'] and ui['build_receipt_sha256'] == digest(lab/'native_build.json')
    assert set(ui['reports']) == {'classic','player'} and all(r['passed'] and r['checks'] >= 68 for r in ui['reports'].values())
    assert real['passed'] and len(real['checks']) >= 14 and all(real['checks'].values())
    assert real['normal_shutdown'] and real['database_restored'] and real['normal_runtime_unchanged']
    vitals = read(Path(proofs['vitals']))
    assert vitals['passed'] and vitals['checks'] >= 23 and vitals['build_receipt_sha256'] == digest(lab/'native_build.json')
    catalog_rows = {key: row for key, row in (successor_rows or {}).items() if key == str(workspace/'models.json')}
    assert all(predecessor_hash(Path(p),catalog_rows) == sha for p,sha in vitals['source_inputs'].items())
    assert all(real['checks'][k] for k in ['both_players_ordinary','server_ack_druid_twohand',
        'server_ack_druid_standard','server_ack_ranger_ranged','server_ack_ranger_standard',
        'sprint_authorized_server_speed','sprint_off_server_speed','stale_character_cannot_sprint'])
    if verify_sources:
        for proof in [state,gateway,real]:
            assert all(digest(Path(p)) == h for p,h in proof['source_inputs'].items())
    source = Path(__file__).resolve().parents[1]
    plugin = workspace/'Client/Plugins/DAoCVisualBridge'
    candidate = Path(build['project']).parent/'Plugins/DAoCVisualBridge'
    rows = []
    def add(origin,target,before,after):
        if verify_sources:
            assert origin.is_file() and digest(origin) == after,str(origin)
        assert target.resolve().is_relative_to(workspace.resolve())
        rows.append(dict(source=str(origin),target=str(target),before_sha256=before,after_sha256=after))
    for relative in NATIVE_TARGETS:
        if relative.startswith('Source/'):
            key = str(Path(relative.removeprefix('Source/')))
            before,after = old['source_sha256'][key],build['source_sha256'][key]
            origin = source/'UnrealPlugin/DAoCVisualBridge'/relative
        else:
            before,after = old['binaries_sha256'][Path(relative).name],build['binaries_sha256'][Path(relative).name]
            origin = candidate/relative
        add(origin,plugin/relative,before,after)
    prior = {r['target']:r for r in read(workspace/'PersonalTorchLab/installed.json')['files']}
    for name in GODOT_TARGETS:
        origin,target = source/'Godot'/name,workspace/'Godot'/name
        before = prior[str(target)]['after_sha256'] if name!='weapon_sprint_state.gd' else None
        add(origin,target,before,real['source_inputs'][str(origin)])
    assert len(rows) == len({r['target'] for r in rows}) == 8
    return rows


def verify(workspace,successor_rows=None):
    successor_rows = successor_rows or {}
    def current_hash(path):
        replacement = successor_rows.get(str(path))
        if replacement:
            assert digest(path) == replacement['after_sha256']
            return replacement['before_sha256']
        return digest(path)
    lab = workspace/'OriginalControlsLab'
    path = lab/'installed.json'
    data = read(path) if path.exists() else None
    if not data or not data.get('installed'):
        return None,{}
    assert data['phase']=='complete' and not any(data[k] for k in ['database_modified','server_rules_modified','map_geometry_modified','teleport_enabled'])
    predecessor = workspace/'NpcEffectsLab/installed.json'
    assert digest(predecessor) == data['predecessor_receipt_sha256']
    assert read(predecessor)['native_after_sha256'] == data['native_before_sha256']
    assert data['evidence'] and all(digest(Path(p)) == sha for p,sha in data['evidence'].items())
    expected = {r['target']:r for r in expected_files(workspace,data['proofs'],verify_sources=False,successor_rows=successor_rows)}
    rows = {r['target']:r for r in data['files']}
    assert len(rows)==len(data['files'])==len(expected) and rows.keys()==expected.keys()
    for target,row in rows.items():
        assert all(row[k]==expected[target][k] for k in ['source','before_sha256','after_sha256'])
        assert current_hash(Path(target))==row['after_sha256']
    assert data['native_after_sha256']==read(lab/'native_build.json')['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll']
    return data,rows
