"""Bounded original rigid ground-object delivery; no server, database or authored-map edits."""
from pathlib import Path
from npc_ghost_receipts import read
from prepare_combined_expansion_data import digest

NATIVE_SOURCES=['DAoCVisualBridge.Build.cs','Public/DAoCBridgeSubsystem.h']+['Private/'+n for n in [
    'DAoCBridgeClassicUI.cpp','DAoCBridgeGroundObjectFrameAcceptance.cpp','DAoCBridgeGroundObjectKeysAcceptance.inl',
    'DAoCBridgeGroundObjectRuntimeAcceptance.cpp','DAoCBridgeGroundObjects.cpp','DAoCBridgeInteraction.cpp',
    'DAoCBridgeKeyConfiguration.cpp','DAoCBridgeKeyConfigurationAcceptance.cpp','DAoCBridgeNameplates.cpp','DAoCBridgeSubsystem.cpp']]
GODOT=['decoded_world_adapter.gd','ground_object_state.gd','live_gateway.gd','visual_bridge.gd']

def inventory(workspace):
    lab=workspace/'GroundObjectRuntimeLab';build=read(lab/'native_build.json');plugin=workspace/'Client/Plugins/DAoCVisualBridge'
    source=Path(__file__).resolve().parents[1];candidate=Path(build['project']).parent/'Plugins/DAoCVisualBridge';rows=[]
    for name in ['UnrealEditor-DAoCVisualBridge.dll','UnrealEditor.modules']:
        rows.append((candidate/'Binaries/Win64'/name,plugin/'Binaries/Win64'/name,build['binaries_sha256'][name]))
    for relative in NATIVE_SOURCES:
        key=str(Path('DAoCVisualBridge')/relative);rows.append((source/'UnrealPlugin/DAoCVisualBridge/Source'/key,plugin/'Source'/key,build['source_sha256'][key]))
    for name in GODOT:
        origin=source/'Godot'/name;rows.append((origin,workspace/'Godot'/name,read(lab/'gateway_tests.json')['source_inputs'][str(origin)]))
    catalog=workspace/'GroundObjectsLab/world_catalog_candidate.json';rows.append((catalog,plugin/'Content/WorldObjects_v01/world_catalog.json',read(workspace/'GroundObjectsLab/catalogue_verified.json')['sha256']))
    assert len(rows)==19 and len({str(r[1]) for r in rows})==19
    return rows

def expected_files(workspace,proofs,verify_sources=True):
    lab=workspace/'GroundObjectRuntimeLab';build=read(lab/'native_build.json');base=read(lab/'runtime_baseline.json')
    old=read(workspace/'GroupTargetKeysLab/installed.json');assert build['passed'] and build['normal_binary_sha256']==old['native_after_sha256']==base['normal_binary_sha256']
    state,gateway,native,keys,render,real,geometry=[read(Path(proofs[k])) for k in ['state','gateway','native','keys','render','real','geometry']]
    assert state['passed'] and state['checks']>=68 and state['original_get_object_executed']
    assert gateway['passed'] and {r['test']:r['checks'] for r in gateway['reports']}=={'test_ground_object_gateway.gd':15,'test_weapon_sprint_gateway.gd':8,'test_personal_torch_gateway.gd':261,'test_live_riding_gateway.gd':8,'test_remote_player_state.gd':69}
    assert native['passed'] and native['checks']>=22 and not native['failures']
    assert keys['passed'] and keys['checks']>=415 and not keys['failures']
    assert render['passed'] and render['captures']==2 and render['actual_runtime_bodies'] and not render['failures']
    assert all(p['build_receipt_sha256']==digest(lab/'native_build.json') for p in [native,keys,render])
    assert real['passed'] and len(real['checks'])>=12 and all(real['checks'].values()) and real['normal_shutdown'] and real['database_restored'] and real['normal_runtime_unchanged']
    assert geometry['passed'] and geometry['assets']==918 and geometry['models']==1021 and geometry['vertices']==293417 and geometry['max_bounds_error_cm']<.02
    if verify_sources:
        for proof in [state,gateway,real]:assert all(digest(Path(p))==h for p,h in proof['source_inputs'].items())
        source=Path(__file__).resolve().parents[1]/'UnrealPlugin/DAoCVisualBridge/Source';assert all(digest(source/p)==h for p,h in build['source_sha256'].items())
    rows=[]
    for origin,target,after in inventory(workspace):
        assert target.resolve().is_relative_to(workspace.resolve())
        if verify_sources:assert origin.is_file() and digest(origin)==after,str(origin)
        rows.append(dict(source=str(origin),target=str(target),before_sha256=base['files'][str(target)],after_sha256=after))
    assert {r['target'] for r in rows}==set(base['files'])
    return rows

def verify(workspace,successor_rows=None):
    successor_rows=successor_rows or {}
    def current_hash(path):
        replacement=successor_rows.get(str(path))
        if replacement:
            assert digest(path)==replacement["after_sha256"]
            return replacement["before_sha256"]
        return digest(path)
    lab=workspace/'GroundObjectRuntimeLab';path=lab/'installed.json';data=read(path) if path.exists() else None
    if not data or not data.get('installed'):return None,{}
    assert data['phase']=='complete' and not any(data[k] for k in ['database_modified','server_rules_modified','map_geometry_modified','teleport_enabled'])
    predecessor=workspace/'GroupTargetKeysLab/installed.json';assert digest(predecessor)==data['predecessor_receipt_sha256'] and read(predecessor)['native_after_sha256']==data['native_before_sha256']
    assert data['evidence'] and all(digest(Path(p))==h for p,h in data['evidence'].items())
    expected={r['target']:r for r in expected_files(workspace,data['proofs'],False)};rows={r['target']:r for r in data['files']}
    assert len(rows)==len(data['files'])==19 and rows.keys()==expected.keys()
    for target,row in rows.items():
        assert all(row[k]==expected[target][k] for k in ['source','before_sha256','after_sha256'])
        assert current_hash(Path(target))==row['after_sha256']
    assert data['native_after_sha256']==read(lab/'native_build.json')['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll']
    return data,rows
