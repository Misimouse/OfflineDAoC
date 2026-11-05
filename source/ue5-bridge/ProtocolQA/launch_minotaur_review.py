"""Run only the independent Minotaur owner-review copy; never use the normal DB."""
import argparse
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import time
import xml.etree.ElementTree as ET


def wait_until(predicate, seconds, label):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        if predicate():return
        time.sleep(.25)
    raise RuntimeError(label)


def main(root, install, engine, smoke=False, smoke_world=False):
    root,install,engine=(p.resolve() for p in (root,install,engine))
    assert root.name=='MinotaurOwnerReview' and root.parent.name=='ExpansionRaceLab'
    assert json.loads((root/'prepared.json').read_text())['prepared']
    config=json.loads((root/'private_review_config.json').read_text())
    assert config['server_port']==10361 and config['bridge_port']==19747
    tasks=json.loads((root/'SourceModels/tasks.json').read_text())
    assert any(row.get('info',{}).get('race')=='mino' and str(row['id'])=='1419' for row in tasks), 'Minotaur world mapping is required'
    assert '1419' in json.loads((root/'models.json').read_text())
    database=root/'runtime/data/review.sqlite3.db'
    node=ET.parse(root/'runtime/server/config/serverconfig.xml').getroot().find('Server')
    assert str(database) in node.find('DBConnectionString').text
    assert node.find('Port').text=='10361' and node.find('IP').text=='127.0.0.1'
    with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True) as db:
        assert db.execute('SELECT RunId FROM CodexQaIsolationMarker').fetchone()[0]==config['run_id']
        character=db.execute('SELECT Name FROM DOLCharacters WHERE AccountName=? AND Race=21 ORDER BY Class LIMIT 1',(config['account'],)).fetchone()[0]
    reservations=[]
    try:
        for port in [10361,19747]:
            reservation=socket.socket();reservation.bind(('127.0.0.1',port));reservations.append(reservation)
    finally:
        for reservation in reservations:reservation.close()
    sdk=engine/'Binaries/ThirdParty/DotNet/10.0/win-x64'
    env=dict(os.environ,DOTNET_ROOT=str(sdk),DOTNET_ROOT_X64=str(sdk),PATH=str(sdk)+os.pathsep+os.environ.get('PATH',''),APPDATA=str(root/'AppData'),LOCALAPPDATA=str(root/'LocalAppData'))
    reports=root/'Reports/live';reports.mkdir(parents=True,exist_ok=True)
    logout=reports/'logout.request';logout.unlink(missing_ok=True)
    state=reports/'godot_session.json';state.unlink(missing_ok=True)
    if smoke or smoke_world:
        for name in ['unreal_session.json','world_observed.json','live_menu.json','ArdeeMinotaur.png']:
            (reports/name).unlink(missing_ok=True)
    server=client=unreal=None
    with (reports/'server.log').open('w') as server_log, (reports/'gateway.log').open('w') as gateway_log, (reports/'unreal.log').open('w') as unreal_log:
        try:
            server=subprocess.Popen([str(sdk/'dotnet.exe'),str(root/'runtime/server/CoreServer.dll'),'--start'],cwd=root/'runtime/server',env=env,stdin=subprocess.PIPE,stdout=server_log,stderr=subprocess.STDOUT,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
            def server_ready():
                if server.poll() is not None:raise RuntimeError('Private server did not start')
                try:
                    with socket.create_connection(('127.0.0.1',10361),timeout=.2):return True
                except OSError:return False
            wait_until(server_ready,60,'Private server timeout')
            command=[str(install/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'),'--headless','--path',str(root/'GodotProject'),'--script',str(root/'Godot/gateway_main.gd'),'--','--server=127.0.0.1','--server-port=10361','--account='+config['account'],'--password='+config['password'],'--no-world']
            command.append('--bridge-character='+character if smoke_world else '--bridge-character-menu')
            client=subprocess.Popen(command,cwd=root,env=env,stdout=gateway_log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            def client_ready():
                if client.poll() is not None:raise RuntimeError('Private gateway did not start')
                try:
                    value=json.loads(state.read_text())
                    return (value.get('playing') and value.get('player_prefix')=='mino') if smoke_world else value.get('character_lobby',{}).get('ready')
                except (OSError,ValueError):return False
            wait_until(client_ready,90,'Private login timeout')
            lab=root.parent;workspace=lab.parent
            project=lab/'SharLobbyHost/SharLobbyHost.uproject'
            map_name='/Engine/Maps/Entry' if smoke else '/Game/DAoC/Connacht_v01/Ardee_Nwiro_Prueba_Limpieza_v01'
            command=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe' if smoke or smoke_world else engine/'Binaries/Win64/UnrealEditor.exe'),str(project),map_name,'-game','-EnablePlugins=DAoCVisualBridge','-DaocBridge','-DaocBridgePort=19747','-windowed','-ResX=1600','-ResY=900','-d3d11','-nosplash','-DaocBridgeCatalog='+str(root/'models.json'),'-DaocBridgeEquipmentCatalog='+str(root/'equipment_catalog.json'),'-DaocBridgeLobbyAppearance='+str(root/'appearance_catalog.json'),'-DaocBridgeLobbyLore='+str(lab/'Delivery/lore.json'),'-DaocBridgeHeights='+str(install/'new-client/godot/content/zones/zone207/heights.f32'),'-DaocBridgeQuality=balanced','-DaocBridgeReport='+str(reports/'unreal_session.json')]
            for flag,file in [('CollisionCatalog','collision_catalog.json'),('EnvironmentCatalog','environment_catalog.json'),('FoliageCatalog','foliage_lods.json')]:
                if (workspace/file).exists():command.append('-DaocBridge'+flag+'='+str(workspace/file))
            if smoke:command+=['-unattended','-nosound','-RenderOffscreen','-DaocBridgeCharacterLobbyLiveProbe='+str(reports/'live_menu.json')]
            if smoke_world:command+=['-unattended','-nosound','-RenderOffscreen','-DaocBridgeAutoTest','-DaocBridgeNavigationProbe','-DaocBridgeCapture='+str(reports/'ArdeeMinotaur.png')]
            print('Opening isolated Minotaur review. Use the four existing level 5 characters.',flush=True)
            unreal=subprocess.Popen(command,cwd=project.parent,stdout=unreal_log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            if smoke_world:
                def world_ready():
                    if unreal.poll() is not None:raise RuntimeError('Review world closed before validation')
                    try:
                        raw=(reports/'unreal_session.json').read_bytes()
                        value=json.loads(raw.decode('utf-16' if raw[:2] in [b'\xff\xfe',b'\xfe\xff'] else 'utf-8-sig'))
                        ready=(value.get('connected') and value.get('character')==character
                               and value.get('map')=='Ardee_Nwiro_Prueba_Limpieza_v01'
                               and value.get('navigation_ready') and value.get('test_elapsed',0)>2)
                        if ready:(reports/'world_observed.json').write_text(json.dumps(value,indent=2))
                        return ready
                    except (OSError,ValueError):return False
                wait_until(world_ready,240,'Private world did not become playable')
            unreal.wait(timeout=300 if smoke or smoke_world else None)
            assert unreal.returncode==0
            if smoke:
                raw=(reports/'live_menu.json').read_bytes();result=json.loads(raw.decode('utf-16' if raw[:2] in [b'\xff\xfe',b'\xfe\xff'] else 'utf-8-sig'))
                assert result['passed'] and result['characters']==4 and not result['world_entered']
                print('Live private character menu passed.',flush=True)
        finally:
            if unreal and unreal.poll() is None and (smoke or smoke_world):
                unreal.terminate();unreal.wait(timeout=20)
            logout.write_text('logout',encoding='utf-8')
            try:
                if client and client.poll() is None:client.wait(timeout=90)
            finally:
                if server and server.poll() is None:
                    server.stdin.write('exit\n');server.stdin.flush();server.wait(timeout=60)
            assert not client or client.returncode==0
            assert not server or server.returncode==0
    print('Private session saved and closed. Normal installation unchanged.',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['root','install','engine']:parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--smoke',action='store_true')
    parser.add_argument('--smoke-world',action='store_true')
    args=parser.parse_args()
    assert not(args.smoke and args.smoke_world)
    main(args.root,args.install,args.engine,args.smoke,args.smoke_world)
