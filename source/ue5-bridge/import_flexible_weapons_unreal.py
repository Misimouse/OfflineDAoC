import unreal,json,traceback
from pathlib import Path
R=Path(__file__).resolve().parent;assets=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem);tools=unreal.AssetToolsHelpers.get_asset_tools();report={'passed':False,'entries':{},'errors':[]}
try:
 unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(['/DAoCVisualBridge/FlexibleWeapons_v02'],True)
 source=json.loads((R/'equipment_catalog_v01.json').read_text())['models']
 tasks={int(t['model']):t for t in json.loads((R/'SourceFlexibleWeapons_v01/tasks.json').read_text())}
 measured=json.loads((R/'Reports/equipment/all_import.json').read_text())['models']
 report['measurements']={}
 for row in json.loads((R/'SourceFlexibleWeapons_v01/exported.json').read_text()):
  ident=str(int(row['model']));dest='/DAoCVisualBridge/FlexibleWeapons_v02/Model_'+ident
  found=assets.list_assets(dest,recursive=True,include_folder=False)
  if not found:
   task=unreal.AssetImportTask();task.filename=row['file'];task.destination_path=dest;task.automated=True;task.save=True;tools.import_asset_tasks([task]);found=assets.list_assets(dest,recursive=True,include_folder=False)
  objects=[assets.load_asset(p)for p in found];meshes=[x for x in objects if isinstance(x,unreal.SkeletalMesh)];assert len(meshes)==1,[(x.get_name(),x.get_class().get_name())for x in objects]
  mesh=meshes[0];entry=dict(source[ident]);entry.update(asset=mesh.get_path_name(),type='skeletal')
  clips={}
  for a in objects:
   if isinstance(a,unreal.AnimSequence):
    clip=next((k for k in sorted(row['animations'],key=len,reverse=True) if a.get_name().endswith(k)),None)
    if clip:clips[clip]=a.get_path_name()
  assert all(k in clips for k in ['idle','combat_idle','attack_high','attack_low']),list(clips)
  entry['complete_bone_tracks']=bool(row['complete_bone_tracks']);entry['animations']=clips;entry['posed_attack_bounds_cm']=[[p[0]*100,p[2]*100,p[1]*100]for p in row['posed_attack_bounds_m']];entry['attack_sample_s']=row['attack_sample_s'];entry['posed_idle_bounds_cm']=[[p[0]*100,p[2]*100,p[1]*100]for p in row['posed_idle_bounds_m']];report['entries'][ident]=entry
  modifier=unreal.SkeletonModifier();assert modifier.set_skeletal_mesh(mesh);bounds=mesh.get_bounds()
  envelope=[[p[0]*100,p[2]*100,p[1]*100]for p in row['conservative_bounds_m']]
  lower=[bounds.origin.x-bounds.box_extent.x,bounds.origin.y-bounds.box_extent.y,bounds.origin.z-bounds.box_extent.z];upper=[bounds.origin.x+bounds.box_extent.x,bounds.origin.y+bounds.box_extent.y,bounds.origin.z+bounds.box_extent.z]
  positive=[max(0,envelope[1][i]-upper[i])for i in range(3)];negative=[max(0,lower[i]-envelope[0][i])for i in range(3)]
  mesh.set_editor_property('positive_bounds_extension',unreal.Vector(*positive));mesh.set_editor_property('negative_bounds_extension',unreal.Vector(*negative));assets.save_loaded_asset(mesh)
  entry['animation_envelope_cm']=envelope
  expected=measured[str(tasks[int(ident)]['export_id'])]['bounds_cm'];actual=[[bounds.origin.x-bounds.box_extent.x,bounds.origin.y-bounds.box_extent.y,bounds.origin.z-bounds.box_extent.z],[bounds.origin.x+bounds.box_extent.x,bounds.origin.y+bounds.box_extent.y,bounds.origin.z+bounds.box_extent.z]]
  error=max(abs(actual[a][b]-expected[a][b])for a in range(2)for b in range(3)) # Rest bounds can legitimately differ from the animated idle pose.
  report['measurements'][ident]={'bounds_max_error_cm':error,'bone_count':len(modifier.get_all_bone_names()),'bounds_origin_cm':[bounds.origin.x,bounds.origin.y,bounds.origin.z],'bounds_extent_cm':[bounds.box_extent.x,bounds.box_extent.y,bounds.box_extent.z],'clips':list(clips)}
 report['passed']=True
except Exception:report['errors'].append(traceback.format_exc())
(R/'Reports/training_staff_fx_pets/flexible_import.json').write_text(json.dumps(report,indent=2));assert report['passed'],report['errors']
