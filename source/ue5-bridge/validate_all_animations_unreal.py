"""Preserve existing materials on new meshes and validate imported skeleton links."""
import json,traceback
from pathlib import Path
import unreal
R=Path(__file__).resolve().parent;O=R/'Reports/pose_animations/asset_validation.json'
assets=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
result={'passed':False,'models':{},'errors':[],'catalog_changed':False,'map_saved':False}
try:
 imported=json.loads((R/'Reports/pose_animations/import.json').read_text());assert imported['complete']
 catalog=json.loads((R/'models.json').read_text());candidate=json.loads(json.dumps(catalog))
 for ident,row in imported['models'].items():
  assert len(row['meshes'])==1
  mesh=unreal.load_asset(row['meshes'][0]);original=unreal.load_asset(catalog[ident]['asset']);assert mesh and original,'Missing source or sample mesh';skeleton=mesh.get_editor_property('skeleton')
  materials=original.get_editor_property('materials');assert len(materials)==len(mesh.get_editor_property('materials'))
  mesh.set_editor_property('materials',materials);assets.save_loaded_asset(mesh)
  validated=[]
  for name,path in row['animations'].items():
   clip=unreal.load_asset(path);assert clip.get_editor_property('skeleton')==skeleton,name
   assert clip.get_play_length()>0,name
   validated.append({'clip':name,'seconds':clip.get_play_length()})
  candidate[ident]=dict(catalog[ident],asset=mesh.get_path_name(),**row['animations'])
  result['models'][ident]={'material_paths':[str(m.material_interface.get_path_name())if m.material_interface else None for m in materials],'validated_clips':validated,'skeleton':skeleton.get_path_name(),'active':False}
 for ident,base in json.loads((R/'SourceModels/aliases.json').read_text()).items():
  if base in imported['models'] and ident in candidate:candidate[ident]=dict(candidate[ident],asset=candidate[base]['asset'],**imported['models'][base]['animations'])
 candidate['0']=dict(candidate['1984'])
 (R/'models_combat_samples.json').write_text(json.dumps(candidate,indent=2))
 (R/'models_animations_v02.json').write_text(json.dumps(candidate,indent=2))
 result['passed']=True
except Exception:result['errors'].append(traceback.format_exc());raise
finally:O.write_text(json.dumps(result,indent=2))
