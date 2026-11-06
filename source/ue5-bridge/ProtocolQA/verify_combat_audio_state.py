"""Verify packet-to-audio decisions in an isolated Godot process without a server."""
import argparse
import json
import os
from pathlib import Path
import subprocess
from prepare_combined_expansion_data import digest


def verify(workspace, install, engine, weapon_mode=False, door_audio=False):
    repo=Path(__file__).resolve().parents[3]
    source=repo/'source/ue5-bridge/Godot'
    assert not (weapon_mode and door_audio)
    root=workspace/('DoorAudioLab/StateTest' if door_audio else 'WeaponModeAudioLab/StateTest' if weapon_mode else 'CombatAudioLab/StateTest')
    root.mkdir(parents=True,exist_ok=True)
    (root/'project.godot').write_text('config_version=5\n',encoding='utf-8')
    sdk=engine/'Binaries/ThirdParty/DotNet/10.0/win-x64'
    env=dict(os.environ,DOTNET_ROOT=str(sdk),DOTNET_ROOT_X64=str(sdk),
        APPDATA=str(root/'AppData'),LOCALAPPDATA=str(root/'LocalAppData'),PATH=str(sdk)+os.pathsep+os.environ['PATH'])
    for key in ['APPDATA','LOCALAPPDATA']:Path(env[key]).mkdir(exist_ok=True)
    godot=install/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'
    script='test_door_audio_state.gd' if door_audio else 'test_weapon_mode_audio_state.gd' if weapon_mode else 'test_combat_audio_state.gd'
    names=['combat_audio_state.gd',script]+(['door_audio_state.gd'] if door_audio else ['weapon_mode_audio_state.gd'] if weapon_mode else [])
    inputs={str(source/name):digest(source/name) for name in names}
    result=subprocess.run([str(godot),'--headless','--path',str(root),'--script',str(source/script)],
        env=env,capture_output=True,text=True,timeout=40,creationflags=subprocess.CREATE_NO_WINDOW)
    (root/'unit.log').write_text(result.stdout+result.stderr,encoding='utf-8')
    assert result.returncode==0 and 'SCRIPT ERROR' not in result.stderr
    row=next(json.loads(line) for line in result.stdout.splitlines() if line.startswith('{'))
    assert row['passed'] and not row.get('failures',[]) and row['checks']>=(16 if door_audio else 15 if weapon_mode else 22)
    assert all(digest(Path(p))==sha for p,sha in inputs.items())
    report={'passed':True,'checks':row['checks'],'server_started':False,'inputs':inputs,'log_sha256':digest(root/'unit.log')}
    (root/'verified.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['workspace','install','engine']:parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--weapon-mode',action='store_true')
    parser.add_argument('--door-audio',action='store_true')
    args=parser.parse_args()
    print(json.dumps(verify(args.workspace.resolve(),args.install.resolve(),args.engine.resolve(),args.weapon_mode,args.door_audio)))
