"""Observe a disposable native world handoff; never start a normal server."""
import json
from pathlib import Path
import subprocess
import time


def read(path):
    raw=path.read_bytes()
    return json.loads(raw.decode('utf-16' if raw[:2] in [b'\xff\xfe',b'\xfe\xff'] else 'utf-8-sig'))


def start(workspace,install,engine,output):
    workspace,install,engine,output=(Path(p).resolve() for p in [workspace,install,engine,output])
    assert output.is_relative_to(workspace/'Reports/combined_expansions')
    review=workspace/'ExpansionRaceLab/MinotaurOwnerReview'
    project=workspace/'ExpansionRaceLab/SharLobbyHost/SharLobbyHost.uproject'
    for name in ['native_world.json','world_observed.json','native_world.png']:(output/name).unlink(missing_ok=True)
    command=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),str(project),
             '/Game/DAoC/Connacht_v01/Ardee_Nwiro_Prueba_Limpieza_v01','-game','-EnablePlugins=DAoCVisualBridge',
             '-DaocBridge','-DaocBridgePort=19737','-DaocBridgeAutoTest','-DaocBridgeNavigationProbe',
             '-DaocBridgeCatalog='+str(review/'models.json'),'-DaocBridgeEquipmentCatalog='+str(review/'equipment_catalog.json'),
             '-DaocBridgeLobbyAppearance='+str(review/'appearance_catalog.json'),
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
