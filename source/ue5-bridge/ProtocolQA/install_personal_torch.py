"""Install the verified personal torch candidate with exact scope and reversible backups."""
import argparse,json,shutil,socket
from pathlib import Path
from datetime import datetime
from contextlib import ExitStack
from prepare_combined_expansion_data import digest
from central_activation_receipts import verify_files
from personal_torch_receipts import read,NATIVE_TARGETS,GODOT_TARGETS,expected_before

def latest(folder):
 rows=[p for p in sorted(folder.glob('*/verified.json')) if read(p).get('passed')];assert rows,str(folder);return rows[-1],read(rows[-1])
def install(workspace,apply=False):
 root=workspace/'PersonalTorchLab';baseline=verify_files(workspace)
 if baseline['personal_torch_installed']:return dict(passed=True,already_current=True)
 assert baseline['remote_player_installed'];predecessor=workspace/'RemotePlayerLab/installed.json';old=read(predecessor);bp=root/'native_build.json';build=read(bp);assert build['passed'] and build['normal_binary_sha256']==old['native_after_sha256']
 state=read(root/'state_tests.json');gateway=read(root/'gateway_tests.json');assert state['passed'] and state['checks']>=1502 and gateway['passed']
 for proof in [state,gateway]:assert all(digest(Path(p))==h for p,h in proof['source_inputs'].items())
 native_path,native=latest(root/'NativeRegression');assert native['build_sha256']==digest(bp) and {r['name']:r['checks'] for r in native['reports']}=={'torch':19,'pose':55,'combat':25,'motion':387}
 for row in native['reports']:assert digest(Path(row['report']))==row['sha256'] and read(Path(row['report']))['passed']
 key_path,keys=latest(root/'KeyAcceptance');assert keys['build_receipt_sha256']==digest(bp) and keys['checks']>=258
 render_path,render=latest(root/'VisualAcceptance');assert render['build_sha256']==digest(bp) and render['rendered_private_character'] and all(digest(Path(p))==h for p,h in render['images'].items())
 real_path,real=latest(root/'RealProtocol');assert len(real['checks'])>=23 and all(real['checks'].values()) and real['normal_shutdown'] and real['database_restored'] and real['normal_runtime_unchanged']
 source=Path(__file__).resolve().parents[1];native_source=source/'UnrealPlugin/DAoCVisualBridge';candidate=Path(build['project']).parent/'Plugins/DAoCVisualBridge';plugin=workspace/'Client/Plugins/DAoCVisualBridge'
 assert all(digest(native_source/'Source'/p)==h for p,h in build['source_sha256'].items());prior=read(Path(old['real_protocol_proof']));rows=[]
 def add(origin,target,before):
  assert (digest(target) if target.exists() else None)==before;rows.append(dict(source=str(origin),target=str(target),before_sha256=before,after_sha256=digest(origin)))
 for relative in NATIVE_TARGETS:add((candidate if relative.startswith('Binaries/') else native_source)/relative,plugin/relative,expected_before(workspace,relative))
 for name in GODOT_TARGETS:
  origin=source/'Godot'/name;assert digest(origin)==real['source_inputs'][str(origin)];add(origin,workspace/'Godot'/name,prior['source_inputs'].get(str(origin)))
 evidence=[bp,root/'state_tests.json',root/'gateway_tests.json',native_path,key_path,render_path,real_path]+[Path(r['report']) for r in native['reports']]
 receipt=dict(installed=False,phase='planned',database_modified=False,server_rules_modified=False,map_geometry_modified=False,teleport_enabled=False,owner_gameplay_accepted=False,predecessor_receipt_sha256=digest(predecessor),native_before_sha256=build['normal_binary_sha256'],native_after_sha256=build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll'],real_protocol_proof=str(real_path),files=rows,evidence={str(p):digest(p) for p in evidence});plan=root/'install_plan.json';receipt_path=root/'installed.json'
 if not apply:plan.write_text(json.dumps(receipt,indent=2));return dict(passed=True,dry_run=True,files=len(rows))
 assert read(plan)==receipt;sim=read(root/'install_simulation.json');assert sim['passed'] and sim['simulated_only'] and sim['plan_sha256']==digest(plan) and sim['core_source_sha256']==digest(Path(__file__).with_name('central_activation_receipts.py')) and sim['remote_guard_sha256']==digest(Path(__file__).with_name('personal_torch_receipts.py'))
 with ExitStack() as stack:
  for kind,port in [(socket.SOCK_STREAM,10300),(socket.SOCK_DGRAM,10400),(socket.SOCK_STREAM,19727)]:
   guard=stack.enter_context(socket.socket(socket.AF_INET,kind));guard.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1);guard.bind(('127.0.0.1',port))
   if kind==socket.SOCK_STREAM:guard.listen(1)
  backup=workspace/'Backups'/('PersonalTorchLab_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'));backup.mkdir()
  for i,row in enumerate(rows):
   target=Path(row['target']);assert (digest(target) if target.exists() else None)==row['before_sha256'] and digest(Path(row['source']))==row['after_sha256']
   if target.exists():saved=backup/str(i);shutil.copy2(target,saved);assert digest(saved)==row['before_sha256'];row['backup']=str(saved)
  receipt.update(phase='backed_up',backup_directory=str(backup));receipt_path.write_text(json.dumps(receipt,indent=2));changed=[]
  try:
   for row in rows:
    changed.append(row);shutil.copy2(row['source'],row['target']);assert digest(Path(row['target']))==row['after_sha256']
   receipt.update(installed=True,phase='complete');receipt_path.write_text(json.dumps(receipt,indent=2));assert verify_files(workspace)['personal_torch_installed']
  except BaseException:
   for row in reversed(changed):
    if row.get('backup'):shutil.copy2(row['backup'],row['target'])
    else:Path(row['target']).unlink(missing_ok=True)
   receipt.update(installed=False,phase='rolled_back');receipt_path.write_text(json.dumps(receipt,indent=2));raise
 return dict(passed=True,installed=True,files=len(rows),database_modified=False,backup_directory=str(backup))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--apply',action='store_true');a=p.parse_args();print(json.dumps(install(a.workspace.resolve(),a.apply)))
