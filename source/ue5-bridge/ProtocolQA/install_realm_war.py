"""Guarded, reversible delivery of the verified read-only original realm-war window."""
import argparse,json,shutil,socket
from pathlib import Path
from datetime import datetime
from contextlib import ExitStack
from prepare_combined_expansion_data import digest
from central_activation_receipts import verify_files
from realm_war_receipts import NATIVE_TARGETS,GODOT_TARGETS,NEW_NAMES

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def latest(folder,name='verified.json'):
    matches=[p for p in sorted(folder.glob('*/'+name)) if read(p).get('passed')]
    assert matches,str(folder)
    return matches[-1],read(matches[-1])

def install(workspace,apply=False):
    root=workspace/'RvRWindowsLab';receipt_path=root/'installed.json';baseline=verify_files(workspace)
    if baseline['realm_war_window_installed']:return dict(passed=True,already_current=True)
    assert baseline['inventory_quantity_installed']
    predecessor=workspace/'InventoryQuantityLab/installed.json';old=read(predecessor)
    bp=root/'native_build.json';build=read(bp);assert build['passed'] and build['normal_binary_sha256']==old['native_after_sha256']
    evidence=[bp,root/'resources.json',root/'state_tests.json']
    state=read(root/'state_tests.json');assert state['passed'] and state['checks']>=31
    proof,native=latest(root/'NativeAcceptance');assert native['checks']>=22 and native['build_receipt_sha256']==digest(bp);evidence.append(proof)
    proof,vault=latest(root/'VaultRegression');assert vault['state_checks']>=25 and vault['native_checks']>=87 and vault['build_receipt_sha256']==digest(bp);evidence.append(proof)
    proof,quantity=latest(root/'QuantityAcceptance');assert quantity['checks']>=20 and quantity['build_receipt_sha256']==digest(bp);evidence.append(proof)
    proof,windows=latest(root/'WindowAcceptance');assert windows['checks']>=53 and windows['build_receipt_sha256']==digest(bp);evidence.append(proof)
    real_path,real=latest(root/'RealProtocol');assert len(real['checks'])>=13 and all(real['checks'].values()) and real['normal_shutdown'] and real['database_restored'] and real['normal_runtime_unchanged'];evidence.append(real_path)
    source=Path(__file__).resolve().parents[1];native_source=source/'UnrealPlugin/DAoCVisualBridge';candidate=Path(build['project']).parent/'Plugins/DAoCVisualBridge';plugin=workspace/'Client/Plugins/DAoCVisualBridge'
    assert all(digest(native_source/'Source'/p)==h for p,h in build['source_sha256'].items())
    previous=read(workspace/'InventoryQuantityLab/native_build.json');old_sources={Path(p).as_posix():h for p,h in previous['source_sha256'].items()}
    before_proof=read(Path(old['real_protocol_proof']));rows=[]
    def add(origin,target,expected):
        assert target.resolve().is_relative_to(workspace.resolve())
        actual=digest(target) if target.exists() else None;assert actual==expected,(str(target),'unexpected predecessor')
        rows.append(dict(source=str(origin),target=str(target),before_sha256=actual,after_sha256=digest(origin)))
    for rel in NATIVE_TARGETS:
        target=plugin/rel;origin=(candidate if rel.startswith('Binaries/') else native_source)/rel
        expected=None if target.name in NEW_NAMES else old_sources[rel.removeprefix('Source/')] if rel.startswith('Source/') else previous['binaries_sha256'][target.name]
        add(origin,target,expected)
    for name in GODOT_TARGETS:
        origin=source/'Godot'/name;assert digest(origin)==real['source_inputs'][str(origin)]
        add(origin,workspace/'Godot'/name,None if name in NEW_NAMES else before_proof['source_inputs'][str(origin)])
    receipt=dict(installed=False,phase='planned',database_modified=False,server_rules_modified=False,map_geometry_modified=False,teleport_enabled=False,owner_gameplay_accepted=False,predecessor_receipt_sha256=digest(predecessor),native_before_sha256=build['normal_binary_sha256'],native_after_sha256=build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll'],real_protocol_proof=str(real_path),files=rows,evidence={str(p):digest(p) for p in evidence})
    plan=root/'install_plan.json';text=json.dumps(receipt,indent=2)
    if not apply:plan.write_text(text,encoding='utf-8');return dict(passed=True,dry_run=True,files=len(rows))
    assert read(plan)==receipt,'Regenerate and simulate the changed plan before applying'
    simulation=read(root/'install_simulation.json');assert simulation['passed'] and simulation['simulated_only'] and simulation['plan_sha256']==digest(plan) and simulation['core_source_sha256']==digest(Path(__file__).with_name('central_activation_receipts.py')) and simulation['realm_war_guard_sha256']==digest(Path(__file__).with_name('realm_war_receipts.py')) and simulation['quantity_guard_sha256']==digest(Path(__file__).with_name('inventory_quantity_receipts.py'))
    with ExitStack() as stack:
        for kind,port in [(socket.SOCK_STREAM,10300),(socket.SOCK_DGRAM,10400),(socket.SOCK_STREAM,19727)]:
            guard=stack.enter_context(socket.socket(socket.AF_INET,kind));guard.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1);guard.bind(('127.0.0.1',port))
            if kind==socket.SOCK_STREAM:guard.listen(1)
        backup=workspace/'Backups'/('RvRWindowsLab_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'));backup.mkdir()
        for i,row in enumerate(rows):
            target=Path(row['target']);assert (digest(target) if target.exists() else None)==row['before_sha256'] and digest(Path(row['source']))==row['after_sha256']
            if row['before_sha256'] is not None:
                saved=backup/str(i);shutil.copy2(target,saved);assert digest(saved)==row['before_sha256'];row['backup']=str(saved)
        receipt.update(phase='backed_up',backup_directory=str(backup));receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8');changed=[]
        try:
            for row in rows:
                target=Path(row['target']);target.parent.mkdir(parents=True,exist_ok=True);changed.append(row);shutil.copy2(row['source'],target);assert digest(target)==row['after_sha256']
            receipt.update(installed=True,phase='complete');receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8');assert verify_files(workspace)['realm_war_window_installed']
        except BaseException:
            for row in reversed(changed):
                target=Path(row['target'])
                if row['before_sha256'] is None:target.unlink(missing_ok=True)
                else:shutil.copy2(row['backup'],target)
            receipt.update(installed=False,phase='rolled_back');receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8');raise
    return dict(passed=True,installed=True,files=len(rows),database_modified=False,backup_directory=str(backup))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--apply',action='store_true');a=p.parse_args();print(json.dumps(install(a.workspace.resolve(),a.apply)))
