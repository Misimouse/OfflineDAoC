"""Prepare a private effect host; production assets are shared read-only and hash-guarded."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
from prepare_combined_expansion_data import digest


def prepare(workspace, engine):
    lab = workspace/'NpcEffectsLab'
    report = json.loads((lab/'Resources/verified.json').read_text())
    assert report['passed'] and report['originals_unchanged']
    normal = workspace/'Client/Plugins/DAoCVisualBridge'
    before = {str(p):digest(p) for p in [workspace/'models.json',normal/'Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll',normal/'Content/SpellVisuals_v01/catalog.json']}
    host = lab/'RenderHost'
    plugin = host/'Plugins/DAoCVisualBridge'
    content = plugin/'Content'
    content.mkdir(parents=True,exist_ok=True)
    quote = lambda p:"'"+str(p).replace("'","''")+"'"
    for original in (normal/'Content').iterdir():
        target = content/original.name
        if original.is_dir():
            if target.exists():
                assert target.is_junction() and target.resolve() == original.resolve()
            else:
                subprocess.run(['powershell.exe','-NoProfile','-Command',
                    'New-Item -ItemType Junction -Path '+quote(target)+' -Target '+quote(original)+' | Out-Null'],
                    check=True,creationflags=subprocess.CREATE_NO_WINDOW)
        elif not target.exists():
            shutil.copy2(original,target)
    private = content/'NpcEffects_v01'
    private.mkdir(exist_ok=True)
    assert not private.is_junction() and private.resolve().is_relative_to(lab.resolve())
    shutil.copytree(lab/'Resources/Data',private/'Data',dirs_exist_ok=True)
    shutil.copy2(lab/'Resources/catalog.json',private/'catalog.json')
    shutil.copy2(normal/'DAoCVisualBridge.uplugin',plugin/'DAoCVisualBridge.uplugin')
    binaries = plugin/'Binaries/Win64'
    binaries.mkdir(parents=True,exist_ok=True)
    assert not binaries.is_junction()
    for name in ['UnrealEditor-DAoCVisualBridge.dll','UnrealEditor.modules']:
        shutil.copy2(normal/'Binaries/Win64'/name,binaries/name)
    project = host/'NpcEffectsHost.uproject'
    project.write_text(json.dumps(dict(FileVersion=3,EngineAssociation='5.8',Plugins=[
        dict(Name='PythonScriptPlugin',Enabled=True),dict(Name='EditorScriptingUtilities',Enabled=True),
        dict(Name='DAoCVisualBridge',Enabled=True)])))
    script = Path(__file__).with_name('import_npc_effect_textures_unreal.py')
    args = [str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),str(project),'-run=pythonscript',
            '-script='+str(script),'-unattended','-nop4','-nosplash','-nullrhi',
            '-forceDisableDebugViewModes','-abslog='+str(lab/'texture_import.log')]
    with (lab/'texture_import_stdout.log').open('w') as log:
        result = subprocess.run(args,env=dict(os.environ,DAOC_NPC_EFFECT_LAB=str(lab)),
            stdout=log,stderr=subprocess.STDOUT,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode == 0,str(lab/'texture_import.log')
    imported = json.loads((lab/'textures_imported.json').read_text())
    assert imported['passed'] and all(digest(Path(p)) == h for p,h in before.items())
    proof = dict(passed=True,installed=False,protected=before,normal_runtime_unchanged=True,
                 resources=report['resource_count'],textures=len(imported['textures']),
                 new_textures=report['new_texture_imports'],project=str(project))
    (lab/'content_verified.json').write_text(json.dumps(proof,indent=2))
    return proof


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--engine',type=Path,required=True)
    options = parser.parse_args()
    print(json.dumps(prepare(options.workspace.resolve(),options.engine.resolve())))
