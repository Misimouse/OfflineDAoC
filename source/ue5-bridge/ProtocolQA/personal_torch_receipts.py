"""Exact personal-light successor, preserving original protocol and the prior delivery chain."""
import json
from pathlib import Path
from prepare_combined_expansion_data import digest
NATIVE_TARGETS=['Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll','Binaries/Win64/UnrealEditor.modules','Source/DAoCVisualBridge/Public/DAoCBridgeSubsystem.h']+['Source/DAoCVisualBridge/Private/'+n for n in ['DAoCBridgeSubsystem.cpp','DAoCBridgeKeyConfiguration.cpp','DAoCBridgeKeyConfigurationAcceptance.cpp','DAoCBridgePersonalTorch.cpp','DAoCBridgePersonalTorchAcceptance.cpp','DAoCBridgePersonalTorchVisual.cpp']]
GODOT_TARGETS=['live_gateway.gd','visual_bridge.gd','personal_torch_state.gd']
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def expected_before(workspace,relative):
 old=read(workspace/'RemotePlayerLab/native_build.json');key=relative.removeprefix('Source/');return old['source_sha256'].get(str(Path(key))) if relative.startswith('Source/') else old['binaries_sha256'][Path(relative).name]
def verify(workspace):
 root=workspace/'PersonalTorchLab';path=root/'installed.json';data=read(path) if path.exists() else None
 if not data or not data.get('installed'):return None,{}
 assert data['phase']=='complete' and not any(data[k] for k in ['database_modified','server_rules_modified','map_geometry_modified','teleport_enabled'])
 predecessor=workspace/'RemotePlayerLab/installed.json';old=read(predecessor);assert old['installed'] and digest(predecessor)==data['predecessor_receipt_sha256'] and old['native_after_sha256']==data['native_before_sha256']
 assert data['evidence'] and all(digest(Path(p))==h for p,h in data['evidence'].items())
 bp=root/'native_build.json';build=read(bp);assert build['passed'] and build['normal_binary_sha256']==data['native_before_sha256'] and data['evidence'][str(bp)]==digest(bp)
 plugin=workspace/'Client/Plugins/DAoCVisualBridge';rows={r['target']:r for r in data['files']};expected={str(plugin/p) for p in NATIVE_TARGETS}|{str(workspace/'Godot'/p) for p in GODOT_TARGETS};assert len(rows)==len(data['files'])==len(expected) and set(rows)==expected
 for relative in NATIVE_TARGETS:
  row=rows[str(plugin/relative)];after=build['source_sha256'][str(Path(relative.removeprefix('Source/')))] if relative.startswith('Source/') else build['binaries_sha256'][Path(relative).name];assert row['before_sha256']==expected_before(workspace,relative) and row['after_sha256']==after==digest(Path(row['target']))
 real=read(Path(data['real_protocol_proof']));assert real['passed'] and len(real['checks'])>=23 and all(real['checks'].values()) and real['normal_shutdown'] and real['database_restored'] and real['normal_runtime_unchanged']
 prior=read(Path(old['real_protocol_proof']))
 for name in GODOT_TARGETS:
  row=rows[str(workspace/'Godot'/name)];assert row['before_sha256']==prior['source_inputs'].get(row['source']) and row['after_sha256']==real['source_inputs'][row['source']]==digest(Path(row['target']))
 assert data['native_after_sha256']==build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll'];return data,rows
