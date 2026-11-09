"""Exact additive original siege body library and authoritative animation successor."""
import json
from pathlib import Path
from prepare_combined_expansion_data import digest
NATIVE_TARGETS=['Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll','Binaries/Win64/UnrealEditor.modules','Source/DAoCVisualBridge/Public/DAoCBridgeSubsystem.h','Source/DAoCVisualBridge/Private/DAoCBridgeSubsystem.cpp','Source/DAoCVisualBridge/Private/DAoCBridgeAnimation.cpp','Source/DAoCVisualBridge/Private/DAoCBridgeSiegeWorldAcceptance.cpp']
GODOT_TARGETS=['live_gateway.gd','siege_visual_state.gd']
NEW_NAMES={'DAoCBridgeSiegeWorldAcceptance.cpp','siege_visual_state.gd'}
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def asset_rows(workspace):
 root=workspace/'SiegeWorldLab';proof=read(root/'asset_import.json');assert proof['passed'] and not proof['normal_content_modified'] and not proof['normal_catalogue_modified'] and len(proof['models'])==10
 private=root/'AssetHost/Plugins/DAoCVisualBridge/Content/SiegeWorld_v01';normal=workspace/'Client/Plugins/DAoCVisualBridge/Content/SiegeWorld_v01'
 assert private.resolve().is_relative_to(root.resolve()) and not private.is_junction()
 out=[]
 for p,h in proof['files'].items():
  source=Path(p);assert source.resolve().is_relative_to(private.resolve()) and source.suffix=='.uasset' and digest(source)==h
  out.append(dict(source=str(source),target=str(normal/source.relative_to(private)),before_sha256=None,after_sha256=h))
 assert len(out)==100 and len({r['target'] for r in out})==100
 return proof,out

def verify(workspace):
 root=workspace/'SiegeWorldLab';path=root/'installed.json';data=read(path) if path.exists() else None
 if not data or not data.get('installed'):return None,{}
 assert data['phase']=='complete' and not data['database_modified'] and not data['server_rules_modified'] and not data['map_geometry_modified'] and not data['teleport_enabled']
 old_path=workspace/'GroundTargetLab/installed.json';old=read(old_path);assert old['installed'] and digest(old_path)==data['predecessor_receipt_sha256'] and old['native_after_sha256']==data['native_before_sha256']
 assert all(digest(Path(p))==h for p,h in data['evidence'].items())
 build_path=root/'native_build.json';build=read(build_path);assert build['passed'] and build['normal_binary_sha256']==data['native_before_sha256'] and data['evidence'][str(build_path)]==digest(build_path)
 before=read(workspace/'GroundTargetLab/native_build.json');previous={Path(p).as_posix():h for p,h in before['source_sha256'].items()};current={Path(p).as_posix():h for p,h in build['source_sha256'].items()}
 rows={r['target']:r for r in data['files']};plugin=workspace/'Client/Plugins/DAoCVisualBridge';assets,added=asset_rows(workspace)
 expected={str(plugin/p) for p in NATIVE_TARGETS}|{str(workspace/'Godot'/p) for p in GODOT_TARGETS}|{str(workspace/'models.json')}|{r['target'] for r in added}
 assert len(rows)==len(data['files'])==len(expected) and set(rows)==expected
 for rel in NATIVE_TARGETS:
  row=rows[str(plugin/rel)];key=rel.removeprefix('Source/').replace('\\','/')
  expected_before=None if Path(rel).name in NEW_NAMES else previous[key] if rel.startswith('Source/') else before['binaries_sha256'][Path(rel).name]
  expected_after=current[key] if rel.startswith('Source/') else build['binaries_sha256'][Path(rel).name]
  assert row['before_sha256']==expected_before and row['after_sha256']==expected_after==digest(Path(row['target']))
 assert data['native_after_sha256']==build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll']
 real_path=Path(data['real_protocol_proof']);real=read(real_path);assert data['evidence'][str(real_path)]==digest(real_path) and real['passed'] and len(real['checks'])>=24 and all(real['checks'].values()) and real['normal_shutdown'] and real['database_restored'] and real['normal_runtime_unchanged']
 prior=read(Path(old['real_protocol_proof']))
 for name in GODOT_TARGETS:
  row=rows[str(workspace/'Godot'/name)];assert row['before_sha256']==(None if name in NEW_NAMES else prior['source_inputs'][row['source']]) and row['after_sha256']==real['source_inputs'][row['source']]==digest(Path(row['target']))
 for added_row in added:
  row=rows[added_row['target']];assert row['before_sha256'] is None and row['after_sha256']==added_row['after_sha256']==digest(Path(row['target']))
 original_path=root/'catalogue_before.json';candidate_path=root/'models_candidate.json';original=read(original_path);candidate=read(candidate_path);additions={k:r['entry'] for k,r in assets['models'].items()}
 assert not(set(original)&set(additions)) and candidate==dict(original,**additions)
 row=rows[str(workspace/'models.json')];assert row['before_sha256']==digest(original_path) and row['after_sha256']==digest(candidate_path)==real['source_inputs'][str(candidate_path)]==digest(Path(row['target']))
 return data,rows
