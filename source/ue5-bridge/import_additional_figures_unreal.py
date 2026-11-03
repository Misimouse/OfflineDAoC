"""Import extra original character figures and clips into new private assets."""
import json,struct,traceback
from pathlib import Path
import unreal

ROOT=Path(__file__).resolve().parent
assets=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
tools=unreal.AssetToolsHelpers.get_asset_tools()
report={'passed':False,'models':{},'errors':[]}
target=ROOT/'Reports/character_lobby/additional_figures_import.json'
target.parent.mkdir(parents=True,exist_ok=True)
try:
    models=json.loads((ROOT/'models.json').read_text(encoding='utf-8-sig'))
    rows=json.loads((ROOT/'SourceAdditionalFigures/exported.json').read_text(encoding='utf-8-sig'))
    for row in rows:
        ident=str(row['id']);raw=Path(row['file']).read_bytes()
        size=struct.unpack_from('<I',raw,12)[0];gltf=json.loads(raw[20:20+size])
        expected=[a['name'] for a in gltf.get('animations',[])]
        assert all(k in expected for k in ['idle','walk','run','death','sit_down','sit_idle','cast_start','cast_mid','cast_end'])
        assert len(gltf.get('skins',[]))==1
        destination='/DAoCVisualBridge/AdditionalFigures_v01/Model_'+ident
        paths=assets.list_assets(destination,recursive=True,include_folder=False)
        if not paths:
            task=unreal.AssetImportTask();task.filename=row['file'];task.destination_path=destination
            task.automated=True;task.save=True;task.replace_existing=False;tools.import_asset_tasks([task])
            paths=assets.list_assets(destination,recursive=True,include_folder=False)
        loaded=[assets.load_asset(p) for p in paths]
        meshes=[a for a in loaded if isinstance(a,unreal.SkeletalMesh)]
        animations={a.get_name():a.get_path_name() for a in loaded if isinstance(a,unreal.AnimSequence)}
        assert len(meshes)==1
        clips={}
        for name in expected:
            found=[p for key,p in animations.items() if key in [name,'model_'+ident+name,'model_'+ident+'_'+name]]
            if len(found)==1:clips[name]=found[0]
            else:assert name=='RESET',('missing original clip',ident,name)
        models[ident]={'asset':meshes[0].get_path_name(),'type':'skeletal','scale':row['scale'],'yaw_offset':-90,'name':row.get('name',ident),**clips}
        report['models'][ident]={'asset':meshes[0].get_path_name(),'original_clips':len(expected),'imported_clips':len(clips),'skeleton':meshes[0].get_editor_property('skeleton').get_path_name()}
    (ROOT/'models_additional_figures_candidate.json').write_text(json.dumps(models,indent=2),encoding='utf-8')
    report['passed']=True
except Exception:report['errors'].append(traceback.format_exc())
target.write_text(json.dumps(report,indent=2),encoding='utf-8');assert report['passed'],report['errors']
