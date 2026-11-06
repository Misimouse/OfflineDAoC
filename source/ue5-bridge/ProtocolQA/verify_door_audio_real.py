"""Exercise acknowledged doors using only the existing marked disposable server."""
import argparse
from contextlib import closing
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import traceback

parser=argparse.ArgumentParser(description=__doc__)
for key in ['workspace','install']:parser.add_argument('--'+key,type=Path,required=True)
parser.add_argument('--native',action='store_true')
parser.add_argument('--crossing',action='store_true')
parser.add_argument('--footsteps',action='store_true')
args=parser.parse_args();workspace=args.workspace.resolve();repo=Path(__file__).resolve().parents[3]
assert not args.crossing or args.native
assert not args.footsteps or (args.native and args.crossing)
os.environ['DAOC_INSTALL']=str(args.install.resolve());sys.path.insert(0,str(workspace/'ProtocolQA'))
from qa_runtime import ROOT,RUN,SERVER,DB,env,dotnet,ENGINE
assert ROOT.resolve()==workspace and DB.is_relative_to(RUN) and RUN.is_relative_to(workspace/'ProtocolQA')
output=workspace/('Reports/footstep_audio_real_protocol' if args.footsteps else 'Reports/door_audio_real_protocol')/datetime.now().strftime('%Y%m%d-%H%M%S-%f');output.mkdir(parents=True)
result={'passed':False,'disposable_only':True,'checks':{},'errors':[]};server=client=peer=relay=None;logs=[];backed=False
session='';snapshot={};buffer=b'';serial=0;trace=[];states=[];motion=[]
config=RUN/'bridge_config.json';config_before=config.read_bytes()
digest=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
source=repo/'source/ue5-bridge/Godot';inputs={str(p):digest(p) for p in source.glob('*.gd')}

def checked():
    db=sqlite3.connect(DB);db.row_factory=sqlite3.Row
    assert db.execute('SELECT RunId FROM CodexQaIsolationMarker').fetchone()[0]==RUN.name
    return db

def send(action,**values):
    global serial
    serial+=1;peer.sendall((json.dumps(dict(type='command',session=session,id='doorqa:'+str(serial),action=action,**values))+'\n').encode())

def pump():
    global session,snapshot,buffer
    try:data=peer.recv(1048576)
    except socket.timeout:return
    if not data:raise RuntimeError('Private door bridge closed')
    buffer+=data
    while b'\n' in buffer:
        line,buffer=buffer.split(b'\n',1);value=json.loads(line)
        if value.get('type')=='hello':session=value['session']
        if value.get('type')=='snapshot':
            snapshot=value
            if args.crossing and relay:
                current=relay.read_report()
                if current.get('door_auto_test') and (not motion or current.get('test_elapsed')!=motion[-1].get('test_elapsed')):motion.append(current)
            for event in value.get('combat_audio',[]):
                if event.get('sheet')=='doors' and not any(row['seq']==event['seq'] for row in trace):trace.append(event)
            for row in value.get('doors',[]):
                if not states or row not in states[-2:]:states.append(row)

def wait(test,label,seconds=25):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        pump()
        if test():return
    raise RuntimeError(label)

def settle(seconds):
    end=time.monotonic()+seconds
    while time.monotonic()<end:pump()

