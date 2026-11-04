"""Reimport only original hair meshes whose bound morph targets were lost. No activation."""
import os,json,hashlib,re,traceback,sys
from pathlib import Path
import unreal
R=Path(os.environ['DAOC_CHARACTER_LAB']);sys.path.insert(0,str(Path(__file__).resolve().parent))
from densify_appearance_morphs import densify,moving_morph_names
A=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem);T=unreal.AssetToolsHelpers.get_asset_tools()
C=json.loads((R/'appearance_catalog_colour_candidate.json').read_text());audit=json.loads(Path(os.environ.get('DAOC_MORPH_AUDIT',R/'Reports/all_hair_morph_audit/native.json')).read_text(encoding='utf-8-sig'));source=json.loads(Path(os.environ.get('DAOC_APPEARANCE_EXPORT',R.parent/'SourceAppearance/exported.json')).read_text())
rows={str(v['base_id']):v for v in source['races'].values()};report={'passed':False,'installed':False,'repairs':{},'errors':[]}
try:
    for base,part in sorted({(v['base_id'],v['part']) for v in audit['missing_facial_morph_targets']}):
        original=C['figures'][base]['parts'][part];src=rows[base]['parts'][part];source_file=Path(src['file']);source_sha=hashlib.sha256(source_file.read_bytes()).hexdigest();file=R/'DenseMorphSources'/(base+'_'+part+'.glb');dense_report=densify(source_file,file);sha=hashlib.sha256(file.read_bytes()).hexdigest();dest='/DAoCVisualBridge/AppearanceMorph_v03/'+C['figures'][base]['race']+'/'+part+'_'+sha[:12]
        existing=A.list_assets(dest,recursive=True,include_folder=False)
        if not existing:
            pipeline=unreal.InterchangeGenericAssetsPipeline();pipeline.get_editor_property('mesh_pipeline').set_editor_property('morph_threshold_position',0.0)
            overrides=unreal.InterchangePipelineStackOverride();overrides.add_pipeline(pipeline)
            task=unreal.AssetImportTask();task.filename=str(file);task.destination_path=dest;task.automated=True;task.save=True;task.replace_existing=False;task.options=overrides;T.import_asset_tasks([task]);existing=A.list_assets(dest,recursive=True,include_folder=False)
        meshes=[A.load_asset(p) for p in existing if 'SkeletalMesh' in str(A.find_asset_data(p).asset_class_path)];assert len(meshes)==1,(base,part,existing);mesh=meshes[0];old=unreal.load_asset(original['asset']);assert old
        old_mod=unreal.SkeletonModifier();new_mod=unreal.SkeletonModifier();assert old_mod.set_skeletal_mesh(old) and new_mod.set_skeletal_mesh(mesh)
        normal=lambda n:re.sub(r'[-_ ]','',str(n)).lower();bones={normal(n):n for n in old_mod.get_all_bone_names()};assert len(bones)==len(new_mod.get_all_bone_names())
        for name in new_mod.get_all_bone_names():
            assert normal(name) in bones;before=old_mod.get_bone_transform(bones[normal(name)],True);after=new_mod.get_bone_transform(name,True);assert before.translation.distance(after.translation)<.1,(base,part,'bone position',str(name));assert abs(sum(getattr(before.rotation,v)*getattr(after.rotation,v) for v in ['x','y','z','w']))>.99999,(base,part,'bone rotation',str(name))
        morphs=[m.get_name() for m in mesh.get_editor_property('morph_targets')];moving,empty=moving_morph_names(source_file);assert moving<=set(morphs)<=set(src['morphs']),(base,part,morphs,sorted(moving));assert set(src['morphs'])-set(morphs)<=empty
        skeleton=mesh.get_editor_property('skeleton');skeleton.add_compatible_skeleton(old.get_editor_property('skeleton'));A.save_loaded_asset(skeleton)
        report['repairs'][base+'/'+part]={'before':original['asset'],'candidate':mesh.get_path_name(),'source_sha256':source_sha,'dense_sha256':sha,'dense_verification':dense_report,'morph_threshold_position':0,'bones_checked':len(bones),'morphs':morphs,'empty_source_morphs':sorted(empty)}
        original['asset']=mesh.get_path_name();original['morphs']=src['morphs'];original['imported_morphs']=morphs;original['empty_source_morphs']=sorted(empty);original['morph_threshold_position']=0
    (R/'appearance_catalog_visual_candidate.json').write_text(json.dumps(C,indent=2),encoding='utf-8');report['passed']=True
except Exception:report['errors'].append(traceback.format_exc())
(R/'morph_reimport_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');assert report['passed'],report['errors']
