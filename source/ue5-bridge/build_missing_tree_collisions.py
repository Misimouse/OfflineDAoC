import unreal,json,hashlib,traceback
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/remote_collision';report={'passed':False,'models':{},'errors':[]}
try:
 A=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem);T=unreal.AssetToolsHelpers.get_asset_tools();E=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
 data=json.loads((R/'collision_catalog.json').read_text(encoding='utf-8'));audit=json.loads((D/'scene_audit.json').read_text(encoding='utf-8'));sources=sorted({r['asset'] for r in audit['rows'] if r['tree'] and not r['known']})
 for path in sources:
  source=A.load_asset(path);assert source,path
  slots=list(source.get_editor_property('static_materials'));trunk=[i for i,m in enumerate(slots) if any(k in (str(m.material_slot_name)+' '+(m.material_interface.get_name() if m.material_interface else '')).lower() for k in ['bark','trunk','corteza','wood'])]
  assert trunk,('No explicit trunk material',path,[(str(m.material_slot_name),m.material_interface.get_name() if m.material_interface else '') for m in slots])
  dm=unreal.DynamicMesh();read=unreal.GeometryScriptMeshReadLOD();read.lod_type=unreal.GeometryScriptLODType.RENDER_DATA;read.lod_index=0
  _,result=unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(source,dm,unreal.GeometryScriptCopyMeshFromAssetOptions(),read,use_section_materials=False);assert 'SUCCESS' in str(result).upper(),str(result)
  for i in range(len(slots)):
   if i not in trunk:unreal.GeometryScript_Materials.delete_triangles_by_material_id(dm,i)
  name='NC_'+source.get_name()[:48]+'_'+hashlib.sha256(path.encode()).hexdigest()[:8];target='/DAoCVisualBridge/NavigationCollision_v02/'+name
  mesh=A.load_asset(target) if A.does_asset_exist(target) else T.duplicate_asset(name,'/DAoCVisualBridge/NavigationCollision_v02',A.load_asset('/Engine/BasicShapes/Cube.Cube'));assert mesh
  options=unreal.GeometryScriptCopyMeshToAssetOptions();options.replace_materials=True;options.new_materials=[m.material_interface for m in slots];write=unreal.GeometryScriptMeshWriteLOD();write.lod_index=0
  _,result=unreal.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dm,mesh,options,write);assert 'SUCCESS' in str(result).upper(),str(result)
  body=mesh.get_editor_property('body_setup');body.set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE);body.set_editor_property('double_sided_geometry',True)
  for section in range(mesh.get_num_sections(0)):E.enable_section_collision(mesh,True,0,section)
  assert mesh.get_num_triangles(0)>0
  A.save_loaded_asset(mesh,only_if_is_dirty=False)
  entry={'kind':'tree','shape':'mesh','asset':mesh.get_path_name(),'triangles':mesh.get_num_triangles(0),'trunk_only':True};data['models'][path]=entry;report['models'][path]=entry
  (D/'tree_collision_build.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 (R/'collision_catalog.json').write_text(json.dumps(data,indent=2),encoding='utf-8');report['passed']=True
except Exception:report['errors'].append(traceback.format_exc())
(D/'tree_collision_build.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
if not report['passed']:raise RuntimeError(report['errors'])
print('PRIVATE_NEW_TREE_COLLISIONS_BUILT',len(report['models']))
