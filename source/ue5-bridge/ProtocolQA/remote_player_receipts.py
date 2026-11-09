"""Exact remote-player delivery and original-network successor checks."""
import json
from pathlib import Path
from prepare_combined_expansion_data import digest
NATIVE_TARGETS=['Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll','Binaries/Win64/UnrealEditor.modules']+['Source/DAoCVisualBridge/Private/'+name for name in ['DAoCBridgeAnimation.cpp','DAoCBridgeRemoteMotion.cpp','DAoCBridgePoseAcceptance.cpp']]
GODOT_TARGETS=['live_gateway.gd','decoded_world_adapter.gd']
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def backend_rows(workspace):
 path=workspace/'RemotePlayerLab/backend_verified.json';data=read(path);assert data['passed'] and data['checks']>=73 and not data['normal_runtime_modified']
 assert all(digest(Path(p))==h for p,h in data['source_inputs'].items())
 from ground_target_receipts import backend_plan
 old,previous=backend_plan(workspace);normal=Path(old['install_root'])/'new-client/godot';runtime=normal/'.godot/mono/temp/bin/Debug'
 expected={str(runtime/'MMOEngine.dll'),str(runtime/'MMOEngine.pdb'),str(normal/'game/net/DaocClient.cs')};rows={r['target']:r for r in data['backend_files']};assert len(rows)==3 and set(rows)==expected
 for target,row in rows.items():assert row['before_sha256']==previous[target]['after_sha256'] and digest(Path(row['source']))==row['after_sha256']
 assert data['candidate_binary_sha256']==rows[str(runtime/'MMOEngine.dll')]['after_sha256'];return data,rows

def verify(workspace):
 root=workspace/'RemotePlayerLab';path=root/'installed.json';data=read(path) if path.exists() else None
 if not data or not data.get('installed'):return None,{}
 assert data['phase']=='complete' and not any(data[k] for k in ['database_modified','server_rules_modified','map_geometry_modified','teleport_enabled'])
 old_path=workspace/'SiegeImpactLab/installed.json';old=read(old_path);assert old['installed'] and digest(old_path)==data['predecessor_receipt_sha256'] and old['native_after_sha256']==data['native_before_sha256']
 assert data['evidence'] and all(digest(Path(p))==h for p,h in data['evidence'].items())
 bp=root/'native_build.json';build=read(bp);assert build['passed'] and build['normal_binary_sha256']==data['native_before_sha256'] and data['evidence'][str(bp)]==digest(bp)
 previous=read(workspace/'SiegeImpactLab/native_build.json');before_sources={Path(p).as_posix():h for p,h in previous['source_sha256'].items()};current={Path(p).as_posix():h for p,h in build['source_sha256'].items()}
 plugin=workspace/'Client/Plugins/DAoCVisualBridge';backend,network=backend_rows(workspace);rows={r['target']:r for r in data['files']}
 expected={str(plugin/p) for p in NATIVE_TARGETS}|{str(workspace/'Godot'/p) for p in GODOT_TARGETS}|set(network);assert len(rows)==len(data['files'])==len(expected) and set(rows)==expected
 for rel in NATIVE_TARGETS:
  row=rows[str(plugin/rel)];key=rel.removeprefix('Source/');before=before_sources[key] if rel.startswith('Source/') else previous['binaries_sha256'][Path(rel).name];after=current[key] if rel.startswith('Source/') else build['binaries_sha256'][Path(rel).name]
  assert row['before_sha256']==before and row['after_sha256']==after==digest(Path(row['target']))
 real_path=Path(data['real_protocol_proof']);real=read(real_path);assert data['evidence'][str(real_path)]==digest(real_path) and real['passed'] and len(real['checks'])>=18 and all(real['checks'].values()) and real['normal_shutdown'] and real['database_restored'] and real['normal_runtime_unchanged']
 assert real['source_inputs'][str(root/'backend_verified.json')]==digest(root/'backend_verified.json')
 prior=read(Path(old['real_protocol_proof']))
 for name in GODOT_TARGETS:
  row=rows[str(workspace/'Godot'/name)];assert row['before_sha256']==prior['source_inputs'][row['source']] and row['after_sha256']==real['source_inputs'][row['source']]==digest(Path(row['target']))
 for target,row in network.items():assert rows[target]['before_sha256']==row['before_sha256'] and rows[target]['after_sha256']==row['after_sha256']==digest(Path(target))
 assert data['native_after_sha256']==build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll'];return data,rows
