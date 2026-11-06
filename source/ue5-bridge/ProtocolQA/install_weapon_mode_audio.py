"""Install only accepted local draw/sheathe triggers; no native rebuild or DB writes."""
import argparse
from contextlib import ExitStack
from datetime import datetime
import json
from pathlib import Path
import shutil
import socket

from central_activation_receipts import verify_files
from prepare_combined_expansion_data import digest


def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))


def install(workspace, apply=False):
    repo=Path(__file__).resolve().parents[3]
    root=workspace/'WeaponModeAudioLab'
    receipt_path=root/'installed.json'
    if receipt_path.exists():
        receipt=read(receipt_path)
        assert receipt['installed'] and receipt['phase']=='complete'
        assert all(digest(Path(p))==sha for p,sha in receipt['evidence'].items())
        verify_files(workspace)
        return {'passed':True,'installed':True,'already_current':True}
    base_path=workspace/'CombatAudioLab/installed.json';base=read(base_path)
    assert base['installed'] and base['phase']=='complete'
    verify_files(workspace)
    state_path=root/'StateTest/verified.json';state=read(state_path)
    protocol_path=workspace/'Reports/weapon_mode_audio_real_protocol/real_protocol.json';protocol=read(protocol_path)
    native_path=workspace/'CombatAudioLab/NativeInstalledAcceptance/verified.json';native=read(native_path)
    assert state['passed'] and state['checks']>=15 and not state['server_started']
    assert native['passed'] and native['installed_client_resources_only']
    assert native['reports']['combat']['checks']>=14 and native['reports']['spell_regression']['checks']>=15
    assert all(protocol[k] for k in ['passed','real_protocol','disposable_only','normal_shutdown','database_restored','candidate_server_restored'])
    assert not protocol['errors']
    assert protocol['checks']['original_server_confirmed_draw_and_sheathe_audio']
    trace=protocol['combat_audio_wire_trace'];audio=protocol['native_combat_audio']
    assert any(row['event']=='activate' for row in trace) and any(row['event']=='deactivate' for row in trace)
    assert audio['combat_events_seen']>=len(trace) and audio['played_clips']>=len(trace)
    assert audio['pcm_consumed_bytes']>0 and audio['invalid_resources']==0 and audio['unresolved_references']==0
    assert protocol['combat_power']['normal_player_privileges'] and protocol['combat_power']['no_resource_grants']
    assert protocol['combat_power']['walked_out_of_melee_before_quit']
    for group in [state['inputs'],protocol['native_audio_inputs']]:assert all(digest(Path(p))==sha for p,sha in group.items())
    binary=workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    assert digest(binary)==base['native_after_sha256']
    observed=workspace/'CombatAudioLab/NativeHost/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    assert digest(observed)==digest(binary)
    rows=[]
    for name in ['weapon_mode_audio_state.gd','live_gateway.gd']:
        source=repo/'source/ue5-bridge/Godot'/name;target=workspace/'Godot'/name
        assert target.resolve().is_relative_to(workspace.resolve())
        before=digest(target) if target.exists() else None
        if name=='weapon_mode_audio_state.gd':assert before is None,'Refuse to overwrite an unrecorded trigger module'
        else:assert before==next(row['after_sha256'] for row in base['files'] if row['target']==str(target))
        rows.append({'source':str(source),'target':str(target),'before_sha256':before,'after_sha256':digest(source)})
    evidence={str(p):digest(p) for p in [state_path,protocol_path,native_path]}
    receipt={'passed':True,'installed':False,'database_modified':False,'native_binary_modified':False,
        'predecessor_receipt_sha256':digest(base_path),'native_sha256':digest(binary),'files':rows,'evidence':evidence}
    (root/'install_plan.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    if not apply:return {'passed':True,'installed':False,'dry_run':True,'files':len(rows),'native_binary_modified':False}
    with ExitStack() as stack:
        for kind,port in [(socket.SOCK_STREAM,10300),(socket.SOCK_DGRAM,10400),(socket.SOCK_STREAM,19727)]:
            guard=stack.enter_context(socket.socket(socket.AF_INET,kind));guard.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
            guard.bind(('127.0.0.1',port))
            if kind==socket.SOCK_STREAM:guard.listen(1)
        backup=workspace/'Backups'/('WeaponModeAudio_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'));backup.mkdir()
        assert backup.resolve().is_relative_to((workspace/'Backups').resolve())
        for index,row in enumerate(rows):
            target=Path(row['target'])
            assert (digest(target) if target.exists() else None)==row['before_sha256']
            assert digest(Path(row['source']))==row['after_sha256']
            if row['before_sha256'] is not None:
                saved=backup/(str(index)+'.before');shutil.copy2(target,saved)
                assert digest(saved)==row['before_sha256'];row['backup']=str(saved)
        changed=[]
        receipt.update(phase='backed_up',backup_directory=str(backup))
        receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
        try:
            for row in rows:
                target=Path(row['target']);changed.append(row)
                shutil.copy2(row['source'],target);assert digest(target)==row['after_sha256']
            assert digest(binary)==receipt['native_sha256']
            assert all(digest(Path(p))==sha for p,sha in evidence.items())
            receipt.update(installed=True,phase='complete',audible_owner_acceptance=False)
            receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8');verify_files(workspace)
        except BaseException:
            for row in reversed(changed):
                target=Path(row['target']);current=digest(target) if target.exists() else None
                if current==row['before_sha256']:continue
                if row['before_sha256'] is None:
                    assert current==row['after_sha256'];target.unlink()
                else:shutil.copy2(row['backup'],target);assert digest(target)==row['before_sha256']
            receipt.update(installed=False,phase='rolled_back')
            receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8');raise
    return {'passed':True,'installed':True,'files':len(rows),'native_binary_modified':False,'database_modified':False,'backup_directory':str(backup)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True);parser.add_argument('--apply',action='store_true')
    args=parser.parse_args();print(json.dumps(install(args.workspace.resolve(),args.apply)))
