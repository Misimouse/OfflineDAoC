"""Install only the proven spell audio client, with hash guards and file rollback."""
import argparse
from contextlib import ExitStack
from datetime import datetime
import json
from pathlib import Path
import shutil
import socket
import subprocess

from prepare_combined_expansion_data import digest


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def install(workspace, apply=False):
    repo=Path(__file__).resolve().parents[3]
    root=workspace/'SpellAudioLab'
    central=workspace/'Client/Plugins/DAoCVisualBridge'
    built=read(root/'native_build.json')
    resources=read(root/'resources.json')
    proof=read(root/'NativeAcceptance/verified.json')
    regression=read(root/'CharacterRegression/verified.json')
    protocol_path=workspace/'Reports/spell_audio_real_protocol/race_9/real_protocol.json'
    protocol=read(protocol_path)
    state=read(root/'StateTest/verified.json')
    assert state['passed'] and not state['server_started']
    assert all(digest(Path(p))==sha for p,sha in state['inputs'].items())
    assert built['passed'] and resources['passed'] and proof['passed'] and regression['passed'] and protocol['passed']
    assert proof['native_build_receipt_sha256']==digest(root/'native_build.json')
    assert proof['resources_receipt_sha256']==digest(root/'resources.json')
    assert regression['audio_candidate'] and regression['material_isolation_passed']
    assert not regression['full_appearance_passed']
    assert regression['known_source_geometry_failure']==['world and frozen miniature publish actual facial render weights 1419']
    assert all(protocol[k] for k in ['normal_shutdown','database_restored','candidate_server_restored','qa_native_catalogue_restored'])
    assert protocol['checks']['original_real_server_spell_audio_consumed_by_engine']
    assert protocol['native_spell_audio']['pcm_consumed_bytes']>0
    assert protocol['native_spell_audio']['invalid_resources']==0
    assert all(digest(Path(p))==sha for p,sha in protocol['native_form_inputs'].items())
    assert all(digest(Path(p))==sha for p,sha in regression['inputs'].items())
    assert all(digest(Path(p))==sha for p,sha in resources['input_hashes'].items())
    source=repo/'source/ue5-bridge/UnrealPlugin/DAoCVisualBridge/Source'
    assert all(digest(source/p)==sha for p,sha in built['source_sha256'].items())
    candidate=Path(built['project']).parent/'Plugins/DAoCVisualBridge'
    pairs=[]
    for name,sha in built['binaries_sha256'].items():
        path=candidate/'Binaries/Win64'/name
        assert digest(path)==sha
        pairs.append((path,central/'Binaries/Win64'/name))
    # Keep future builds reproducible, without replacing unrelated source files.
    for name in ['DAoCVisualBridge.Build.cs','Public/DAoCBridgeSubsystem.h',
                 'Private/DAoCBridgeSubsystem.cpp','Private/DAoCBridgeSpellAudio.cpp',
                 'Private/DAoCBridgeSpellAudioAcceptance.cpp']:
        pairs.append((source/'DAoCVisualBridge'/name,central/'Source/DAoCVisualBridge'/name))
    pairs.append((repo/'source/ue5-bridge/Godot/spell_visual_state.gd',workspace/'Godot/spell_visual_state.gd'))
    audio_source=Path(resources['catalog']).parent.resolve()
    assert audio_source==root/'OriginalAudio_v01'
    audio_files=dict(resources['files'])
    audio_files[resources['catalog']]=resources['catalog_sha256']
    for path,sha in audio_files.items():
        path=Path(path).resolve()
        assert path.is_relative_to(audio_source) and digest(path)==sha
        pairs.append((path,central/'Content/OriginalAudio_v01'/path.relative_to(audio_source)))
    receipt_path=root/'installed.json'
    if receipt_path.exists():
        receipt=read(receipt_path)
        assert receipt['installed'] and receipt['phase']=='complete'
        assert all(digest(Path(row['target']))==row['after_sha256'] for row in receipt['files'])
        assert all(digest(s)==digest(t) for s,t in pairs)
        return {'passed':True,'installed':True,'already_current':True}
    assert digest(central/'Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll')==built['normal_binary_sha256']
    rows=[]
    for s,t in pairs:
        assert s.is_file() and t.resolve().is_relative_to(workspace.resolve())
        after=digest(s)
        before=digest(t) if t.exists() else None
        if t.is_relative_to(central/'Content/OriginalAudio_v01'):
            assert before is None or before==after, 'Never replace an unrecognized audio asset'
        rows.append({'source':str(s),'target':str(t),'before_sha256':before,'after_sha256':after})
    evidence={str(p):digest(p) for p in [root/'native_build.json',root/'resources.json',root/'NativeAcceptance/verified.json',root/'CharacterRegression/verified.json',root/'StateTest/verified.json',protocol_path]}
    plan={'passed':True,'installed':False,'database_modified':False,'files':rows,'evidence':evidence}
    (root/'install_plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
    if not apply:return {'passed':True,'installed':False,'files':len(rows),'dry_run':True}
    # No running user editor/game may retain the old client DLL.
    running=subprocess.check_output(['powershell.exe','-NoProfile','-Command',
        "@(Get-Process -Name 'UnrealEditor','UnrealEditor-Cmd','DAoCEnhanced','DAoCBridgeClient' -ErrorAction SilentlyContinue).Count"],text=True,creationflags=subprocess.CREATE_NO_WINDOW).strip()
    assert running=='0','Close UE/editor and game normally before client installation'
    with ExitStack() as stack:
        for kind,port in [(socket.SOCK_STREAM,10300),(socket.SOCK_DGRAM,10400),(socket.SOCK_STREAM,19727)]:
            guard=stack.enter_context(socket.socket(socket.AF_INET,kind))
            guard.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
            guard.bind(('127.0.0.1',port))
            if kind==socket.SOCK_STREAM:guard.listen(1)
        backup=workspace/'Backups'/('SpellAudio_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        backup.mkdir()
        assert backup.resolve().is_relative_to((workspace/'Backups').resolve())
        for index,row in enumerate(rows):
            s,t=Path(row['source']),Path(row['target'])
            assert digest(s)==row['after_sha256']
            assert (digest(t) if t.exists() else None)==row['before_sha256']
            if row['before_sha256'] is not None:
                saved=backup/(str(index)+'.before')
                shutil.copy2(t,saved)
                assert digest(saved)==row['before_sha256']
                row['backup']=str(saved)
        receipt=dict(plan,phase='backed_up',backup_directory=str(backup))
        receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
        changed=[]
        try:
            for row in rows:
                s,t=Path(row['source']),Path(row['target'])
                changed.append(row)
                t.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(s,t)
                assert digest(t)==row['after_sha256']
            assert all(digest(Path(p))==sha for p,sha in evidence.items())
            receipt.update(installed=True,phase='complete',audible_owner_acceptance=False,
                known_original_missing_sound_sets=[332],normal_native_sha256=built['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll'])
            receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
        except BaseException:
            for row in reversed(changed):
                t=Path(row['target'])
                if row['before_sha256'] is None:
                    if t.exists():
                        assert digest(t)==row['after_sha256'], 'Unexpected target bytes; retain backup for manual recovery'
                        t.unlink()
                else:
                    shutil.copy2(row['backup'],t)
                    assert digest(t)==row['before_sha256']
            receipt.update(installed=False,phase='rolled_back')
            receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
            raise
    return {'passed':True,'installed':True,'files':len(rows),'database_modified':False,'backup_directory':str(backup)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    print(json.dumps(install(args.workspace.resolve(),args.apply)))
