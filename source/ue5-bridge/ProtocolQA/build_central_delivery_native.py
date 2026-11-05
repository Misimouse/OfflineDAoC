"""Build a separate central-delivery acceptance host without changing earlier test binaries."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--workspace', type=Path, required=True)
parser.add_argument('--engine', type=Path, required=True)
args = parser.parse_args()
workspace, engine = args.workspace.resolve(), args.engine.resolve()
lab = workspace/'ExpansionRaceLab'
repo = Path(__file__).resolve().parents[3]
build_host = lab/'StarterNativeBuild/HostProject'
build_plugin = build_host/'Plugins/DAoCVisualBridge'
target_host = lab/'CentralDeliveryHost'
target_plugin = target_host/'Plugins/DAoCVisualBridge'
target_plugin.mkdir(parents=True, exist_ok=True)
assert build_plugin.resolve().is_relative_to(lab) and target_host.resolve().is_relative_to(lab)
quote = lambda value: "'"+str(value).replace("'", "''")+"'"
for target, source in [(target_host/'Content', lab/'SharLobbyHost/Content'),
                       (target_plugin/'Content', lab/'SharLobbyHost/Plugins/DAoCVisualBridge/Content')]:
    if target.exists():
        assert target.is_junction() and target.resolve() == source.resolve()
    else:
        subprocess.run(['powershell.exe', '-NoProfile', '-Command',
                        'New-Item -ItemType Junction -Path '+quote(target)+' -Target '+quote(source)+' | Out-Null'],
                       check=True, creationflags=subprocess.CREATE_NO_WINDOW)
shutil.copy2(lab/'SharLobbyHost/Plugins/DAoCVisualBridge/DAoCVisualBridge.uplugin', target_plugin/'DAoCVisualBridge.uplugin')
project = target_host/'CentralDeliveryHost.uproject'
project.write_text(json.dumps({'FileVersion': 3, 'EngineAssociation': '5.8',
                              'Plugins': [{'Name': 'DAoCVisualBridge', 'Enabled': True}]}), encoding='utf-8')
shutil.copytree(repo/'source/ue5-bridge/UnrealPlugin/DAoCVisualBridge/Source', build_plugin/'Source', dirs_exist_ok=True)
command = [str(engine/'Build/BatchFiles/Build.bat'), 'UnrealEditor', 'Win64', 'Development',
           '-Project='+str(build_host/'HostProject.uproject'), '-Plugin='+str(build_plugin/'DAoCVisualBridge.uplugin'),
           '-WaitMutex', '-NoHotReload', '-DisableLiveCoding']
with (lab/'central_delivery_native_build.log').open('w', encoding='utf-8') as log:
    result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=600,
                            creationflags=subprocess.CREATE_NO_WINDOW)
assert result.returncode == 0, 'See private central_delivery_native_build.log'
binary_target = target_plugin/'Binaries/Win64'
binary_target.mkdir(parents=True, exist_ok=True)
for source in (build_plugin/'Binaries/Win64').iterdir():
    if source.suffix in ['.dll', '.modules']:
        shutil.copy2(source, binary_target/source.name)
print(json.dumps({'passed': True, 'project': str(project), 'normal_binary_modified': False}))
