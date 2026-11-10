"""Verify ground-object lifecycle and actual original pickup/relic protocol functions privately."""
import argparse,json,os,shutil,subprocess,textwrap
from pathlib import Path
from prepare_combined_expansion_data import digest


def function(text,name):
    start=text.index('func '+name+'(')
    return text[start:].split('\n\n\n',1)[0].expandtabs(4)+'\n'


def verify(workspace,install,engine):
    source=Path(__file__).resolve().parents[1]
    lab=workspace/'GroundObjectsLab';project=lab/'StateProject';project.mkdir(exist_ok=True)
    (project/'project.godot').write_text('[application]\nconfig/name="Private ground object state QA"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n')
    paths=[source/'Godot'/n for n in ['ground_object_state.gd','interaction_state.gd','test_ground_object_state.gd']]
    paths += [install/'new-client/godot/game/net/server_world.gd',install/'new-client/godot/game/net/server.gd',source.parent/'server/GameServer/packets/Client/168/PlayerPickUpRequestHandler.cs']
    normal=workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll';paths.append(normal);inputs={str(p):digest(p) for p in paths}
    for path in paths[:3]:shutil.copy2(path,project/path.name)
    world=paths[3].read_text(encoding='utf-8-sig');server=paths[4].read_text(encoding='utf-8-sig');dol=paths[5].read_text(encoding='utf-8-sig')
    assert 'GameObject target = client.Player.TargetObject;' in dol and 'client.Player.PickupObject(target, false);' in dol
    wrapper='extends RefCounted\nconst RELIC_MODELS := [630,631,632,633,634,635]\nclass SourceServer extends RefCounted:\n    var client:Node\n    func zone_info(_id:int)->Dictionary:return {"x":35,"y":51}\n'
    wrapper+=textwrap.indent(function(server,'to_region'),'    ')
    wrapper+='var Server=SourceServer.new()\nvar objects:Dictionary={}\nvar target_object:=0\nvar player:Node3D\nfunc _current_zone()->int:return 207\nfunc setup(c:Node,p:Node3D,oid:int,model:int)->void:\n    Server.client=c;player=p;target_object=oid\n    if objects.has(oid):objects[oid].free()\n    var holder:=Node3D.new();holder.set_meta("model",model);objects[oid]=holder\nfunc close()->void:\n    for holder in objects.values():holder.free()\n    objects.clear()\n'
    wrapper+=function(world,'get_object');(project/'original_ground_reference.gd').write_text(wrapper)
    sdk=engine/'Binaries/ThirdParty/DotNet/10.0/win-x64';env=dict(os.environ,DOTNET_ROOT=str(sdk),DOTNET_ROOT_X64=str(sdk),PATH=str(sdk)+os.pathsep+os.environ['PATH'],APPDATA=str(lab/'StateAppData'),LOCALAPPDATA=str(lab/'StateLocalAppData'))
    for key in ['APPDATA','LOCALAPPDATA']:Path(env[key]).mkdir(exist_ok=True)
    exe=install/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'
    cmd=[str(exe),'--headless','--audio-driver','Dummy','--path',str(project),'--script','res://test_ground_object_state.gd']
    r=subprocess.run(cmd,cwd=lab,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
    (lab/'state_tests.log').write_text(r.stdout,encoding='utf-8');assert r.returncode==0 and 'ERROR:' not in r.stdout,r.stdout
    proof=json.loads((project/'verified.json').read_text());assert proof['passed'] and proof['checks']>=60 and proof['original_get_object_executed'],proof
    assert all(digest(Path(p))==sha for p,sha in inputs.items())
    proof.update(source_inputs=inputs,original_reference_sha256=digest(project/'original_ground_reference.gd'),server_started=False)
    (lab/'state_tests.json').write_text(json.dumps(proof,indent=2));return {k:v for k,v in proof.items() if k!='source_inputs'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['workspace','install','engine']:p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.install.resolve(),a.engine.resolve())))
