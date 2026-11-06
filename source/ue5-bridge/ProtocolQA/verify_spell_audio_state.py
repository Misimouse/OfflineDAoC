"""Run original event metadata checks without a game/server autoload."""
import argparse
import json
import os
from pathlib import Path
import subprocess
from prepare_combined_expansion_data import digest


def verify(workspace, install, engine):
    repo=Path(__file__).resolve().parents[3]
    source=repo/'source/ue5-bridge/Godot'
    root=workspace/'SpellAudioLab/StateTest'
    root.mkdir(parents=True,exist_ok=True)
    (root/'project.godot').write_text('config_version=5\n',encoding='utf-8')
    sdk=engine/'Binaries/ThirdParty/DotNet/10.0/win-x64'
    env=dict(os.environ,DOTNET_ROOT=str(sdk),DOTNET_ROOT_X64=str(sdk),
        APPDATA=str(root/'AppData'),LOCALAPPDATA=str(root/'LocalAppData'),PATH=str(sdk)+os.pathsep+os.environ['PATH'])
    for key in ['APPDATA','LOCALAPPDATA']:Path(env[key]).mkdir(exist_ok=True)
    godot=install/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'
    inputs={str(source/name):digest(source/name) for name in ['spell_visual_state.gd','test_spell_audio_state.gd']}
    result=subprocess.run([str(godot),'--headless','--path',str(root),'--script',str(source/'test_spell_audio_state.gd')],
        env=env,capture_output=True,text=True,timeout=40,creationflags=subprocess.CREATE_NO_WINDOW)
    (root/'unit.log').write_text(result.stdout+result.stderr,encoding='utf-8')
    assert result.returncode==0 and 'SPELL_AUDIO_STATE_PASS' in result.stdout
    assert 'SCRIPT ERROR' not in result.stderr
    assert all(digest(Path(p))==sha for p,sha in inputs.items())
    report={'passed':True,'server_started':False,'inputs':inputs,'log_sha256':digest(root/'unit.log')}
    (root/'verified.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['workspace','install','engine']:parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(verify(args.workspace.resolve(),args.install.resolve(),args.engine.resolve())))
