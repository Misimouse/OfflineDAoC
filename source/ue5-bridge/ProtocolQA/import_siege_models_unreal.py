"""Import only the ten original siege models into a private content namespace."""
import hashlib,json,traceback
from pathlib import Path
import unreal
root=Path(__file__).resolve().parent;assert root.name=='SiegeWorldLab'
private=Path(unreal.Paths.project_plugins_dir()).resolve()/'DAoCVisualBridge/Content/SiegeWorld_v01'
assert private.resolve().is_relative_to(root.resolve()) and not (getattr(private.lstat(),"st_file_attributes",0)&1024)
assets=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem);tools=unreal.AssetToolsHelpers.get_asset_tools()
report=dict(passed=False,models={},errors=[],normal_content_modified=False,normal_catalogue_modified=False)
def vec(v):return [v.x,v.y,v.z]
try:
 for row in json.loads((root/'SourceModels/exported.json').read_text()):
  ident=row['id'];dest='/DAoCVisualBridge/SiegeWorld_v01/Model_'+ident
  paths=assets.list_assets(dest,recursive=True,include_folder=False)
  # This namespace is private and physically isolated; reimport corrected exports only here.
  task=unreal.AssetImportTask();task.filename=row['file'];task.destination_path=dest;task.automated=True;task.save=True;task.replace_existing=True;tools.import_asset_tasks([task]);paths=assets.list_assets(dest,recursive=True,include_folder=False)
  objects=[assets.load_asset(p) for p in paths];skeletal=[x for x in objects if isinstance(x,unreal.SkeletalMesh)];static=[x for x in objects if isinstance(x,unreal.StaticMesh)]
  meshes=skeletal if row['animated'] else static;assert len(meshes)==1,(ident,'Expected one complete body',len(meshes))
  mesh=meshes[0];entry=dict(asset=mesh.get_path_name(),type='skeletal' if row['animated'] else 'static',scale=1.0,yaw_offset=row['yaw_offset'],name=row['name'],siege=True)
  for obj in objects:
   if isinstance(obj,unreal.AnimSequence):
    clip=obj.get_name().removeprefix('model_'+ident).removeprefix('_')
    if clip in row['clips']:
     assert abs(obj.get_play_length()-row['clips'][clip])<.05,(ident,clip,'clip duration mismatch')
     entry[clip]=obj.get_path_name()
  assert all(k in entry for k in row['clips']),(ident,'Missing original clip',entry)
  bounds=mesh.get_bounds();actual=[vec(bounds.origin-bounds.box_extent),vec(bounds.origin+bounds.box_extent)]
  expected=[[p[0]*100,p[2]*100,p[1]*100] for p in row['bounds_m']]
  error=max(abs(actual[a][b]-expected[a][b]) for a in range(2) for b in range(3))
  if not row['animated']:assert error<.2,(ident,'Static geometry coordinate mismatch',actual,expected)
  assert .3<max(actual[1][j]-actual[0][j] for j in range(3))/100<30,(ident,'Unreasonable original world size',actual)
  report['models'][ident]=dict(entry=entry,bounds_cm=actual,expected_bounds_cm=expected,bounds_max_error_cm=error,original_vertices=row['vertices'],original_clips=row['clips'])
 report.update(passed=True,files={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in private.rglob('*') if p.is_file()})
except Exception:report['errors'].append(traceback.format_exc());raise
finally:(root/'asset_import.json').write_text(json.dumps(report,indent=2))
