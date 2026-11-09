"""Export original siege scene geometry/clips in an isolated Godot project; no normal catalogue edits."""
import argparse,json,os,subprocess
from pathlib import Path
from prepare_combined_expansion_data import digest
IDS=['2598','2599','2600','2601','2602','2604','2605','2606','2607','2645']
def prepare(workspace,install,engine):
    root=workspace/'SiegeWorldLab';out=root/'SourceModels';out.mkdir(parents=True,exist_ok=True)
    base=install/'new-client/godot/content/weapons';meta_path=base/'weapons.json';meta=json.loads(meta_path.read_text())['models'];inputs={str(meta_path):digest(meta_path)};tasks=[]
    for ident in IDS:
        row=meta[ident];path=base/row.get('anim_file',row['file']);assert path.is_file();inputs[str(path)]=digest(path);doc=json.loads(path.read_text())
        for image in doc.get('images',[]):
            uri=image.get('uri','')
            if not uri or uri.startswith('data:'):continue
            image_path=(path.parent/uri).resolve();assert image_path.is_relative_to(base.resolve()) and image_path.is_file();inputs[str(image_path)]=digest(image_path)
        tasks.append(dict(id=ident,file=str(path),name=row['name'],animated='anim_file' in row))
    (out/'tasks.json').write_text(json.dumps(tasks,indent=2))
    source=Path(__file__).resolve().parents[1]/'Godot/export_siege_models.gd';inputs[str(source)]=digest(source)
    for name in ['export_pet_models.gd']:
        p=source.with_name(name);inputs[str(p)]=digest(p)
    for name in ['nif_scene.gd','nif_materials.gd','nif_particles.gd','weapon_models.gd']:
        p=install/'new-client/godot/game'/name;inputs[str(p)]=digest(p)
    prepared=json.loads((workspace/'Reports/protocol_qa/prepared.json').read_text());project=Path(prepared['root'])/'LobbyProject';assert project.resolve().is_relative_to(workspace/'ProtocolQA')
    sdk=engine/'Binaries/ThirdParty/DotNet/10.0/win-x64';env=dict(os.environ,DOTNET_ROOT=str(sdk),DOTNET_ROOT_X64=str(sdk),APPDATA=str(root/'appdata'))
    args=[str(install/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'),'--headless','--path',str(project),'--script',str(source),'--','--output-folder='+str(out)]
    with (root/'export.log').open('w',encoding='utf-8') as log:result=subprocess.run(args,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=150,creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode==0 and 'ERROR:' not in (root/'export.log').read_text(encoding='utf-8'),'See SiegeWorldLab/export.log'
    rows=json.loads((out/'exported.json').read_text());assert [r['id'] for r in rows]==IDS
    assert all(r['vertices']>0 and Path(r['file']).is_file() and (not r['animated'] or 'fire' in r['clips']) for r in rows)
    from restore_siege_idle import restore
    idle={}
    for row in rows:
        if row['animated']:idle[row['id']]=restore(base/meta[row['id']]['anim_file'],Path(row['file']),row['clips']['idle'])
    inputs[str(Path(__file__).with_name('restore_siege_idle.py'))]=digest(Path(__file__).with_name('restore_siege_idle.py'))
    assert all(digest(Path(p))==h for p,h in inputs.items())
    proof=dict(passed=True,source_inputs=inputs,exported_sha256=digest(out/'exported.json'),models=len(rows),animated_models=sum(r['animated'] for r in rows),normal_runtime_modified=False,normal_catalogue_modified=False,idle_preservation=idle)
    (root/'export_verified.json').write_text(json.dumps(proof,indent=2));return {k:v for k,v in proof.items() if k!='source_inputs'}
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ['workspace','install','engine']:p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();print(json.dumps(prepare(a.workspace.resolve(),a.install.resolve(),a.engine.resolve())))
