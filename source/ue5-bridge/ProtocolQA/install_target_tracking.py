"""Deliver verified local face/follow/stick without changing server rules, maps or saves."""
import argparse
from contextlib import ExitStack
from datetime import datetime
import json
from pathlib import Path
import shutil
import socket
from central_activation_receipts import verify_files,TARGET_TRACKING_NATIVE_TARGETS
from prepare_combined_expansion_data import digest

def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))

def install(workspace,apply=False,rollback=False):
    root=workspace/'TargetTrackingLab';receipt_path=root/'installed.json';plugin=workspace/'Client/Plugins/DAoCVisualBridge'
    if receipt_path.exists() and read(receipt_path).get('installed') and not rollback:
        verify_files(workspace);return {'passed':True,'already_current':True}
    verify_files(workspace)
    if rollback:
        receipt=read(receipt_path);assert receipt['installed'] and receipt['phase']=='complete';rows=receipt['files']
    else:
        native_path=sorted((root/'NativeAcceptance').glob('*/verified.json'))[-1];native=read(native_path)
        real_path=sorted((workspace/'Reports/target_tracking_real_protocol').glob('*/verified.json'))[-1];real=read(real_path)
        build_path=root/'native_build.json';build=read(build_path);resources_path=root/'resources.json';resources=read(resources_path)
        state_path=sorted((root/'StateTest').glob('*/verified.json'))[-1];state=read(state_path)
        assert state['passed'] and state['checks']>=37 and not state['normal_installation_modified']
        assert all(digest(Path(p))==sha for p,sha in state['source_inputs'].items())
        rules_path=sorted((root/'NativeTrackingAcceptance').glob('*/verified.json'))[-1];rules=read(rules_path)
        assert rules['passed'] and rules['checks']>=35 and not rules['failures'] and rules['build_receipt_sha256']==digest(build_path) and rules['resources_receipt_sha256']==digest(resources_path)
        assert native['passed'] and native['build_receipt_sha256']==digest(build_path) and not native['normal_binary_modified']
        for name,count in [('server_sound',40),('footstep',149),('door',15),('options',17),('selection',15),('combat',14),('spell',15)]:assert native['reports'][name]['passed'] and native['reports'][name]['checks']>=count and not native['reports'][name]['failures']
        assert real['passed'] and real['disposable_only'] and real['normal_shutdown'] and real['database_restored'] and not real['errors'] and real['native_exit']==0
        assert real['native_inputs'][str(build_path)]==digest(build_path)
        for group in [real['source_inputs'],real['native_inputs']]:assert all(digest(Path(p))==sha for p,sha in group.items())
        for check in ['actual_face_keeps_position','follow_respects_closed_real_door','actual_follow_switches_target_and_stops','actual_stick_stops_at_close_gap','actual_target_despawn_cancels_tracking']:assert real['checks'][check]
        assert all(digest(Path(p))==sha for p,sha in resources['input_hashes'].items())
        predecessor=workspace/'MovementKeysLab/installed.json';assert read(predecessor)['native_after_sha256']==build['normal_binary_sha256']
        source=Path(__file__).resolve().parents[3]/'source/ue5-bridge/UnrealPlugin/DAoCVisualBridge'
        assert all(digest(source/'Source'/name)==sha for name,sha in build['source_sha256'].items())
        candidate=Path(build['project']).parent/'Plugins/DAoCVisualBridge'
        pairs=[(candidate/name if name.startswith('Binaries/') else source/name,plugin/name) for name in TARGET_TRACKING_NATIVE_TARGETS]
        godot=Path(__file__).resolve().parents[1]/'Godot'
        pairs += [(godot/name,workspace/'Godot'/name) for name in ['live_gateway.gd','visual_bridge.gd','target_tracking_state.gd']]
        rows=[]
        for origin,target in pairs:
            assert target.resolve().is_relative_to(workspace.resolve());before=digest(target) if target.exists() else None
            new=target.name in ['DAoCBridgeTargetTracking.h','DAoCBridgeTargetTracking.cpp','DAoCBridgeTargetTrackingAcceptance.cpp','target_tracking_state.gd']
            assert (before is None)==new
            rows.append({'source':str(origin),'target':str(target),'before_sha256':before,'after_sha256':digest(origin)})
        receipt={'installed':False,'phase':'planned','database_modified':False,'local_target_tracking_implemented':True,'server_rules_modified':False,'pathfinding_implemented':False,'visuals_modified':False,'npc_steps_enabled':False,
            'native_before_sha256':build['normal_binary_sha256'],'native_after_sha256':build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll'],
            'predecessor_receipt_sha256':digest(predecessor),'resources_receipt_sha256':digest(resources_path),'files':rows,
            'evidence':{str(p):digest(p) for p in [native_path,real_path,build_path,resources_path,state_path,rules_path]}}
        (root/'install_plan.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    if not apply:return {'passed':True,'dry_run':True,'files':len(rows),'rollback':rollback}
    with ExitStack() as stack:
        for kind,port in [(socket.SOCK_STREAM,10300),(socket.SOCK_DGRAM,10400),(socket.SOCK_STREAM,19727)]:
            guard=stack.enter_context(socket.socket(socket.AF_INET,kind));guard.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1);guard.bind(('127.0.0.1',port))
            if kind==socket.SOCK_STREAM:guard.listen(1)
        if rollback:
            for row in rows:
                target=Path(row['target']);assert target.resolve().is_relative_to(workspace.resolve()) and digest(target)==row['after_sha256']
                if row['before_sha256'] is not None:assert digest(Path(row['backup']))==row['before_sha256']
            for row in reversed(rows):
                target=Path(row['target'])
                if row['before_sha256'] is None:target.unlink()
                else:shutil.copy2(row['backup'],target)
            receipt.update(installed=False,phase='rolled_back');receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8');verify_files(workspace)
            return {'passed':True,'rolled_back':True}
        backup=workspace/'Backups'/('TargetTracking_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'));backup.mkdir()
        for i,row in enumerate(rows):
            target=Path(row['target']);assert (digest(target) if target.exists() else None)==row['before_sha256'] and digest(Path(row['source']))==row['after_sha256']
            if row['before_sha256'] is not None:
                saved=backup/str(i);shutil.copy2(target,saved);assert digest(saved)==row['before_sha256'];row['backup']=str(saved)
        receipt.update(phase='backed_up',backup_directory=str(backup));receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8');changed=[]
        try:
            for row in rows:
                target=Path(row['target']);target.parent.mkdir(parents=True,exist_ok=True);changed.append(row);shutil.copy2(row['source'],target);assert digest(target)==row['after_sha256']
            receipt.update(installed=True,phase='complete');receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8');verify_files(workspace)
        except BaseException:
            for row in reversed(changed):
                target=Path(row['target']);assert target.resolve().is_relative_to(workspace.resolve())
                if row['before_sha256'] is None:target.unlink(missing_ok=True)
                else:assert digest(Path(row['backup']))==row['before_sha256'];shutil.copy2(row['backup'],target)
            receipt.update(installed=False,phase='rolled_back');receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8');raise
    return {'passed':True,'installed':True,'files':len(rows),'backup_directory':str(backup),'database_modified':False}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--apply',action='store_true');parser.add_argument('--rollback',action='store_true');args=parser.parse_args();print(json.dumps(install(args.workspace.resolve(),args.apply,args.rollback)))
