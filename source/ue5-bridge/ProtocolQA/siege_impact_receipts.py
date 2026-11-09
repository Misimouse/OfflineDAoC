"""Exact five-file successor: original siege impacts, without world or rule changes."""
import json
from pathlib import Path
from prepare_combined_expansion_data import digest
NATIVE_TARGETS=['Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll','Binaries/Win64/UnrealEditor.modules','Source/DAoCVisualBridge/Private/DAoCBridgeSpellVisuals.cpp']
GODOT_TARGETS=['live_gateway.gd','spell_visual_state.gd']
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def verify(workspace):
    root=workspace/'SiegeImpactLab';path=root/'installed.json'
    data=read(path) if path.exists() else None
    if not data or not data.get('installed'):return None,{}
    assert data['phase']=='complete' and not any(data[k] for k in ['database_modified','server_rules_modified','map_geometry_modified','teleport_enabled'])
    predecessor=workspace/'SiegeWorldLab/installed.json';old=read(predecessor)
    assert old['installed'] and digest(predecessor)==data['predecessor_receipt_sha256'] and old['native_after_sha256']==data['native_before_sha256']
    assert data['evidence'] and all(digest(Path(p))==h for p,h in data['evidence'].items())
    build_path=root/'native_build.json';build=read(build_path);assert build['passed'] and build['normal_binary_sha256']==data['native_before_sha256'] and data['evidence'][str(build_path)]==digest(build_path)
    previous=read(workspace/'SiegeWorldLab/native_build.json');previous_sources={Path(p).as_posix():h for p,h in previous['source_sha256'].items()};current={Path(p).as_posix():h for p,h in build['source_sha256'].items()}
    plugin=workspace/'Client/Plugins/DAoCVisualBridge';rows={r['target']:r for r in data['files']}
    expected={str(plugin/p) for p in NATIVE_TARGETS}|{str(workspace/'Godot'/p) for p in GODOT_TARGETS}
    assert len(rows)==len(data['files'])==5 and set(rows)==expected
    for rel in NATIVE_TARGETS:
        r=rows[str(plugin/rel)];key=rel.removeprefix('Source/')
        before=previous_sources[key] if rel.startswith('Source/') else previous['binaries_sha256'][Path(rel).name]
        after=current[key] if rel.startswith('Source/') else build['binaries_sha256'][Path(rel).name]
        assert r['before_sha256']==before and r['after_sha256']==after==digest(Path(r['target']))
    real_path=Path(data['real_protocol_proof']);real=read(real_path)
    assert data['evidence'][str(real_path)]==digest(real_path) and real['passed'] and len(real['checks'])>=15 and all(real['checks'].values()) and real['normal_shutdown'] and real['database_restored'] and real['normal_runtime_unchanged']
    prior=read(Path(old['real_protocol_proof']))
    for name in GODOT_TARGETS:
        r=rows[str(workspace/'Godot'/name)];assert r['before_sha256']==prior['source_inputs'][r['source']] and r['after_sha256']==real['source_inputs'][r['source']]==digest(Path(r['target']))
    assert data['native_after_sha256']==build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll']
    return data,rows
