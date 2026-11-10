"""Verify original incoming private templates and actual Server.command routing without live accounts."""
import argparse,json,os,shutil,subprocess
from pathlib import Path
from prepare_combined_expansion_data import digest
from verify_ground_object_state import function

def verify(workspace,install,engine):
    source=Path(__file__).resolve().parents[1]/'Godot';lab=workspace/'ChatReplyLab';lab.mkdir(exist_ok=True);project=lab/'StateProject';project.mkdir(exist_ok=True)
    (lab/'Reports/chat_channels').mkdir(parents=True,exist_ok=True)
    original=install/'new-client/godot/game/net/server.gd';dol=source.parents[1]/'server/GameServer/gameobjects/GamePlayer.cs';language=dol.parents[1]/'language/EN/GameObjects/GamePlayer.txt'
    assert 'Social.ReceiveMessage.Private.Sends' in dol.read_text() and '{0} sends, "{1}"' in language.read_text(encoding='utf-8-sig')
    inputs={str(p):digest(p) for p in list(source.glob('*.gd'))+[original,dol,language]}
    for p in source.glob('*.gd'):shutil.copy2(p,project/p.name)
    (project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Private chat reply QA"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n')
    (project/'original_chat_reference.gd').write_text('extends Node\nvar client:Node\nvar playing:=true\nvar entry:={"zone":207}\n'+function(original.read_text(encoding='utf-8-sig'),'command'))
    sdk=engine/'Binaries/ThirdParty/DotNet/10.0/win-x64';env=dict(os.environ,DOTNET_ROOT=str(sdk),DOTNET_ROOT_X64=str(sdk),PATH=str(sdk)+os.pathsep+os.environ['PATH'],APPDATA=str(lab/'appdata'),LOCALAPPDATA=str(lab/'localappdata'))
    for k in ['APPDATA','LOCALAPPDATA']:Path(env[k]).mkdir(exist_ok=True)
    reports=[]
    for name in ['test_chat_reply_state.gd','test_chat_state.gd']:
        r=subprocess.run([str(install/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'),'--headless','--audio-driver','Dummy','--path',str(project),'--script','res://'+name],env=env,capture_output=True,text=True,timeout=35,creationflags=subprocess.CREATE_NO_WINDOW)
        text=r.stdout+r.stderr;(lab/(name+'.log')).write_text(text,encoding='utf-8');assert r.returncode==0 and 'ERROR:' not in text,str(lab/(name+'.log'))
        data=json.loads(next(l for l in text.splitlines() if l.startswith('{')));assert data['passed'] and data['checks']>=20,data;reports.append(dict(test=name,checks=data['checks']))
    assert all(digest(Path(p))==h for p,h in inputs.items())
    data=dict(passed=True,reports=reports,source_inputs=inputs,original_command_executed=True,server_started=False,installed=False);(lab/'state_tests.json').write_text(json.dumps(data,indent=2));return {k:v for k,v in data.items() if k!='source_inputs'}

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ['workspace','install','engine']:p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.install.resolve(),a.engine.resolve())))
