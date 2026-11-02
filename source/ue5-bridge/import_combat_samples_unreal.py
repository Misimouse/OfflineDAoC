"""Import new private samples only; do not activate them or save a map."""
import json,traceback
from pathlib import Path
import unreal
R=Path(__file__).resolve().parent;O=R/'Reports/player_state/combat_import.json'
assets=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem);tools=unreal.AssetToolsHelpers.get_asset_tools()
report={'complete':False,'models':{},'errors':[]}
def save():O.write_text(json.dumps(report,indent=2))
try:
 proof=json.loads((R/'Reports/player_state/combat_export_verification.json').read_text());assert proof['passed']
 for row in json.loads((R/'SourceModelsCombat_v01/exported.json').read_text()):
  ident=row['id'];destination='/DAoCVisualBridge/ModelsCombat_v01/Model_'+ident
  existing=assets.list_assets(destination,recursive=True,include_folder=False)
  if not existing:
   task=unreal.AssetImportTask();task.filename=row['file'];task.destination_path=destination;task.automated=True;task.save=True;task.replace_existing=False;tools.import_asset_tasks([task]);existing=assets.list_assets(destination,recursive=True,include_folder=False)
  meshes=[];animations={};other=[]
  for path in existing:
   item=assets.load_asset(path)
   if isinstance(item,unreal.SkeletalMesh):meshes.append(item.get_path_name())
   elif isinstance(item,unreal.AnimSequence):animations[item.get_name()]=item.get_path_name()
   else:other.append(path)
  assert meshes and animations,'Missing imported mesh or animations for '+ident
  expected=proof['models'][ident]['animations'];mapped={}
  for clip in expected:
   # Interchange prefixes the animation with its original model stem.
   candidates=[path for name,path in animations.items()if name==f'model_{ident}{clip}' or name==f'model_{ident}_{clip}' or name==clip]
   if len(candidates)==1:mapped[clip]=candidates[0]
  missing=[c for c in expected if c!='RESET' and c not in mapped]
  report['models'][ident]={'meshes':meshes,'animations':mapped,'unmapped':missing,'all_animation_assets':animations,'other_count':len(other),'active':False};save();assert not missing,'Unmapped animations '+str(missing)
 report['complete']=True;save()
except Exception:
 report['errors'].append(traceback.format_exc());save();raise
