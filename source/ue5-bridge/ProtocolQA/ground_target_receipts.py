"""Exact scope of the original ground target, physical marker and independent visibility delivery."""
import json
from pathlib import Path
from prepare_combined_expansion_data import digest
from inventory_quantity_receipts import latest

NATIVE_TARGETS=['Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll','Binaries/Win64/UnrealEditor.modules',
    'Source/DAoCVisualBridge/Public/DAoCBridgeSubsystem.h','Source/DAoCVisualBridge/Private/DAoCBridgeSubsystem.cpp',
    'Source/DAoCVisualBridge/Private/DAoCBridgeClassicUI.cpp','Source/DAoCVisualBridge/Private/DAoCBridgeKeyConfiguration.cpp','Source/DAoCVisualBridge/Private/DAoCBridgeKeyConfigurationAcceptance.cpp',
    'Source/DAoCVisualBridge/Private/DAoCBridgeGroundTarget.cpp','Source/DAoCVisualBridge/Private/DAoCBridgeGroundTargetAcceptance.cpp']
GODOT_TARGETS=['live_gateway.gd','visual_bridge.gd','ground_target_state.gd']
NEW_NAMES={'DAoCBridgeGroundTarget.cpp','DAoCBridgeGroundTargetAcceptance.cpp','ground_target_state.gd'}

def backend_plan(workspace):
    path=workspace/'GroundTargetLab/backend_verified.json';data=json.loads(path.read_text())
    assert data['passed'] and data['checks']>=8 and not data['normal_runtime_modified']
    install=Path(data['install_root']).resolve()
    # Explicit original client root, never an arbitrary path from a receipt.
    original_sources=[Path(p) for p in data['source_inputs'] if p.replace('\\','/').endswith('/game/world_host/BotSim.cs')]
    assert len(original_sources)==1 and original_sources[0].resolve()==install/'new-client/godot/game/world_host/BotSim.cs'
    normal=install/'new-client/godot';runtime=normal/'.godot/mono/temp/bin/Debug'
    expected={str(runtime/'MMOEngine.dll'),str(runtime/'MMOEngine.pdb'),str(normal/'game/net/DaocClient.cs')}
    rows={r['target']:r for r in data['backend_files']}
    assert len(rows)==3 and set(rows)==expected
    assert all(digest(Path(p))==h for p,h in data['source_inputs'].items())
    for r in rows.values():
        assert digest(Path(r['source']))==r['after_sha256'] and r['before_sha256'] and r['after_sha256']
    assert rows[str(runtime/'MMOEngine.dll')]['after_sha256']==data['candidate_binary_sha256']
    return data,rows

def verify(workspace):
    root=workspace/'GroundTargetLab';path=root/'installed.json'
    data=json.loads(path.read_text()) if path.exists() else None
    if not data or not data.get('installed'):return None,{}
    assert data['phase']=='complete' and not data['database_modified'] and not data['server_rules_modified'] and not data['map_geometry_modified'] and not data['teleport_enabled']
    predecessor=workspace/'SiegeWindowLab/installed.json';old=json.loads(predecessor.read_text())
    assert old['installed'] and data['predecessor_receipt_sha256']==digest(predecessor) and data['native_before_sha256']==old['native_after_sha256']
    assert data['evidence'] and all(digest(Path(p))==h for p,h in data['evidence'].items())
    old_build_path=workspace/'SiegeWindowLab/native_build.json';build_path=root/'native_build.json'
    assert old['evidence'][str(old_build_path)]==digest(old_build_path) and data['evidence'][str(build_path)]==digest(build_path)
    previous=json.loads(old_build_path.read_text());build=json.loads(build_path.read_text());assert build['passed'] and build['normal_binary_sha256']==data['native_before_sha256']
    previous_sources={Path(p).as_posix():h for p,h in previous['source_sha256'].items()};current_sources={Path(p).as_posix():h for p,h in build['source_sha256'].items()}
    plugin=workspace/'Client/Plugins/DAoCVisualBridge';rows={r['target']:r for r in data['files']}
    backend,backend_rows=backend_plan(workspace)
    backend_path=root/'backend_verified.json';assert data['evidence'][str(backend_path)]==digest(backend_path)
    expected={str(plugin/p) for p in NATIVE_TARGETS}|{str(workspace/'Godot'/p) for p in GODOT_TARGETS}|set(backend_rows)
    for target,r in backend_rows.items():
        row=rows[target];assert row['before_sha256']==r['before_sha256'] and row['after_sha256']==r['after_sha256']==digest(Path(target))
    assert len(rows)==len(data['files'])==len(expected) and set(rows)==expected
    for rel in NATIVE_TARGETS:
        row=rows[str(plugin/rel)];key=rel.removeprefix('Source/').replace('\\','/')
        before=None if Path(rel).name in NEW_NAMES else previous_sources[key] if rel.startswith('Source/') else previous['binaries_sha256'][Path(rel).name]
        after=current_sources[key] if rel.startswith('Source/') else build['binaries_sha256'][Path(rel).name]
        assert row['before_sha256']==before and row['after_sha256']==after and digest(Path(row['target']))==after
    assert data['native_after_sha256']==build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll']
    real_path=Path(data['real_protocol_proof']);real=json.loads(real_path.read_text())
    assert data['evidence'][str(real_path)]==digest(real_path) and real['passed'] and real['normal_shutdown'] and real['database_restored'] and real['normal_runtime_unchanged'] and len(real['checks'])>=21 and all(real['checks'].values())
    assert real['source_inputs'][str(backend_path)]==digest(backend_path) and real['checks']['candidate_network_backend_loaded'] and real['checks']['godot_public_network_sight_binding']
    before_path=Path(old['real_protocol_proof']);before=json.loads(before_path.read_text());assert old['evidence'][str(before_path)]==digest(before_path)
    for name in GODOT_TARGETS:
        row=rows[str(workspace/'Godot'/name)];expected_before=None if name in NEW_NAMES else before['source_inputs'][row['source']]
        assert row['before_sha256']==expected_before and row['after_sha256']==real['source_inputs'][row['source']]==digest(Path(row['target']))
    art_path=root/'resources.json';art=json.loads(art_path.read_text());assert data['evidence'][str(art_path)]==digest(art_path)
    assert art['passed'] and not art['original_art_modified'] and not art['world_map_modified'] and len(art['files'])==2
    assert all(digest(Path(p))==h for p,h in art['source_inputs'].items())
    for r in art['files']:assert digest(Path(r['target']))==r['sha256']
    return data,rows
