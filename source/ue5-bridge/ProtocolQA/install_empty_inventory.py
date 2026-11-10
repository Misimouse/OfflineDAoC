"""Guarded one-file empty inventory initialization install and rollback, without server/DB edits."""
import argparse,json,shutil,socket
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path
from prepare_combined_expansion_data import digest
from central_activation_receipts import verify_files
from empty_inventory_receipts import read,validate

def install(workspace,state,real,apply=False,rollback=False):
    root=workspace/'CharacterInventorySwitchLab';path=root/'installed.json'
    baseline=verify_files(workspace)
    assert baseline['realm_war_keys_installed']
    source=Path(__file__).resolve().parents[1]/'Godot/inventory_state.gd';target=workspace/'Godot/inventory_state.gd'
    native=workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    if rollback:
        data=validate(workspace,read(path));row=data['files'][0];saved=Path(row['backup'])
        assert digest(native)==data['native_sha256']
        assert saved.resolve().is_relative_to((workspace/'Backups').resolve()) and digest(saved)==row['before_sha256']
        if not apply:return dict(passed=True,rollback_preview=True,files=1)
    else:
        if path.exists() and read(path).get('installed'):return dict(passed=True,already_current=True)
        assert state.resolve().is_relative_to(root.resolve()) and real.resolve().is_relative_to(root.resolve())
        data=dict(installed=True,phase='complete',database_modified=False,native_modified=False,server_rules_modified=False,map_modified=False,owner_gameplay_accepted=False,
            predecessor_sha256=digest(workspace/'CrossClassSwitchLab/installed.json'),native_sha256=digest(native),
            proofs=dict(state=str(state),real=str(real)),evidence={str(p):digest(p) for p in [state,real,root/'runtime_baseline.json']},
            files=[dict(source=str(source),target=str(target),before_sha256=digest(target),after_sha256=digest(source))])
        validate(workspace,data,False)
        assert digest(native)==read(root/'runtime_baseline.json')['normal_native_sha256']==data['native_sha256']
        plan=root/'install_plan.json'
        if not apply:
            plan.write_text(json.dumps(data,indent=2));return dict(passed=True,dry_run=True,files=1)
        assert read(plan)==data
        simulation=read(root/'install_simulation.json')
        assert simulation['passed'] and simulation['simulated_only'] and simulation['plan_sha256']==digest(plan)
        assert all(digest(Path(__file__).with_name(name))==sha for name,sha in simulation['guard_sources'].items())
        row=data['files'][0]
    with ExitStack() as stack:
        for kind,port in [(socket.SOCK_STREAM,10300),(socket.SOCK_DGRAM,10400),(socket.SOCK_STREAM,19727)]:
            guard=stack.enter_context(socket.socket(socket.AF_INET,kind));guard.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1);guard.bind(('127.0.0.1',port))
            if kind==socket.SOCK_STREAM:guard.listen(1)
        if rollback:
            current=target.read_bytes();receipt=path.read_bytes()
            try:
                shutil.copy2(saved,target);assert digest(target)==row['before_sha256'];data.update(installed=False,phase='rolled_back');path.write_text(json.dumps(data,indent=2));verify_files(workspace)
            except BaseException:
                target.write_bytes(current);path.write_bytes(receipt);raise
            return dict(passed=True,rolled_back=True)
        assert target.resolve().is_relative_to(workspace.resolve()) and digest(target)==row['before_sha256'] and digest(source)==row['after_sha256']
        backup=workspace/'Backups'/('CharacterInventorySwitch_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'));backup.mkdir();saved=backup/'inventory_state.gd';shutil.copy2(target,saved);assert digest(saved)==row['before_sha256'];row['backup']=str(saved)
        try:
            shutil.copy2(source,target);validate(workspace,data);path.write_text(json.dumps(data,indent=2));assert verify_files(workspace)['empty_inventory_installed']
        except BaseException:
            shutil.copy2(saved,target);data.update(installed=False,phase='rolled_back');path.write_text(json.dumps(data,indent=2));raise
    return dict(passed=True,installed=True,files=1,backup_directory=str(backup))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--state',type=Path);p.add_argument('--real',type=Path);p.add_argument('--apply',action='store_true');p.add_argument('--rollback',action='store_true');a=p.parse_args()
    print(json.dumps(install(a.workspace.resolve(),a.state.resolve() if a.state else None,a.real.resolve() if a.real else None,a.apply,a.rollback)))
