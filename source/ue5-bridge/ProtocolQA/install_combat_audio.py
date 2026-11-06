"""Deliver accepted combat audio files only, preserving DB and historical receipts."""
import argparse
from contextlib import ExitStack
from datetime import datetime
import json
from pathlib import Path
import shutil
import socket
import subprocess

from central_activation_receipts import verify_files
from prepare_combined_expansion_data import digest


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def install(workspace, apply=False):
    repo=Path(__file__).resolve().parents[3]
    root=workspace/'CombatAudioLab'
    central=workspace/'Client/Plugins/DAoCVisualBridge'
    built=read(root/'native_build.json');resources=read(root/'resources.json')
    proof=read(root/'NativeAcceptance/verified.json');regression=read(root/'CharacterRegression/verified.json')
    state=read(root/'StateTest/verified.json')
    protocol_path=workspace/'Reports/combat_audio_real_protocol/real_protocol.json'
    protocol=read(protocol_path)
    assert all(p['passed'] for p in [built,resources,proof,regression,state,protocol])
    assert not resources['installed'] and not state['server_started'] and state['checks']>=22
    assert proof['build_receipt_sha256']==digest(root/'native_build.json')
    assert proof['resources_receipt_sha256']==digest(root/'resources.json')
    assert proof['reports']['combat']['checks']>=14 and proof['reports']['spell_regression']['checks']>=15
    assert regression['combat_audio_candidate'] and regression['material_isolation_passed']
    assert regression['known_source_geometry_failure']==['world and frozen miniature publish actual facial render weights 1419']
    assert all(protocol[k] for k in ['normal_shutdown','database_restored','candidate_server_restored'])
    assert not protocol['errors'] and protocol['checks']['original_real_combat_audio_consumed_by_engine']
    assert protocol['combat_power']['normal_player_privileges'] and protocol['combat_power']['no_resource_grants']
    assert protocol['combat_power']['walked_out_of_melee_before_quit']
    assert protocol['native_combat_audio']['pcm_consumed_bytes']>0 and protocol['native_combat_audio']['invalid_resources']==0
    assert protocol['combat_audio_wire_trace']
    for group in [state['inputs'],protocol['native_audio_inputs'],regression['inputs'],resources['input_hashes'],resources['files']]:
        assert all(digest(Path(p))==sha for p,sha in group.items())
    native_source=repo/'source/ue5-bridge/UnrealPlugin/DAoCVisualBridge/Source'
    assert all(digest(native_source/p)==sha for p,sha in built['source_sha256'].items())
    old_path=workspace/'SpellAudioLab/installed.json';old=read(old_path)
    assert old['installed'] and old['phase']=='complete'
    assert built['normal_binary_sha256']==old['normal_native_sha256']
    minotaur_path=workspace/'ExpansionRaceLab/CentralDelivery/MinotaurActivation/installed.json'
    assert read(minotaur_path)['installed']
    candidate=Path(built['project']).parent/'Plugins/DAoCVisualBridge'
    pairs=[]
    for name,sha in built['binaries_sha256'].items():
        path=candidate/'Binaries/Win64'/name
        assert digest(path)==sha
        pairs.append((path,central/'Binaries/Win64'/name))
    for name in ['DAoCVisualBridge.Build.cs','Public/DAoCBridgeSubsystem.h','Private/DAoCBridgeSpellAudio.cpp',
                 'Private/DAoCBridgeSpellAudioAcceptance.cpp','Private/DAoCBridgeCombatAudioAcceptance.cpp']:
        pairs.append((native_source/'DAoCVisualBridge'/name,central/'Source/DAoCVisualBridge'/name))
    for name in ['live_gateway.gd','visual_bridge.gd','combat_audio_state.gd']:
        pairs.append((repo/'source/ue5-bridge/Godot'/name,workspace/'Godot'/name))
    audio_source=Path(resources['catalog']).parent.resolve()
    assert audio_source==root/'OriginalCombatAudio_v01'
    audio_files=dict(resources['files']);audio_files[resources['catalog']]=resources['catalog_sha256']
    for p,sha in audio_files.items():
        path=Path(p).resolve()
        assert path.is_relative_to(audio_source) and digest(path)==sha
        pairs.append((path,central/'Content/OriginalCombatAudio_v01'/path.relative_to(audio_source)))
    receipt_path=root/'installed.json'
    if receipt_path.exists():
        receipt=read(receipt_path)
        assert receipt['installed'] and receipt['phase']=='complete'
        assert receipt['spell_audio_receipt_sha256']==digest(old_path)
        assert all(digest(Path(row['target']))==row['after_sha256'] for row in receipt['files'])
        assert all(digest(s)==digest(t) for s,t in pairs)
        verify_files(workspace)
        return {'passed':True,'installed':True,'already_current':True}
    verify_files(workspace)
    # The predecessor's complete file set must still be present before replacing it.
    assert all(digest(Path(row['target']))==row['after_sha256'] for row in old['files'])
    rows=[]
    for s,t in pairs:
        assert s.is_file() and t.resolve().is_relative_to(workspace.resolve())
        after=digest(s);before=digest(t) if t.exists() else None
        if t.is_relative_to(central/'Content/OriginalCombatAudio_v01'):assert before is None or before==after
        rows.append({'source':str(s),'target':str(t),'before_sha256':before,'after_sha256':after})
    gateway=next(row for row in rows if row['target']==str(workspace/'Godot/live_gateway.gd'))
    old_gateway=next(row for row in read(minotaur_path)['files'] if row['target']==gateway['target'])
    assert gateway['before_sha256']==old_gateway['after_sha256']
    evidence={str(p):digest(p) for p in [root/'native_build.json',root/'resources.json',root/'NativeAcceptance/verified.json',
        root/'CharacterRegression/verified.json',root/'StateTest/verified.json',protocol_path]}
    receipt={'passed':True,'installed':False,'database_modified':False,'files':rows,'evidence':evidence,
        'spell_audio_receipt_sha256':digest(old_path),'minotaur_receipt_sha256':digest(minotaur_path),
        'native_before_sha256':built['normal_binary_sha256'],'native_after_sha256':built['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll']}
    (root/'install_plan.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    if not apply:return {'passed':True,'installed':False,'files':len(rows),'dry_run':True}
    running=subprocess.check_output(['powershell.exe','-NoProfile','-Command',
        "@(Get-Process -Name 'UnrealEditor','UnrealEditor-Cmd','DAoCEnhanced','DAoCBridgeClient' -ErrorAction SilentlyContinue).Count"],text=True,creationflags=subprocess.CREATE_NO_WINDOW).strip()
    assert running=='0','Close editor/game normally before installation'
    with ExitStack() as stack:
        for kind,port in [(socket.SOCK_STREAM,10300),(socket.SOCK_DGRAM,10400),(socket.SOCK_STREAM,19727)]:
            guard=stack.enter_context(socket.socket(socket.AF_INET,kind));guard.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
            guard.bind(('127.0.0.1',port))
            if kind==socket.SOCK_STREAM:guard.listen(1)
        backup=workspace/'Backups'/('CombatAudio_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'));backup.mkdir()
        assert backup.resolve().is_relative_to((workspace/'Backups').resolve())
        for index,row in enumerate(rows):
            t=Path(row['target'])
            assert digest(Path(row['source']))==row['after_sha256']
            assert (digest(t) if t.exists() else None)==row['before_sha256']
            if row['before_sha256'] is not None:
                saved=backup/(str(index)+'.before');shutil.copy2(t,saved)
                assert digest(saved)==row['before_sha256'];row['backup']=str(saved)
        receipt.update(phase='backed_up',backup_directory=str(backup))
        receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
        changed=[]
        try:
            for row in rows:
                s,t=Path(row['source']),Path(row['target']);changed.append(row)
                t.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(s,t);assert digest(t)==row['after_sha256']
            assert all(digest(Path(p))==sha for p,sha in evidence.items())
            receipt.update(installed=True,phase='complete',audible_owner_acceptance=False)
            receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
            verify_files(workspace)
        except BaseException:
            for row in reversed(changed):
                t=Path(row['target']);current=digest(t) if t.exists() else None
                if current==row['before_sha256']:continue
                if row['before_sha256'] is None:
                    assert current==row['after_sha256'];t.unlink()
                else:shutil.copy2(row['backup'],t);assert digest(t)==row['before_sha256']
            receipt.update(installed=False,phase='rolled_back')
            receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8');raise
    return {'passed':True,'installed':True,'files':len(rows),'database_modified':False,'backup_directory':str(backup)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True);parser.add_argument('--apply',action='store_true')
    args=parser.parse_args();print(json.dumps(install(args.workspace.resolve(),args.apply)))