try:
    for kind,port in [(socket.SOCK_STREAM,10351),(socket.SOCK_DGRAM,10451),(socket.SOCK_STREAM,19737)]:
        with socket.socket(socket.AF_INET,kind) as guard:
            guard.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1);guard.bind(('127.0.0.1',port))
    with closing(checked()) as db:
        with closing(sqlite3.connect(output/'before.sqlite3.db')) as backup:db.backup(backup)
        backed=True;char=db.execute("SELECT * FROM DOLCharacters WHERE Name='Codexdruid'").fetchone();assert char
        db.execute('UPDATE Account SET PrivLevel=3,Realm=3 WHERE Name=?',(char['AccountName'],))
        # Fixture only. This does not relocate or change an owner character.
        db.execute("UPDATE DOLCharacters SET Class=53,Level=5,Region=200,Xpos=?,Ypos=?,Zpos=?,Health=200,DeathTime=0,HasGravestone=0 WHERE Name='Codexdruid'",(round(1375.4*40)+35*8192,round(1250.6*40)+51*8192,5200))
        db.commit()
    cfg=json.loads(config_before);cfg['initial_spawn_m']=[1375.4,130,1250.6];config.write_text(json.dumps(cfg),encoding='utf-8')
    for p in source.glob('*.gd'):shutil.copy2(p,RUN/'Godot'/p.name)
    p=RUN/'Godot/visual_bridge.gd';p.write_text(p.read_text(encoding='utf-8-sig').replace('port: int = 19727','port: int = 19737'),encoding='utf-8')
    log=(output/'server.log').open('w',encoding='utf-8');logs.append(log)
    server=subprocess.Popen([str(dotnet),str(SERVER/'CoreServer.dll'),'--start'],cwd=SERVER,env=env,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
    end=time.monotonic()+45
    while time.monotonic()<end:
        try:
            with socket.create_connection(('127.0.0.1',10351),timeout=.2):break
        except OSError:time.sleep(.2)
    else:raise RuntimeError('Private server unavailable')
    account='codexqa'+hashlib.sha256(RUN.name.encode()).hexdigest()[:10];password=hashlib.sha256(('disposable-local-protocol-qa:'+RUN.name).encode()).hexdigest()[:24]
    sdk=ENGINE/'Binaries/ThirdParty/DotNet/10.0/win-x64';ce=dict(env,DOTNET_ROOT=str(sdk),DOTNET_ROOT_X64=str(sdk),PATH=str(sdk)+os.pathsep+env['PATH'])
    (RUN/'Reports/live/logout.request').unlink(missing_ok=True)
    log=(output/'client.log').open('w',encoding='utf-8');logs.append(log)
    command=[str(args.install/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'),'--headless','--path',str(RUN/'LobbyProject'),'--script',str(RUN/'Godot/gateway_main.gd'),'--','--server=127.0.0.1','--server-port=10351','--account='+account,'--password='+password,'--no-world','--bridge-character=Codexdruid','--bridge-door-audio-catalog='+str(workspace/'DoorAudioLab/OriginalDoorAudio_v01/sounds.json')]
    client=subprocess.Popen(command,cwd=RUN,env=ce,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    end=time.monotonic()+45
    while time.monotonic()<end:
        try:peer=socket.create_connection(('127.0.0.1',19737),timeout=.3);peer.settimeout(.1);break
        except OSError:time.sleep(.2)
    else:raise RuntimeError('Private gateway unavailable; inspect client.log')
    wait(lambda:snapshot.get('in_game') and snapshot.get('player_status',{}).get('ready'),'Fixture enters Connacht');settle(3)
    if args.native:
        import importlib.util
        relay_source=repo/'source/ue5-bridge/pet_sight_relay.py'
        spec=importlib.util.spec_from_file_location('door_native_relay',relay_source);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        relay=module.NativeSightRelay(peer,workspace,session,snapshot,output=output,duration=60,entity_ids=['player:local'],render=True,native_profile='footstep_walk' if args.footsteps else 'door_crossing' if args.crossing else 'door_audio');peer=relay
        wait(lambda:relay.read_report().get('spell_audio',{}).get('door_ready'),'Native original door catalog ready',90);settle(3)
        if args.crossing:wait(lambda:not relay.geometry_gate and relay.read_report().get('test_elapsed',0)>0,'Current-map terrain and both door groups loaded before movement',100)
    result['checks']['initial_hydration_silent']=not trace;assert not trace
    door=207033603
    if args.crossing:
        wait(lambda:motion and motion[-1].get('test_elapsed',0)>29,'Native opens, crosses and returns',45)
        fixtures=json.loads((workspace/'collision_catalog.json').read_text())
        fixture=next(f for model in fixtures['models'].values() for f in model.get('door_fixtures',[]) if door in f['groups'].values())
        plane=1250.6-fixture['position_m'][2]
        closed=lambda row:any(d['id']==door and not d['open'] and d['alpha']<.05 for d in row.get('doors',[]))
        outside=[row for row in motion if 6.3<row['test_elapsed']<7.9 and closed(row)]
        inside=[row for row in motion if 16.3<row['test_elapsed']<17.9 and closed(row)]
        assert outside and inside
        assert max(row['door_test_progress_m'] for row in outside)<plane-.05
        assert min(row['door_test_progress_m'] for row in inside)>plane+.05
        assert max(row['door_test_progress_m'] for row in motion)>6
        assert min(abs(row['door_test_progress_m']) for row in motion if 23<row['test_elapsed']<29)<.3
        assert sum(row['event']=='open' for row in trace)>=2 and sum(row['event']=='close' for row in trace)>=2
        result['checks']['native_closed_collision_crossing_return']=True
        result['crossing']={'plane_m':plane,'closed_outside_samples':len(outside),'closed_inside_samples':len(inside),'samples':len(motion)}
    if not args.crossing:
        # Manual packet checks are separate from the native movement itinerary.
        send('door',door_id=door,open=False)
        wait(lambda:any(row['id']==door and not row['open'] for row in snapshot.get('doors',[])),'Closed baseline acknowledged')
        settle(1);baseline=len(trace)
        send('door',door_id=door,open=True)
        wait(lambda:any(row['event']=='open' for row in trace[baseline:]),'Server opening produces original door sound')
        opening=next(row for row in trace[baseline:] if row['event']=='open');assert opening['set']==1 and opening['owner']=='door:'+str(door)
        result['checks']['real_open_acknowledged']=True
        send('door',door_id=door,open=True);settle(1)
        assert len(trace)==baseline+1;result['checks']['repeated_open_silent']=True
        send('door',door_id=door,open=False)
        wait(lambda:any(row['event']=='close' for row in trace[baseline+1:]),'Server closing produces original door sound')
        assert trace[-1]['set']==1 and trace[-1]['position_m']==opening['position_m']
        result['checks']['real_close_acknowledged_and_anchored']=True
        settle(2);assert len(trace)==baseline+2;result['checks']['snapshot_repetition_silent']=True
    if relay:
        wait(lambda:relay.read_report().get('spell_audio',{}).get('pcm_consumed_bytes',0)>0,'Actual server door samples consumed by UE audio',15)
        wait(lambda:relay.read_report().get('spell_audio',{}).get('played_clips',0)>=len(trace),'Native consumes every actual door transition',10)
        audio=relay.read_report()['spell_audio'];assert audio['played_clips']==len(trace)+audio.get('footstep_clips',0) and audio['invalid_resources']==audio['unresolved_references']==0,audio
        if args.footsteps:
            steps=relay.read_report()['footsteps'];assert steps['contacts_crossed']>=4 and audio['footstep_clips']>=4 and audio['footstep_pcm_consumed_bytes']>0
            result['footsteps']=steps;result['checks']['actual_native_local_steps_and_pcm']=True
        result['native_audio']=audio;result['checks']['real_server_door_pcm_consumed_by_engine']=True
        result['native_inputs']={str(p):digest(p) for p in [relay_source,workspace/('FootstepAudioLab/native_build.json' if args.footsteps else 'DoorAudioLab/native_build.json'),workspace/'DoorAudioLab/OriginalDoorAudio_v01/sounds.json']}
        peer=relay.backend;peer.settimeout(.1)
    assert all(digest(Path(path))==sha for path,sha in inputs.items())
    result['checks']['source_unchanged']=True;result['passed']=True
except Exception:result['errors'].append(traceback.format_exc())
finally:
    if peer and session:
        try:send('logout')
        except OSError:pass
    if client and client.poll() is None:
        (RUN/'Reports/live/logout.request').write_text('logout',encoding='utf-8')
        try:client.wait(timeout=90)
        except subprocess.TimeoutExpired:client.kill();client.wait();result['errors'].append('Private client forced stop')
    if peer:peer.close()
    if server and server.poll() is None:
        server.stdin.write('exit\n');server.stdin.flush()
        try:server.wait(timeout=45)
        except subprocess.TimeoutExpired:server.kill();server.wait();result['errors'].append('Private server forced stop')
    for log in logs:log.close()
    if relay:
        try:result['native_exit']=relay.finish();assert result['native_exit']==0
        except Exception:result['errors'].append(traceback.format_exc())
    if backed:
        with closing(checked()) as db,closing(sqlite3.connect(output/'before.sqlite3.db')) as backup:backup.backup(db)
        config.write_bytes(config_before);result['database_restored']=True
    result.update(events=trace,states=states,source_inputs=inputs,normal_shutdown=bool(client and server and client.returncode==server.returncode==0))
    if motion:(output/'crossing_samples.json').write_text(json.dumps(motion),encoding='utf-8')
    result['passed']=result['passed'] and result['normal_shutdown'] and not result['errors']
    (output/'verified.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'passed':result['passed'],'checks':result['checks'],'errors':result['errors'],'output':str(output)}));assert result['passed']
