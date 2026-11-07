"""Preview by default: install or restore only the verified editable-controls delivery."""
import argparse,json,shutil,socket
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path
from central_activation_receipts import verify_files,KEY_CONFIGURATION_NATIVE_TARGETS,KEY_CONFIGURATION_NEW_NAMES,INTERFACE_KEYS_NATIVE_TARGETS
from prepare_combined_expansion_data import digest

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def latest(p):return sorted(p.glob('*/verified.json'))[-1]
def install(workspace,apply=False,rollback=False,lab_name="KeyConfigurationLab"):
    assert lab_name in ["KeyConfigurationLab","InterfaceKeysLab"]
    interface=lab_name=="InterfaceKeysLab"
    root=workspace/lab_name;rp=root/'installed.json';plugin=workspace/'Client/Plugins/DAoCVisualBridge'
    if rp.exists() and read(rp).get('installed') and not rollback:
        verify_files(workspace);return dict(passed=True,already_current=True)
    verify_files(workspace)
    if rollback:
        receipt=read(rp);assert receipt['installed'] and receipt['phase']=='complete';rows=receipt['files']
    else:
        bp=root/'native_build.json';build=read(bp);assert build['passed']
        prior=workspace/('KeyConfigurationLab/installed.json' if interface else 'LiveRidingLab/installed.json');assert read(prior)['native_after_sha256']==build['normal_binary_sha256']
        evidence=[bp,latest(root/'Acceptance'),latest(root/'NativeAcceptance'),root/'movement_regressions.json']
        specific=read(evidence[1]);assert specific['passed'] and specific['checks']>=(256 if interface else 51) and not specific['failures'] and specific['build_receipt_sha256']==digest(bp)
        native=read(evidence[2]);assert native['passed'] and native['build_receipt_sha256']==digest(bp)
        for name,n in [('server_sound',40),('footstep',149),('door',15),('options',17),('selection',15),('combat',14),('spell',15)]:
            proof=native['reports'][name];assert proof['passed'] and proof['checks']>=n and not proof['failures']
        if interface:
            ui_path=latest(root/'UIRegression');ui=read(ui_path);assert ui['passed'] and ui['build_receipt_sha256']==digest(bp)
            for case in ['classic','player']:assert ui['reports'][case]['passed'] and ui['reports'][case]['checks']>=68
            assert all(digest(Path(p))==h for p,h in ui['input_hashes'].items());evidence.append(ui_path)
            audit_path=root/'reference_audit.json';audit=read(audit_path);assert audit['passed'] and len(audit['rows'])==55;evidence.append(audit_path)
        movement=read(evidence[3]);assert movement['passed'] and movement['build_receipt_sha256']==digest(bp)
        for name,n in [('movement',53),('jump',9),('tracking',35),('water',65550)]:
            case=movement['results'][name];assert case['passed'] and case['checks']>=n
            path=Path(case['output'])/'verified.json';proof=read(path);assert proof['passed'] and proof['build_receipt_sha256']==digest(bp);evidence.append(path)
        real=None
        for p in sorted((workspace/'Reports/live_riding_real_protocol').glob('*/verified.json')):
            v=read(p)
            if v.get('passed') and v.get('native_inputs',{}).get(str(bp))==digest(bp) and v['checks'].get('actual_space_key_dismount_request_and_ack'):real=(p,v)
        assert real,'Current candidate requires real riding and native dismount proof'
        p,v=real;assert v['normal_shutdown'] and v['database_restored'] and v['native_exit']==0 and not v['errors']
        for name in ['unsupported_route_no_charge_no_item_no_mount','original_ticket_buy_mount_ack_and_pose','actual_server_route_movement','original_gallop_pcm_consumed_during_real_route','actual_dismount_ack_and_grounded_collision','no_new_hoof_sounds_after_dismount']:assert v['checks'][name]
        for p0,h in {**v['source_inputs'],**v['native_inputs']}.items():assert digest(Path(p0))==h
        evidence.append(p)
        repo=Path(__file__).resolve().parents[3];source=repo/'source/ue5-bridge/UnrealPlugin/DAoCVisualBridge'
        assert all(digest(source/'Source'/p)==h for p,h in build['source_sha256'].items())
        candidate=Path(build['project']).parent/'Plugins/DAoCVisualBridge';rows=[]
        preceding_source={}
        if interface:
            prior_build=workspace/'KeyConfigurationLab/native_build.json'
            assert digest(prior_build)==read(prior)['evidence'][str(prior_build)]
            preceding_source={Path(p).as_posix():h for p,h in read(prior_build)['source_sha256'].items()}
        for rel in (INTERFACE_KEYS_NATIVE_TARGETS if interface else KEY_CONFIGURATION_NATIVE_TARGETS):
            origin=(candidate if rel.startswith('Binaries/') else source)/rel;target=plugin/rel
            assert target.resolve().is_relative_to(workspace.resolve())
            old=digest(target) if target.exists() else None;assert (old is None)==(not interface and target.name in KEY_CONFIGURATION_NEW_NAMES)
            if interface and rel.startswith('Source/'):assert old==preceding_source[rel.removeprefix('Source/')], 'Preceding compiled source was changed: '+str(target)
            if rel.startswith('Binaries/'):assert digest(origin)==build['binaries_sha256'][target.name]
            rows.append(dict(source=str(origin),target=str(target),before_sha256=old,after_sha256=digest(origin)))
        receipt=dict(installed=False,phase='planned',database_modified=False,server_rules_modified=False,owner_gameplay_accepted=False,
            native_before_sha256=build['normal_binary_sha256'],native_after_sha256=build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll'],
            predecessor_receipt_sha256=digest(prior),files=rows,evidence={str(p):digest(p) for p in evidence})
        (root/'install_plan.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    if not apply:return dict(passed=True,dry_run=True,files=len(rows),rollback=rollback)
    with ExitStack() as stack:
        for kind,port in [(socket.SOCK_STREAM,10300),(socket.SOCK_DGRAM,10400),(socket.SOCK_STREAM,19727)]:
            guard=stack.enter_context(socket.socket(socket.AF_INET,kind));guard.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1);guard.bind(('127.0.0.1',port))
            if kind==socket.SOCK_STREAM:guard.listen(1)
        if rollback:
            for row in rows:
                assert Path(row['target']).resolve().is_relative_to(workspace.resolve()) and digest(Path(row['target']))==row['after_sha256']
                if row['before_sha256'] is not None:assert digest(Path(row['backup']))==row['before_sha256']
            for row in reversed(rows):
                if row['before_sha256'] is None:Path(row['target']).unlink()
                else:shutil.copy2(row['backup'],row['target'])
            receipt.update(installed=False,phase='rolled_back');rp.write_text(json.dumps(receipt,indent=2));verify_files(workspace);return dict(passed=True,rolled_back=True)
        backup=workspace/'Backups'/(lab_name+'_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'));backup.mkdir()
        for i,row in enumerate(rows):
            target=Path(row['target']);assert (digest(target) if target.exists() else None)==row['before_sha256'] and digest(Path(row['source']))==row['after_sha256']
            if row['before_sha256'] is not None:
                saved=backup/str(i);shutil.copy2(target,saved);assert digest(saved)==row['before_sha256'];row['backup']=str(saved)
        receipt.update(phase='backed_up',backup_directory=str(backup));rp.write_text(json.dumps(receipt,indent=2));changed=[]
        try:
            for row in rows:
                target=Path(row['target']);target.parent.mkdir(parents=True,exist_ok=True);changed.append(row);shutil.copy2(row['source'],target);assert digest(target)==row['after_sha256']
            receipt.update(installed=True,phase='complete');rp.write_text(json.dumps(receipt,indent=2));verify_files(workspace)
        except BaseException:
            for row in reversed(changed):
                target=Path(row['target']);assert target.resolve().is_relative_to(workspace.resolve())
                if row['before_sha256'] is None:target.unlink(missing_ok=True)
                else:assert digest(Path(row['backup']))==row['before_sha256'];shutil.copy2(row['backup'],target)
            receipt.update(installed=False,phase='rolled_back');rp.write_text(json.dumps(receipt,indent=2));raise
    return dict(passed=True,installed=True,files=len(rows),backup_directory=str(backup),database_modified=False)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--apply',action='store_true');p.add_argument('--rollback',action='store_true');p.add_argument('--interface-keys',action='store_true');a=p.parse_args()
    print(json.dumps(install(a.workspace.resolve(),a.apply,a.rollback,'InterfaceKeysLab' if a.interface_keys else 'KeyConfigurationLab')))
