"""Import original morph-capable heads/hair into a candidate library, without activation."""
import os,hashlib,json,re,traceback
from pathlib import Path
import unreal,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from densify_appearance_morphs import densify,moving_morph_names
R=Path(os.environ.get('DAOC_BRIDGE_WORKSPACE',Path(__file__).resolve().parent));D=R/'Reports/appearance';D.mkdir(parents=True,exist_ok=True)
A=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem);T=unreal.AssetToolsHelpers.get_asset_tools();library=os.environ.get('DAOC_APPEARANCE_LIBRARY','/DAoCVisualBridge/Appearance_v02')
assert library.startswith('/DAoCVisualBridge/') and '..' not in library
expected_figures=int(os.environ.get('DAOC_APPEARANCE_EXPECTED_FIGURES','10'));expected_parts=int(os.environ.get('DAOC_APPEARANCE_EXPECTED_PARTS','62'))
assert expected_figures>0 and expected_parts>=expected_figures
report={'passed':False,'installed':False,'parts':{},'errors':[],'active_catalogues_changed':False}
def write():(D/'import_parts.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
try:
 guarded=[R/'models.json',R/'equipment_catalog_v01.json'];before=[hashlib.sha256(p.read_bytes()).hexdigest() for p in guarded]
 models=json.loads(guarded[0].read_text(encoding='utf-8-sig'));manifest=json.loads((R/'SourceAppearance/exported.json').read_text());assert manifest['complete'] and not manifest['missing_textures']
 normal=lambda n:re.sub(r'[-_ ]','',str(n)).lower();catalog={'version':1,'activated':False,'figures':{}}
 unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous([library],True)
 for race,row in manifest['races'].items():
  body=unreal.load_asset(models[str(row['base_id'])]['asset']);source=unreal.SkeletonModifier();assert source.set_skeletal_mesh(body);bones={normal(n):n for n in source.get_all_bone_names()};figure={'race':race,'meta':row['meta'],'parts':{}}
  for part,data in row['parts'].items():
   key=race+'/'+part;source_file=Path(data['file']);sha=hashlib.sha256(source_file.read_bytes()).hexdigest();dense_file=R/'AppearanceDenseSources'/race/(part+'.glb');dense_report=densify(source_file,dense_file);dense_sha=hashlib.sha256(dense_file.read_bytes()).hexdigest();dest=library+'/'+race+'/'+part+'_'+dense_sha[:12]
   existing=A.list_assets(dest,recursive=True,include_folder=False)
   if not existing:
    pipeline=unreal.InterchangeGenericAssetsPipeline();pipeline.get_editor_property('mesh_pipeline').set_editor_property('morph_threshold_position',0.0);overrides=unreal.InterchangePipelineStackOverride();overrides.add_pipeline(pipeline)
    task=unreal.AssetImportTask();task.filename=str(dense_file);task.destination_path=dest;task.automated=True;task.save=True;task.replace_existing=False;task.options=overrides;T.import_asset_tasks([task]);existing=A.list_assets(dest,recursive=True,include_folder=False)
   meshes=[A.load_asset(p) for p in existing if 'SkeletalMesh' in str(A.find_asset_data(p).asset_class_path)];assert len(meshes)==1,(key,len(meshes));mesh=meshes[0]
   morphs=[m.get_name() for m in mesh.get_editor_property('morph_targets')];moving,empty=moving_morph_names(source_file);assert moving<=set(morphs)<=set(data['morphs']),(key,'nonzero morph targets changed',morphs,sorted(moving));assert set(data['morphs'])-set(morphs)<=empty
   target=unreal.SkeletonModifier();assert target.set_skeletal_mesh(mesh)
   for name in target.get_all_bone_names():
    assert normal(name) in bones,(key,'missing leader bone',str(name));a=source.get_bone_transform(bones[normal(name)],True);b=target.get_bone_transform(name,True)
    assert a.translation.distance(b.translation)<.1,(key,'reference position mismatch',str(name))
    assert abs(sum(getattr(a.rotation,v)*getattr(b.rotation,v) for v in ['x','y','z','w']))>.99999,(key,'reference rotation mismatch',str(name))
   skeleton=mesh.get_editor_property('skeleton');skeleton.add_compatible_skeleton(body.get_editor_property('skeleton'));A.save_loaded_asset(skeleton)
   entry={'asset':mesh.get_path_name(),'morphs':data['morphs'],'imported_morphs':morphs,'empty_source_morphs':sorted(empty),'source_sha256':sha,'dense_sha256':dense_sha,'dense_verification':dense_report,'hair_style':data.get('hair_style'),'facial_morphs':data.get('facial_morphs',{}),'material_slots':[str(m.material_slot_name) for m in mesh.get_editor_property('materials')]}
   figure['parts'][part]=entry;report['parts'][key]=entry
   if len(report['parts'])%10==0:write();unreal.SystemLibrary.collect_garbage()
  catalog['figures'][str(row['base_id'])]=figure
 assert len(catalog['figures'])==expected_figures and len(report['parts'])==expected_parts
 assert before==[hashlib.sha256(p.read_bytes()).hexdigest() for p in guarded]
 (R/'appearance_catalog_candidate.json').write_text(json.dumps(catalog,indent=2),encoding='utf-8');report['figures']=expected_figures;report['morph_targets']=sum(len(p['morphs']) for p in report['parts'].values());report['passed']=True
except Exception:report['errors'].append(traceback.format_exc())
write();assert report['passed'],report['errors']
