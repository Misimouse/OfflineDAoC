"""Stage original horse sound set 41 and original helper hoof-contact timing privately."""
import argparse,importlib.util,io,json,os,subprocess,sys
from contextlib import redirect_stdout
from pathlib import Path
from prepare_combined_expansion_data import digest

def prepare(workspace,install,engine):
    repo=Path(__file__).resolve().parents[3];root=workspace/'LiveRidingLab';assert not (root/'installed.json').exists()
    pipeline=repo/'source/new-client/pipeline/build_sounds.py';os.environ['DAOC_CLIENT']=str(install/'runtime/client-opendaoc/app');sys.path.insert(0,str(pipeline.parent))
    spec=importlib.util.spec_from_file_location('original_riding_audio',pipeline);builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
    original=builder.creature_sets;sheet=original()[41];assert sheet['move_dirt']=='g_Gallop_OnDirt'
    builder.creature_sets=lambda:{41:{k:v for k,v in sheet.items() if k in ['name','move_dirt']}}
    builder.ROOT=root/'AudioScratch';(builder.ROOT/'godot/content').mkdir(parents=True,exist_ok=True);builder.OUT=root/'OriginalRidingAudio_v01';builder.OUT.mkdir(exist_ok=True)
    with redirect_stdout(io.StringIO()):missing=builder.export(set(),set(),creature_set_ids=[41])
    assert not missing,missing
    prepared=json.loads((workspace/'Reports/protocol_qa/prepared.json').read_text());qa=Path(prepared['root']);assert qa.is_relative_to(workspace/'ProtocolQA')
    output=root/'HoofContacts';output.mkdir(exist_ok=True)
    sdk=engine/'Binaries/ThirdParty/DotNet/10.0/win-x64';env=dict(os.environ,DOTNET_ROOT=str(sdk),DOTNET_ROOT_X64=str(sdk),PATH=str(sdk)+os.pathsep+os.environ['PATH'],APPDATA=str(output/'AppData'),LOCALAPPDATA=str(output/'LocalAppData'))
    for key in ['APPDATA','LOCALAPPDATA']:Path(env[key]).mkdir(exist_ok=True)
    script=repo/'source/ue5-bridge/Godot/export_original_riding_contacts.gd';source=root/'SourceModels/model_448.glb';helper=qa/'LobbyProject/game/character_sounds.gd'
    inputs={str(p):digest(p) for p in [pipeline,script,source,helper]}
    exe=install/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'
    command=[str(exe),'--headless','--path',str(qa/'LobbyProject'),'--script',str(script),'--','--riding-source='+str(source),'--riding-contacts='+str(output/'contacts.json')]
    run=subprocess.run(command,env=env,capture_output=True,text=True,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW);text=run.stdout+run.stderr;(output/'godot.log').write_text(text,encoding='utf-8')
    assert run.returncode==0 and 'ORIGINAL_RIDING_CONTACTS_PASS' in text and 'ERROR:' not in text,text
    contacts=json.loads((output/'contacts.json').read_text());assert contacts['passed'] and contacts['model']==448
    for row in contacts['contacts'].values():assert row['length']>0 and row['contacts']==sorted(set(row['contacts'])) and all(0<=t<row['length'] for t in row['contacts'])
    catalog=builder.OUT/'sounds.json';index=json.loads(catalog.read_text());index['mounted_models']={'448':dict(sound_set=41,contacts=contacts['contacts'])};catalog.write_text(json.dumps(index,indent=2),encoding='utf-8')
    files={str(builder.OUT/row['file']):digest(builder.OUT/row['file']) for row in index['named'].values()};assert len(files)==4
    originals={}
    for path,sha in files.items():
        original=Path(builder._find(Path(path).name));assert original.is_file() and digest(original)==sha
        originals[str(original)]=sha
    inputs.update(originals)

    assert all(digest(Path(p))==sha for p,sha in inputs.items())
    result=dict(passed=True,private_only=True,catalog=str(catalog),catalog_sha256=digest(catalog),files=files,original_files=originals,input_hashes=inputs,contacts=contacts['contacts'],normal_installation_modified=False)
    (root/'audio_resources.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return dict(passed=True,original_wavs=len(files),contacts=contacts['contacts'],normal_installation_modified=False)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['workspace','install','engine']:p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();print(json.dumps(prepare(a.workspace.resolve(),a.install.resolve(),a.engine.resolve())))
