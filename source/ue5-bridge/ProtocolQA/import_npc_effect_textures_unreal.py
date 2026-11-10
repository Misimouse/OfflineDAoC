"""Import only missing original NPC effect textures into a private versioned folder."""
import json
import os
from pathlib import Path
import traceback
import unreal

lab = Path(os.environ['DAOC_NPC_EFFECT_LAB']).resolve()
resources = lab/'Resources'
output = dict(passed=False,installed=False,textures=[],errors=[])
try:
    entries = json.loads((resources/'textures_to_import.json').read_text())
    assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(['/DAoCVisualBridge'],False)
    tasks = []
    for key, source in entries.items():
        assert len(key) == 20 and all(c in '0123456789abcdef' for c in key)
        target = '/DAoCVisualBridge/NpcEffects_v01/Textures/T_'+key
        assert not assets.does_asset_exist(target), 'Candidate texture already exists: '+target
        task = unreal.AssetImportTask()
        task.filename = source
        task.destination_path = '/DAoCVisualBridge/NpcEffects_v01/Textures'
        task.destination_name = 'T_'+key
        task.automated = True
        task.save = True
        tasks.append(task)
    tools.import_asset_tasks(tasks)
    catalog = json.loads((resources/'catalog.json').read_text())
    for key, path in catalog['textures'].items():
        texture = unreal.load_asset(path)
        assert isinstance(texture,unreal.Texture2D),path
        output['textures'].append(dict(key=key,asset=path,reused=key not in entries))
    output['passed'] = True
except Exception:
    output['errors'].append(traceback.format_exc())
(lab/'textures_imported.json').write_text(json.dumps(output,indent=2))
assert output['passed'],output['errors']
