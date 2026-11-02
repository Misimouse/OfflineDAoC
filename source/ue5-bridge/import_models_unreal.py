"""Import bridge-owned models into plugin content; never save or change the art map."""
import json
import traceback
from pathlib import Path
import unreal
ROOT=Path(__file__).resolve().parent
assets=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
tools=unreal.AssetToolsHelpers.get_asset_tools()
report={'complete':False,'models':{},'errors':[],'stage':'starting'}
target=ROOT/'Reports/model_import.json'
def write():target.write_text(json.dumps(report,indent=2))
try:
    data=json.loads((ROOT/'SourceModels/exported.json').read_text())
    catalog={}
    for row in data:
        ident=row['id'];destination='/DAoCVisualBridge/ModelsTextured_v03/Model_'+ident
        report['stage']='importing '+ident;write()
        existing=assets.list_assets(destination,recursive=True,include_folder=False)
        if not existing:
            task=unreal.AssetImportTask();task.filename=row['file'];task.destination_path=destination
            task.automated=True;task.save=True;task.replace_existing=False
            tools.import_asset_tasks([task])
            existing=assets.list_assets(destination,recursive=True,include_folder=False)
        skeletal=[];static=[];animations=[]
        for path in existing:
            item=assets.load_asset(path)
            if isinstance(item,unreal.SkeletalMesh):skeletal.append(item)
            elif isinstance(item,unreal.StaticMesh):static.append(item)
            elif isinstance(item,unreal.AnimSequence):animations.append(item)
        if not skeletal and not static:raise RuntimeError('No mesh imported for '+ident)
        chosen=next((s for s in skeletal if 'bridge_merged_character' in s.get_name().lower()),skeletal[0] if skeletal else static[0])
        entry=dict(asset=chosen.get_path_name(),type='skeletal' if skeletal else 'static',
                   scale=row['scale'],yaw_offset=-90,name=row['name'])
        for key in ['idle','walk','run']:
            found=next((a for a in animations if key in a.get_name().lower()),None)
            if found:entry[key]=found.get_path_name()
        catalog[ident]=entry;report['models'][ident]=entry
        (ROOT/'models.json').write_text(json.dumps(catalog,indent=2));write()
    aliases=json.loads((ROOT/'SourceModels/aliases.json').read_text())
    for ident,base in aliases.items():
        if base in catalog:catalog[ident]=dict(catalog[base],shared_base=base)
    # These native IDs are effects/invisible emitters, not missing humanoids.
    for ident in ['667','966','2020']:catalog[ident]=dict(type='hidden')
    # Temporary local player representation until its exact equipment is exported.
    if '310' in catalog:catalog['0']=dict(catalog['310'],name='Local player race preview')
    elif '1984' in catalog:catalog['0']=dict(catalog['1984'],name='Local player race preview')
    (ROOT/'models.json').write_text(json.dumps(catalog,indent=2))
    report.update(complete=True,stage='complete',catalog_entries=len(catalog));write()
except Exception:
    report['errors'].append(traceback.format_exc());write();raise
