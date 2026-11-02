import unreal,json,traceback
from pathlib import Path
R=Path(__file__).resolve().parent;assets=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem);tools=unreal.AssetToolsHelpers.get_asset_tools();report={'passed':False,'errors':[]}
try:
 entries={}
 for row in json.loads((R/'SourcePetModels_v01/exported.json').read_text()):
  dest='/DAoCVisualBridge/PetModels_v01/Model_'+row['id']
  found=assets.list_assets(dest,recursive=True,include_folder=False)
  if not found:
   t=unreal.AssetImportTask();t.filename=row['file'];t.destination_path=dest;t.automated=True;t.save=True;tools.import_asset_tasks([t]);found=assets.list_assets(dest,recursive=True,include_folder=False)
  objects=[assets.load_asset(p)for p in found];skeletal=[x for x in objects if isinstance(x,unreal.SkeletalMesh)];static=[x for x in objects if isinstance(x,unreal.StaticMesh)];assert skeletal or static
  mesh=next((x for x in skeletal if 'merged' in x.get_name().lower()),skeletal[0] if skeletal else static[0]);entry={'asset':mesh.get_path_name(),'type':'skeletal' if skeletal else 'static','scale':row['scale'],'yaw_offset':-90,'name':row['name']}
  for a in objects:
   if isinstance(a,unreal.AnimSequence):
    name=a.get_name();clip=name.removeprefix('model_'+row['id']).removeprefix('_');entry[clip]=a.get_path_name()
  assert all(k in entry for k in ['idle','walk','run','death','attack_med']),(row['id'],list(entry))
  entries[row['id']]=entry
 report.update(passed=True,entries=entries)
except Exception:report['errors'].append(traceback.format_exc())
(R/'Reports/training_staff_fx_pets/pet_models_import.json').write_text(json.dumps(report,indent=2));assert report['passed'],report['errors']
