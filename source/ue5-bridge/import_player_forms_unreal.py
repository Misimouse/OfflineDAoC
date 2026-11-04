"""Import original player-form art into separate plugin resources. No map/catalogue is overwritten."""
import json,os
from pathlib import Path
import unreal

root=Path(os.environ['DAOC_BRIDGE_WORKSPACE'])
folder=root/'SourcePlayerForms_v01'
assets=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
tools=unreal.AssetToolsHelpers.get_asset_tools()
exported=json.loads((folder/'exported.json').read_text());assert len(exported)==1 and exported[0]['id']=='1883'
destination='/DAoCVisualBridge/PlayerForms_v01/Bainshee'
paths=assets.list_assets(destination,recursive=True,include_folder=False)
if not paths:
    task=unreal.AssetImportTask();task.filename=exported[0]['file'];task.destination_path=destination
    task.automated=True;task.save=True;task.replace_existing=False;tools.import_asset_tasks([task])
    paths=assets.list_assets(destination,recursive=True,include_folder=False)
objects=[assets.load_asset(path) for path in paths]
meshes=[x for x in objects if isinstance(x,unreal.SkeletalMesh)];assert len(meshes)==1
clips={}
for item in objects:
    if isinstance(item,unreal.AnimSequence):
        name=item.get_name().removeprefix('model_1883').removeprefix('_')
        clips[name]=item.get_path_name()
assert all(k in clips for k in ['idle','walk','run','death','attack_med']),list(clips)
entries={}
for original in json.loads((folder/'forms.json').read_text()):
    entry={'asset':meshes[0].get_path_name(),'type':'skeletal','scale':original['info']['scale'],'yaw_offset':-90,'name':original['info']['name'],**clips}
    for name,clip in original['info'].get('cast_clips',{}).items():
        assert clip in clips,clip
        entry[name]=clips[clip]
    entries[original['id']]=entry
assert set(entries)=={'1883','1884','1885'}
catalog=json.loads((root/'models.json').read_text())
for key,entry in entries.items():
    assert key not in catalog or catalog[key]==entry,'Review existing player form before replacing'
    catalog[key]=entry
(folder/'models_candidate.json').write_text(json.dumps(catalog,indent=2),encoding='utf-8')
report={'passed':True,'map_saved':False,'installed_catalogue':False,'entries':entries,'animations':len(clips)}
(root/'Reports/appearance/player_forms_import.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('PLAYER_FORMS_IMPORTED original_forms=3 map_saved=False')
