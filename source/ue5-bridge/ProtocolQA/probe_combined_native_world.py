"""Observe a disposable native world handoff; never start a normal server."""
import json
import hashlib
from pathlib import Path
import subprocess
import time


def read(path):
    raw=path.read_bytes()
    return json.loads(raw.decode('utf-16' if raw[:2] in [b'\xff\xfe',b'\xfe\xff'] else 'utf-8-sig'))


def start(workspace,install,engine,output,installed=False):
    workspace,install,engine,output=(Path(p).resolve() for p in [workspace,install,engine,output])
    assert output.is_relative_to(workspace/'Reports/combined_expansions') or (installed and output==workspace/'Reports/central_minotaur_world')
    review=workspace/'ExpansionRaceLab/MinotaurOwnerReview'
    project=workspace/'ExpansionRaceLab/SharLobbyHost/SharLobbyHost.uproject'
    models, equipment, appearance = review/'models.json', review/'equipment_catalog.json', review/'appearance_catalog.json'
    if installed:
        plugin=workspace/'Client/Plugins/DAoCVisualBridge'
        host=workspace/'ExpansionRaceLab/CentralInstalledHost'
        project=host/'CentralInstalledHost.uproject'
        assert (host/'Content').is_junction() and (host/'Content').resolve()==(workspace.parent/'DAoC-Enhanced-Unreal/Content').resolve()
        assert (host/'Plugins/DAoCVisualBridge/Content').is_junction() and (host/'Plugins/DAoCVisualBridge/Content').resolve()==(plugin/'Content').resolve()
        digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        for name in ['UnrealEditor-DAoCVisualBridge.dll','UnrealEditor.modules']:
            assert digest(host/'Plugins/DAoCVisualBridge/Binaries/Win64'/name)==digest(plugin/'Binaries/Win64'/name)
        activation=json.loads((workspace/'ExpansionRaceLab/CentralDelivery/MinotaurActivation/installed.json').read_text())
        assert activation['installed'] and activation['only_race_enabled']==21
        assert all(digest(Path(row['target']))==row['after_sha256'] for row in activation['files'])
        models,equipment,appearance=workspace/'models.json',workspace/'equipment_catalog_v01.json',plugin/'Content/ClassicUI/Pregame/appearance_catalog.json'
        paths=[models,equipment,appearance,plugin/'Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll']
        (output/'installed_inputs.json').write_text(json.dumps({str(p):digest(p) for p in paths},indent=2),encoding='utf-8')
    for name in ['native_world.json','world_observed.json','native_world.png']:(output/name).unlink(missing_ok=True)
    command=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),str(project),
             '/Game/DAoC/Connacht_v01/Ardee_Nwiro_Prueba_Limpieza_v01','-game','-EnablePlugins=DAoCVisualBridge',
             '-DaocBridge','-DaocBridgePort=19737','-DaocBridgeAutoTest','-DaocBridgeNavigationProbe',
             '-DaocBridgeCatalog='+str(models),'-DaocBridgeEquipmentCatalog='+str(equipment),
             '-DaocBridgeLobbyAppearance='+str(appearance),
             '-DaocBridgeHeights='+str(install/'new-client/godot/content/zones/zone207/heights.f32'),
             '-DaocBridgeQuality=balanced','-DaocBridgeReport='+str(output/'native_world.json'),
             '-DaocBridgeCapture='+str(output/'native_world.png'),'-unattended','-nosound','-nosplash','-d3d11',
             '-RenderOffscreen','-windowed','-ResX=1600','-ResY=900','-abslog='+str(output/'native_engine.log')]
    for flag,name in [('CollisionCatalog','collision_catalog.json'),('EnvironmentCatalog','environment_catalog.json'),('FoliageCatalog','foliage_lods.json')]:
        if (workspace/name).exists():command.append('-DaocBridge'+flag+'='+str(workspace/name))
    # The engine has its own private absolute log; no credential-bearing command
    # line or process output is published by this observer.
    return subprocess.Popen(command,cwd=project.parent,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)


def observe(process,output,character,gateway=None):
    deadline=time.monotonic()+240
    observed=None
    while time.monotonic()<deadline:
        try:
            value=read(output/'native_world.json')
            gm=value.get('player_status',{}).get('gm_mode',{})
            if (gm.get('ready') and not gm.get('combat_test') and not gm.get('uncertain') and not gm.get('pending')
                and value.get('connected') and value.get('character')==character
                and value.get('map')=='Ardee_Nwiro_Prueba_Limpieza_v01'
                and value.get('navigation_ready') and value.get('test_elapsed',0)>2):
                observed=value
                (output/'world_observed.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
        except (OSError,ValueError):pass
        if gateway is not None and gateway.poll() is not None and observed is None:
            raise RuntimeError('Disposable gateway closed before native world connection')
        if process.poll() is not None:break
        time.sleep(.25)
    if process.poll() is None:raise RuntimeError('Disposable native world did not close normally')
    assert process.returncode==0 and observed,'Native world was not observed connected and navigable'
    image=output/'native_world.png'
    assert image.is_file() and image.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
    return {'passed':True,'real_native_world':True,'map':observed['map'],
            'navigation_ready':True,'gm_protected_confirmed':True,'normal_native_exit':True,'capture':str(image)}
