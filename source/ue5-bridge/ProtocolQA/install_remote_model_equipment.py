"""Install only the verified native remote equipment successor, with rollback."""
import argparse,json,shutil,socket
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path
from central_activation_receipts import verify_files
from prepare_combined_expansion_data import digest
from remote_model_equipment_receipts import inventory,read,validate

def install(workspace,red,candidate,regression,apply=False):
    baseline=verify_files(workspace);assert baseline['remote_model_size_installed']
    root=workspace/'RemoteModelEquipmentLab';path=root/'installed.json'
    if path.exists() and read(path).get('installed'):
        validate(workspace,read(path));return dict(passed=True,already_current=True)
    proofs=dict(red=str(red),candidate=str(candidate),regression=str(regression));build=read(root/'native_build.json')
    evidence=[red,candidate,regression,root/'native_build.json']
    data=dict(installed=True,phase='complete',database_modified=False,server_rules_modified=False,map_modified=False,art_modified=False,owner_gameplay_accepted=False,
        predecessor_sha256=digest(workspace/'RemoteModelRoundtripLab/installed.json'),native_before_sha256=build['normal_binary_sha256'],native_after_sha256=build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll'],
        proofs=proofs,evidence={str(p):digest(p) for p in evidence},files=[dict(source=str(s),target=str(t),before_sha256=digest(t),after_sha256=digest(s)) for s,t in inventory(workspace)])
    validate(workspace,data,False);plan=root/'install_plan.json'
    if not apply:
        plan.write_text(json.dumps(data,indent=2));return dict(passed=True,dry_run=True,files=3)
    assert read(plan)==data
    backup=workspace/'Backups'/('RemoteModelEquipment_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'));saved=[]
    previous=path.read_bytes() if path.exists() else None
    with ExitStack() as stack:
        for kind,port in [(socket.SOCK_STREAM,10300),(socket.SOCK_DGRAM,10400),(socket.SOCK_STREAM,19727)]:
            guard=stack.enter_context(socket.socket(socket.AF_INET,kind));guard.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1);guard.bind(('127.0.0.1',port))
            if kind==socket.SOCK_STREAM:guard.listen(1)
        for row in data['files']:
            assert Path(row['target']).resolve().is_relative_to((workspace/'Client/Plugins/DAoCVisualBridge').resolve())
            assert digest(Path(row['target']))==row['before_sha256'] and digest(Path(row['source']))==row['after_sha256']
        backup.mkdir()
        for i,row in enumerate(data['files']):
            target=Path(row['target']);copy=backup/(str(i)+'_'+target.name);shutil.copy2(target,copy);assert digest(copy)==row['before_sha256'];row['backup']=str(copy);saved.append((target,copy))
        try:
            for row in data['files']:shutil.copy2(row['source'],row['target'])
            validate(workspace,data);path.write_text(json.dumps(data,indent=2));assert verify_files(workspace)['remote_model_equipment_installed']
        except BaseException:
            for target,copy in saved:shutil.copy2(copy,target)
            if previous is None:path.unlink(missing_ok=True)
            else:path.write_bytes(previous)
            raise
    return dict(passed=True,installed=True,files=3,backup_directory=str(backup))
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ['workspace','red','candidate','regression']:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--apply',action='store_true');a=p.parse_args();print(json.dumps(install(a.workspace.resolve(),a.red.resolve(),a.candidate.resolve(),a.regression.resolve(),a.apply)))
