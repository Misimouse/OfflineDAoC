"""Guarded single adapter replacement; private proofs, exact plan and automatic rollback."""
import argparse,json,shutil,socket
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path
from prepare_combined_expansion_data import digest
from central_activation_receipts import verify_files
from remote_model_size_receipts import read,validate

def install(workspace,red,state,apply=False):
    baseline=verify_files(workspace);assert baseline['empty_inventory_installed']
    root=workspace/'RemoteModelRoundtripLab';receipt=root/'installed.json'
    if receipt.exists() and read(receipt).get('installed'):
        validate(workspace,read(receipt));return dict(passed=True,already_current=True)
    source=Path(__file__).resolve().parents[1]/'Godot/decoded_world_adapter.gd';target=workspace/'Godot/decoded_world_adapter.gd'
    predecessor=workspace/'CharacterInventorySwitchLab/installed.json'
    data=dict(installed=True,phase='complete',database_modified=False,native_modified=False,server_rules_modified=False,map_modified=False,owner_gameplay_accepted=False,
        predecessor_sha256=digest(predecessor),native_sha256=read(predecessor)['native_sha256'],red_proof=str(red),state_proof=str(state),evidence={str(p):digest(p) for p in [red,state]},
        files=[dict(source=str(source),target=str(target),before_sha256=digest(target),after_sha256=digest(source))])
    validate(workspace,data,False);plan=root/'install_plan.json'
    if not apply:
        plan.write_text(json.dumps(data,indent=2));return dict(passed=True,dry_run=True,files=1)
    assert read(plan)==data
    with ExitStack() as stack:
        for kind,port in [(socket.SOCK_STREAM,10300),(socket.SOCK_DGRAM,10400),(socket.SOCK_STREAM,19727)]:
            guard=stack.enter_context(socket.socket(socket.AF_INET,kind));guard.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1);guard.bind(('127.0.0.1',port))
            if kind==socket.SOCK_STREAM:guard.listen(1)
        row=data['files'][0]
        assert digest(target)==row['before_sha256'] and digest(source)==row['after_sha256']
        backup=workspace/'Backups'/('RemoteModelSize_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'));backup.mkdir()
        saved=backup/target.name;shutil.copy2(target,saved);assert digest(saved)==row['before_sha256'];row['backup']=str(saved)
        previous=receipt.read_bytes() if receipt.exists() else None
        try:
            shutil.copy2(source,target);validate(workspace,data);receipt.write_text(json.dumps(data,indent=2))
            assert verify_files(workspace)['remote_model_size_installed']
        except BaseException:
            shutil.copy2(saved,target)
            if previous is None:receipt.unlink(missing_ok=True)
            else:receipt.write_bytes(previous)
            raise
    return dict(passed=True,installed=True,files=1,backup_directory=str(backup))
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ['workspace','red','state']:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--apply',action='store_true');a=p.parse_args()
    print(json.dumps(install(a.workspace.resolve(),a.red.resolve(),a.state.resolve(),a.apply)))
