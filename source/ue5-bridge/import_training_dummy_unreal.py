import unreal,json,traceback
from pathlib import Path
R=Path(__file__).resolve().parent;assets=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem);tools=unreal.AssetToolsHelpers.get_asset_tools();report={'passed':False,'errors':[]}
try:
 row=json.loads((R/'SourceTrainingDummy_v01/exported.json').read_text())[0];dest='/DAoCVisualBridge/TrainingDummy_v01'
 found=assets.list_assets(dest,recursive=True,include_folder=False)
 if not found:
  t=unreal.AssetImportTask();t.filename=row['file'];t.destination_path=dest;t.automated=True;t.save=True;tools.import_asset_tasks([t]);found=assets.list_assets(dest,recursive=True,include_folder=False)
 objects=[assets.load_asset(p)for p in found];skeletal=[x for x in objects if isinstance(x,unreal.SkeletalMesh)];static=[x for x in objects if isinstance(x,unreal.StaticMesh)];assert skeletal or static
 mesh=next((x for x in skeletal if 'merged' in x.get_name().lower()),skeletal[0] if skeletal else static[0]);entry={'asset':mesh.get_path_name(),'type':'skeletal' if skeletal else 'static','scale':row['scale'],'yaw_offset':-90,'name':'Original training dummy'}
 for clip in ['idle','flinch']:
  a=next((x for x in objects if isinstance(x,unreal.AnimSequence) and clip in x.get_name().lower()),None)
  if a:entry[clip]=a.get_path_name()
 report.update(passed=True,entry=entry)
except Exception:report['errors'].append(traceback.format_exc())
(R/'Reports/training_staff_fx_pets/dummy_import.json').write_text(json.dumps(report,indent=2));assert report['passed'],report['errors']
