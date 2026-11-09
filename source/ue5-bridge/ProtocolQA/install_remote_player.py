"""Install only the verified remote-player bridge successor, with complete rollback."""
import argparse,json,shutil,socket
from pathlib import Path
from datetime import datetime
from contextlib import ExitStack
from prepare_combined_expansion_data import digest
from central_activation_receipts import verify_files
from remote_player_receipts import read,backend_rows,NATIVE_TARGETS,GODOT_TARGETS

def latest(folder):
 matches=[p for p in sorted(folder.glob('*/verified.json')) if read(p).get('passed')];assert matches,str(folder);return matches[-1],read(matches[-1])
def install(workspace,apply=False):
 root=workspace/'RemotePlayerLab';receipt_path=root/'installed.json';baseline=verify_files(workspace)
 if baseline['remote_player_installed']:return dict(passed=True,already_current=True)
 assert baseline['siege_impact_installed'];predecessor=workspace/'SiegeImpactLab/installed.json';old=read(predecessor);bp=root/'native_build.json';build=read(bp);assert build['passed'] and build['normal_binary_sha256']==old['native_after_sha256']
 state=read(root/'state_tests.json');assert state['passed'] and state['checks']>=69 and all(digest(Path(p))==h for p,h in state['source_inputs'].items())
 pose_path,pose=latest(root/'NativeAcceptance');assert pose['checks']>=55 and pose['build_sha256']==digest(bp)
 regression_path,regression=latest(root/'Regression');assert regression['build_sha256']==digest(bp) and len(regression['reports'])==2
 for row in regression['reports']:assert digest(Path(row['path']))==row['sha256'] and read(Path(row['path']))['passed']
 assert {row['name']:row['checks'] for row in regression['reports']}=={'combat':25,'motion':387}
 real_path,real=latest(root/'RealProtocol');assert len(real['checks'])>=18 and all(real['checks'].values()) and real['normal_shutdown'] and real['database_restored'] and real['normal_runtime_unchanged']
 backend,network=backend_rows(workspace);backend_path=root/'backend_verified.json';assert real['source_inputs'][str(backend_path)]==digest(backend_path)
 source=Path(__file__).resolve().parents[1];native_source=source/'UnrealPlugin/DAoCVisualBridge';candidate=Path(build['project']).parent/'Plugins/DAoCVisualBridge';plugin=workspace/'Client/Plugins/DAoCVisualBridge';assert all(digest(native_source/'Source'/p)==h for p,h in build['source_sha256'].items())
 previous=read(workspace/'SiegeImpactLab/native_build.json');old_sources={Path(p).as_posix():h for p,h in previous['source_sha256'].items()};before_proof=read(Path(old['real_protocol_proof']));rows=[]
 def add(origin,target,expected):
  assert digest(target)==expected;rows.append(dict(source=str(origin),target=str(target),before_sha256=expected,after_sha256=digest(origin)))
 for rel in NATIVE_TARGETS:
  target=plugin/rel;origin=(candidate if rel.startswith('Binaries/') else native_source)/rel;expected=old_sources[rel.removeprefix('Source/')] if rel.startswith('Source/') else previous['binaries_sha256'][target.name];add(origin,target,expected)
 for name in GODOT_TARGETS:
  origin=source/'Godot'/name;assert digest(origin)==real['source_inputs'][str(origin)];add(origin,workspace/'Godot'/name,before_proof['source_inputs'][str(origin)])
 for row in network.values():add(Path(row['source']),Path(row['target']),row['before_sha256'])
 evidence=[bp,root/'state_tests.json',pose_path,regression_path,real_path,backend_path]+[Path(row['path']) for row in regression['reports']]
 receipt=dict(installed=False,phase='planned',database_modified=False,server_rules_modified=False,map_geometry_modified=False,teleport_enabled=False,owner_gameplay_accepted=False,predecessor_receipt_sha256=digest(predecessor),native_before_sha256=build['normal_binary_sha256'],native_after_sha256=build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll'],real_protocol_proof=str(real_path),files=rows,evidence={str(p):digest(p) for p in evidence});plan=root/'install_plan.json'
 if not apply:plan.write_text(json.dumps(receipt,indent=2));return dict(passed=True,dry_run=True,files=len(rows))
 assert read(plan)==receipt
 sim=read(root/'install_simulation.json');assert sim['passed'] and sim['simulated_only'] and sim['plan_sha256']==digest(plan) and sim['core_source_sha256']==digest(Path(__file__).with_name('central_activation_receipts.py')) and sim['remote_guard_sha256']==digest(Path(__file__).with_name('remote_player_receipts.py'))
 with ExitStack() as stack:
  for kind,port in [(socket.SOCK_STREAM,10300),(socket.SOCK_DGRAM,10400),(socket.SOCK_STREAM,19727)]:
   guard=stack.enter_context(socket.socket(socket.AF_INET,kind));guard.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1);guard.bind(('127.0.0.1',port))
   if kind==socket.SOCK_STREAM:guard.listen(1)
  backup=workspace/'Backups'/('RemotePlayerLab_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'));backup.mkdir()
  for i,row in enumerate(rows):
   target=Path(row['target']);assert digest(target)==row['before_sha256'] and digest(Path(row['source']))==row['after_sha256'];saved=backup/str(i);shutil.copy2(target,saved);assert digest(saved)==row['before_sha256'];row['backup']=str(saved)
  receipt.update(phase='backed_up',backup_directory=str(backup));receipt_path.write_text(json.dumps(receipt,indent=2));changed=[]
  try:
   for row in rows:
    changed.append(row);shutil.copy2(row['source'],row['target']);assert digest(Path(row['target']))==row['after_sha256']
   receipt.update(installed=True,phase='complete');receipt_path.write_text(json.dumps(receipt,indent=2));assert verify_files(workspace)['remote_player_installed']
  except BaseException:
   for row in reversed(changed):shutil.copy2(row['backup'],row['target'])
   receipt.update(installed=False,phase='rolled_back');receipt_path.write_text(json.dumps(receipt,indent=2));raise
 return dict(passed=True,installed=True,files=len(rows),database_modified=False,backup_directory=str(backup))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--apply',action='store_true');a=p.parse_args();print(json.dumps(install(a.workspace.resolve(),a.apply)))
