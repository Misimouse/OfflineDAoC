"""Guarded, reversible delivery of the verified original siege bodies and body animation."""
import argparse,json,shutil,socket
from pathlib import Path
from datetime import datetime
from contextlib import ExitStack
from prepare_combined_expansion_data import digest
from central_activation_receipts import verify_files
from siege_world_receipts import NATIVE_TARGETS,GODOT_TARGETS,NEW_NAMES,asset_rows

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def latest(folder,name='verified.json'):
    matches=[p for p in sorted(folder.glob('*/'+name)) if read(p).get('passed')]
    assert matches,str(folder)
    return matches[-1],read(matches[-1])

def install(workspace,apply=False):
    root=workspace/'SiegeWorldLab';receipt_path=root/'installed.json';baseline=verify_files(workspace)
    if baseline['siege_world_installed']:return dict(passed=True,already_current=True)
    assert baseline['ground_target_installed']
    predecessor=workspace/'GroundTargetLab/installed.json';old=read(predecessor)
    bp=root/'native_build.json';build=read(bp);assert build['passed'] and build['normal_binary_sha256']==old['native_after_sha256']
    assets,added_assets=asset_rows(workspace)
    original_catalogue=root/'catalogue_before.json'
    if not original_catalogue.exists():shutil.copy2(workspace/'models.json',original_catalogue)
    assert digest(original_catalogue)==digest(workspace/'models.json')
    assert read(root/'models_candidate.json')==dict(read(original_catalogue),**{k:r['entry'] for k,r in assets['models'].items()})
    export=read(root/'export_verified.json');assert export['passed'] and all(digest(Path(p))==h for p,h in export['source_inputs'].items())
    evidence=[bp,root/'asset_import.json',root/'export_verified.json',root/'state_tests.json',original_catalogue,root/'models_candidate.json']
    state=read(root/'state_tests.json');assert state['passed'] and state['checks']>=22 and all(digest(Path(p))==h for p,h in state['source_inputs'].items())
    proof,native=latest(root/'NativeAcceptance');assert native['checks']>=125 and native['build_receipt_sha256']==digest(bp);evidence.append(proof)
    proof,ground=latest(root/'GroundAcceptance');assert ground['checks']>=26 and ground['build_receipt_sha256']==digest(bp);evidence.append(proof)
    proof,combat=latest(root/'CombatRegression');assert combat['checks']>=14 and combat['build_receipt_sha256']==digest(bp);evidence.append(proof)
    proof,siege=latest(root/'SiegeAcceptance');assert siege['checks']>=26 and siege['build_receipt_sha256']==digest(bp);evidence.append(proof)
    proof,keys=latest(root/'KeyAcceptance');assert keys['passed'] and keys['checks']>=257 and keys['build_receipt_sha256']==digest(bp);evidence.append(proof)
    real_path,real=latest(root/'RealProtocol');assert len(real['checks'])>=24 and all(real['checks'].values()) and real['normal_shutdown'] and real['database_restored'] and real['normal_runtime_unchanged'];evidence.append(real_path)
    source=Path(__file__).resolve().parents[1];native_source=source/'UnrealPlugin/DAoCVisualBridge';candidate=Path(build['project']).parent/'Plugins/DAoCVisualBridge';plugin=workspace/'Client/Plugins/DAoCVisualBridge'
    assert all(digest(native_source/'Source'/p)==h for p,h in build['source_sha256'].items())
    previous=read(workspace/'GroundTargetLab/native_build.json');old_sources={Path(p).as_posix():h for p,h in previous['source_sha256'].items()}
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
    for row in added_assets:add(Path(row['source']),Path(row['target']),None)
    add(root/'models_candidate.json',workspace/'models.json',digest(original_catalogue))
    receipt=dict(installed=False,phase='planned',database_modified=False,server_rules_modified=False,map_geometry_modified=False,teleport_enabled=False,owner_gameplay_accepted=False,predecessor_receipt_sha256=digest(predecessor),native_before_sha256=build['normal_binary_sha256'],native_after_sha256=build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll'],real_protocol_proof=str(real_path),files=rows,evidence={str(p):digest(p) for p in evidence})
    plan=root/'install_plan.json';text=json.dumps(receipt,indent=2)
    if not apply:plan.write_text(text,encoding='utf-8');return dict(passed=True,dry_run=True,files=len(rows))
    assert read(plan)==receipt,'Regenerate and simulate the changed plan before applying'
    simulation=read(root/'install_simulation.json');assert simulation['passed'] and simulation['simulated_only'] and simulation['plan_sha256']==digest(plan) and simulation['core_source_sha256']==digest(Path(__file__).with_name('central_activation_receipts.py')) and simulation['siege_world_guard_sha256']==digest(Path(__file__).with_name('siege_world_receipts.py')) and simulation['ground_target_guard_sha256']==digest(Path(__file__).with_name('ground_target_receipts.py')) and simulation['siege_guard_sha256']==digest(Path(__file__).with_name('siege_receipts.py')) and simulation['realm_war_guard_sha256']==digest(Path(__file__).with_name('realm_war_receipts.py')) and simulation['quantity_guard_sha256']==digest(Path(__file__).with_name('inventory_quantity_receipts.py'))
    with ExitStack() as stack:
        for kind,port in [(socket.SOCK_STREAM,10300),(socket.SOCK_DGRAM,10400),(socket.SOCK_STREAM,19727)]:
            guard=stack.enter_context(socket.socket(socket.AF_INET,kind));guard.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1);guard.bind(('127.0.0.1',port))
            if kind==socket.SOCK_STREAM:guard.listen(1)
        backup=workspace/'Backups'/('SiegeWorldLab_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'));backup.mkdir()
        for i,row in enumerate(rows):
            target=Path(row['target']);assert (digest(target) if target.exists() else None)==row['before_sha256'] and digest(Path(row['source']))==row['after_sha256']
            if row['before_sha256'] is not None:
                saved=backup/str(i);shutil.copy2(target,saved);assert digest(saved)==row['before_sha256'];row['backup']=str(saved)
        receipt.update(phase='backed_up',backup_directory=str(backup));receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8');changed=[]
        try:
            for row in rows:
                target=Path(row['target']);target.parent.mkdir(parents=True,exist_ok=True);changed.append(row);shutil.copy2(row['source'],target);assert digest(target)==row['after_sha256']
            receipt.update(installed=True,phase='complete');receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8');assert verify_files(workspace)['siege_world_installed']
        except BaseException:
            for row in reversed(changed):
                target=Path(row['target'])
                if row['before_sha256'] is None:target.unlink(missing_ok=True)
                else:shutil.copy2(row['backup'],target)
            receipt.update(installed=False,phase='rolled_back');receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8');raise
    return dict(passed=True,installed=True,files=len(rows),database_modified=False,backup_directory=str(backup))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--apply',action='store_true');a=p.parse_args();print(json.dumps(install(a.workspace.resolve(),a.apply)))
