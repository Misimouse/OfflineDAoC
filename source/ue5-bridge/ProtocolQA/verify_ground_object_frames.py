"""Measure original rigid world-item frames privately; no native content or runtime activation."""
import argparse,json,os,shutil,subprocess
from pathlib import Path
from prepare_combined_expansion_data import digest


def verify(workspace,install,engine):
    source=Path(__file__).resolve().parents[1]
    lab=workspace/'GroundObjectsLab';project=workspace/'ProtocolQA/run-20261102-053353/LobbyProject'
    script=source/'Godot/probe_ground_object_frames.gd';private=lab/script.name
    assert not (lab/'installed.json').exists()
    origin=install/'new-client/godot'
    assert digest(project/'game/weapon_models.gd')==digest(origin/'game/weapon_models.gd')
    assert (project/'content/weapons').resolve()==(origin/'content/weapons').resolve()
    inputs={str(p):digest(p) for p in [script,origin/'game/weapon_models.gd',origin/'content/weapons/weapons.json',workspace/'SourceWeapons_All_v01/exported.json',workspace/'equipment_catalog_v01.json',workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll',lab/'geometry_tasks.json',lab/'geometry_aliases.json']}
    tasks=json.loads((lab/'geometry_tasks.json').read_text());definitions=json.loads((origin/'content/weapons/weapons.json').read_text())['models']
    for task in tasks:
        model=origin/'content/weapons'/definitions[str(task['model'])]['file'];inputs[str(model)]=digest(model)
        gltf=json.loads(model.read_text())
        for buffer in gltf.get('buffers',[]):
            uri=buffer.get('uri','')
            if uri and not uri.startswith('data:'):
                path=(model.parent/uri).resolve();assert path.is_relative_to((origin/'content/weapons').resolve());inputs[str(path)]=digest(path)
    shutil.copy2(script,private)
    sdk=engine/'Binaries/ThirdParty/DotNet/10.0/win-x64'
    env=dict(os.environ,DOTNET_ROOT=str(sdk),DOTNET_ROOT_X64=str(sdk),PATH=str(sdk)+os.pathsep+os.environ['PATH'],APPDATA=str(lab/'ProbeAppData'),LOCALAPPDATA=str(lab/'ProbeLocalAppData'))
    for name in ['APPDATA','LOCALAPPDATA']:Path(env[name]).mkdir(exist_ok=True)
    cmd=[str(install/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'),'--headless','--audio-driver','Dummy','--path',str(project),'--script',str(private),'--',str(lab/'geometry_tasks.json'),str(lab/'geometry_frames.json')]
    with (lab/'geometry_frames.log').open('w',encoding='utf-8') as out:result=subprocess.run(cmd,cwd=lab,env=env,stdout=out,stderr=subprocess.STDOUT,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode==0,str(lab/'geometry_frames.log')
    data=json.loads((lab/'geometry_frames.json').read_text());assert data['passed'] and data['checked_assets']==len(tasks)==918,data.get('failures')
    assert all(digest(Path(p))==sha for p,sha in inputs.items())
    proof=dict(passed=True,source_inputs=inputs,unique_assets=len(tasks),rigid_model_ids=1021,vertices=sum(r['vertices'] for r in data['models'].values()),max_vertex_error_m=max(r['source_vertex_error_m'] for r in data['models'].values()),max_canonical_bounds_error_m=max(r['canonical_bounds_error_m'] for r in data['models'].values()),frames_sha256=digest(lab/'geometry_frames.json'),normal_runtime_modified=False,server_started=False,installed=False)
    (lab/'geometry_verified.json').write_text(json.dumps(proof,indent=2))
    return {k:v for k,v in proof.items() if k!='source_inputs'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['workspace','install','engine']:p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.install.resolve(),a.engine.resolve())))
