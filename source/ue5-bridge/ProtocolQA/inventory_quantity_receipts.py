"""Exact delivery scope for the inventory quantity successor."""
import json
from pathlib import Path
from prepare_combined_expansion_data import digest

NATIVE_TARGETS=['Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll','Binaries/Win64/UnrealEditor.modules',
    'Source/DAoCVisualBridge/Public/DAoCBridgeSubsystem.h','Source/DAoCVisualBridge/Private/DAoCBridgeSubsystem.cpp',
    'Source/DAoCVisualBridge/Private/DAoCBridgeInventory.cpp','Source/DAoCVisualBridge/Private/DAoCBridgeClassicUI.cpp',
    'Source/DAoCVisualBridge/Private/DAoCBridgeClassicQuantity.inl','Source/DAoCVisualBridge/Private/DAoCBridgeInventoryQuantityAcceptance.cpp']
NEW_NAMES={'DAoCBridgeClassicQuantity.inl','DAoCBridgeInventoryQuantityAcceptance.cpp'}

def latest(rows,row,expected):
    replacement=rows.get(row['target'])
    if replacement:
        assert replacement['before_sha256']==expected
        expected=replacement['after_sha256']
    return expected

def verify(workspace):
    root=workspace/'InventoryQuantityLab';path=root/'installed.json'
    data=json.loads(path.read_text()) if path.exists() else None
    if not data or not data.get('installed'):return None,{}
    assert data['phase']=='complete' and not data['database_modified'] and not data['server_rules_modified']
    predecessor=workspace/'StealthLab/installed.json';old=json.loads(predecessor.read_text())
    assert old['installed'] and data['predecessor_receipt_sha256']==digest(predecessor)
    assert data['native_before_sha256']==old['native_after_sha256']
    assert data['evidence'] and all(digest(Path(p))==h for p,h in data['evidence'].items())
    old_build_path=workspace/'StealthLab/native_build.json';build_path=root/'native_build.json'
    assert old['evidence'][str(old_build_path)]==digest(old_build_path) and data['evidence'][str(build_path)]==digest(build_path)
    previous=json.loads(old_build_path.read_text());build=json.loads(build_path.read_text())
    assert build['passed'] and build['normal_binary_sha256']==data['native_before_sha256']
    previous_sources={Path(p).as_posix():h for p,h in previous['source_sha256'].items()}
    current_sources={Path(p).as_posix():h for p,h in build['source_sha256'].items()}
    plugin=workspace/'Client/Plugins/DAoCVisualBridge';rows={r['target']:r for r in data['files']}
    expected={str(plugin/p) for p in NATIVE_TARGETS}|{str(workspace/'Godot/inventory_state.gd')}
    assert len(rows)==len(data['files'])==len(expected) and set(rows)==expected
    for rel in NATIVE_TARGETS:
        row=rows[str(plugin/rel)];key=rel.removeprefix('Source/').replace('\\','/')
        before=None if Path(rel).name in NEW_NAMES else previous_sources[key] if rel.startswith('Source/') else previous['binaries_sha256'][Path(rel).name]
        after=current_sources[key] if rel.startswith('Source/') else build['binaries_sha256'][Path(rel).name]
        assert row['before_sha256']==before and row['after_sha256']==after and digest(Path(row['target']))==after
    assert data['native_after_sha256']==build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll']
    real_path=Path(data['real_protocol_proof']);real=json.loads(real_path.read_text())
    assert data['evidence'][str(real_path)]==digest(real_path) and real['passed'] and real['normal_shutdown'] and real['database_restored'] and real['normal_runtime_unchanged'] and len(real['checks'])>=25 and all(real['checks'].values())
    before_path=Path(old['godot_after_proof']);before=json.loads(before_path.read_text());assert old['evidence'][str(before_path)]==digest(before_path)
    row=rows[str(workspace/'Godot/inventory_state.gd')]
    assert row['before_sha256']==before['source_inputs'][row['source']]
    assert row['after_sha256']==real['source_inputs'][row['source']]==digest(Path(row['target']))
    art=json.loads((root/'resources.json').read_text());assert data['evidence'][str(root/'resources.json')]==digest(root/'resources.json')
    assert art['passed'] and not art['original_art_modified'] and len(art['files'])==3
    for r in art['files']:
        assert Path(r['target']).resolve().is_relative_to((plugin/'Content/ClassicUI/QuantityUI_v01').resolve()) and digest(Path(r['target']))==r['sha256']
    return data,rows
