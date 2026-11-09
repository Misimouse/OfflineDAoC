"""Import original ghost-render samples into a private host; no normal catalogue or map writes."""
import json,os,traceback,hashlib
from pathlib import Path
import unreal
lab=Path(os.environ['DAOC_NPC_GHOST_LAB']).resolve();host=lab/'RenderHost';content=host/'Plugins/DAoCVisualBridge/Content';private=content/'GhostAppearance_v01';private.mkdir(exist_ok=True)
assert private.resolve().is_relative_to(host) and not (private.lstat().st_file_attributes & 0x400)
assets=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem);tools=unreal.AssetToolsHelpers.get_asset_tools();report=dict(passed=False,installed=False,models={},materials=[],errors=[],normal_catalogue_modified=False);materials=set()
try:
 for row in json.loads((lab/'SourceModels/exported.json').read_text()):
  ident=str(row['id']);assert ident in ['110','307'];destination='/DAoCVisualBridge/GhostAppearance_v01/Samples/Model_'+ident;paths=assets.list_assets(destination,recursive=True,include_folder=False)
  if not paths:
   task=unreal.AssetImportTask();task.filename=row['file'];task.destination_path=destination;task.automated=True;task.save=True;task.replace_existing=False;tools.import_asset_tasks([task]);paths=assets.list_assets(destination,recursive=True,include_folder=False)
  meshes=[];anims=[]
  for path in paths:
   item=unreal.load_asset(path)
   if isinstance(item,(unreal.SkeletalMesh,unreal.StaticMesh)):meshes.append(item)
   elif isinstance(item,unreal.AnimSequence):anims.append(item)
  assert meshes,ident;mesh=next((x for x in meshes if 'bridge_merged_character' in x.get_name().lower()),meshes[0]);entry=dict(asset=mesh.get_path_name(),type='skeletal' if isinstance(mesh,unreal.SkeletalMesh) else 'static',scale=row['scale'],yaw_offset=-90,name=row['name'])
  for slot in mesh.get_editor_property('materials') if isinstance(mesh,unreal.SkeletalMesh) else mesh.get_editor_property('static_materials'):
   material=slot.get_editor_property('material_interface')
   if material:materials.add(material.get_path_name())
  for key in ['idle','walk','run']:
   clip=next((a for a in anims if key in a.get_name().lower()),None)
   if clip:entry[key]=clip.get_path_name()
  report['models'][ident]=entry
 report['materials']=sorted(materials);assert report['materials'];report['passed']=True
except Exception:report['errors'].append(traceback.format_exc())
(lab/'samples_imported.json').write_text(json.dumps(report,indent=2));assert report['passed'],report['errors']
