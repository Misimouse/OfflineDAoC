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
parser.add_argument('--server-sounds',action='store_true')
parser.add_argument('--water-motion',action='store_true')
parser.add_argument('--water-regression',action='store_true')
parser.add_argument('--target-tracking',action='store_true')
parser.add_argument('--live-riding',action='store_true')
parser.add_argument('--riding-full-route',action='store_true')
parser.add_argument('--riding-space',action='store_true')
parser.add_argument('--key-configuration-candidate',action='store_true')
parser.add_argument('--keys-candidate',action='store_true')
parser.add_argument('--movement-keys',action='store_true')
parser.add_argument('--jump-landing',action='store_true')
parser.add_argument('--jump-candidate',action='store_true')
args=parser.parse_args();workspace=args.workspace.resolve();repo=Path(__file__).resolve().parents[3]
assert not args.key_configuration_candidate or (args.native and args.live_riding)
assert not args.riding_space or (args.live_riding and not args.riding_full_route)
assert not args.riding_full_route or args.live_riding
assert not args.live_riding or (args.native and not any([args.target_tracking,args.crossing,args.water_motion,args.water_regression,args.server_sounds,args.footsteps,args.jump_landing,args.jump_candidate,args.movement_keys,args.keys_candidate]))
assert not args.target_tracking or (args.native and not any([args.crossing,args.water_motion,args.water_regression,args.server_sounds,args.footsteps,args.jump_landing,args.jump_candidate,args.movement_keys,args.keys_candidate]))
assert not args.keys_candidate or (args.native and (args.water_motion or args.water_regression))
assert not args.movement_keys or (args.native and not any([args.crossing,args.water_motion,args.water_regression,args.server_sounds,args.footsteps,args.jump_landing,args.jump_candidate]))
assert not args.jump_candidate or (args.native and (args.water_motion or args.water_regression))
assert not args.jump_landing or (args.native and not any([args.crossing,args.water_motion,args.water_regression,args.server_sounds,args.footsteps]))
assert not args.server_sounds or (args.native and not args.crossing and not args.footsteps)
assert not args.water_regression or (args.native and args.crossing and not args.water_motion and not args.server_sounds and not args.footsteps)
assert not args.water_motion or (args.native and not args.crossing and not args.footsteps and not args.server_sounds)
assert not args.crossing or args.native
assert not args.footsteps or (args.native and args.crossing)
os.environ['DAOC_INSTALL']=str(args.install.resolve());sys.path.insert(0,str(workspace/'ProtocolQA'))
from qa_runtime import ROOT,RUN,SERVER,DB,env,dotnet,ENGINE
assert ROOT.resolve()==workspace and DB.is_relative_to(RUN) and RUN.is_relative_to(workspace/'ProtocolQA')
output=workspace/('Reports/live_riding_real_protocol' if args.live_riding else 'Reports/target_tracking_real_protocol' if args.target_tracking else 'Reports/movement_keys_real_protocol' if args.movement_keys else 'Reports/jump_landing_real_protocol' if args.jump_landing else 'Reports/water_door_regression' if args.water_regression else 'Reports/water_movement_real_protocol' if args.water_motion else 'Reports/server_sound_audio_real_protocol' if args.server_sounds else 'Reports/footstep_audio_real_protocol' if args.footsteps else 'Reports/door_audio_real_protocol')/datetime.now().strftime('%Y%m%d-%H%M%S-%f');output.mkdir(parents=True)
result={'passed':False,'disposable_only':True,'checks':{},'errors':[]};server=client=peer=relay=None;logs=[];backed=False
session='';snapshot={};buffer=b'';serial=0;trace=[];states=[];motion=[];sound_trace=[]
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
            if (args.crossing or args.water_motion or args.jump_landing or args.movement_keys or args.target_tracking or args.live_riding) and relay:
                current=relay.read_report()
                if (current.get('door_auto_test') or args.water_motion or args.jump_landing or args.movement_keys or args.target_tracking or args.live_riding) and (not motion or current.get('test_elapsed')!=motion[-1].get('test_elapsed')):motion.append(current)
            for event in value.get('server_sound_audio',[]):
                if not any(row['seq']==event['seq'] for row in sound_trace):sound_trace.append(event)
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
        start=[1470.4,118.3,1091.2] if args.water_motion else [1375.4,130,1250.6]
        db.execute("UPDATE DOLCharacters SET Class=53,Level=5,Region=200,Xpos=?,Ypos=?,Zpos=?,Health=200,DeathTime=0,HasGravestone=0 WHERE Name='Codexdruid'",(round(start[0]*40)+35*8192,round(start[2]*40)+51*8192,round(start[1]*40)))
        if args.target_tracking:
            witness=dict(db.execute("SELECT * FROM Mob WHERE ClassType='DOL.GS.GameTrainingDummy' AND Region=200 LIMIT 1").fetchone());assert witness
            witness.update(Mob_ID='codex_target_tracking_'+hashlib.sha256(RUN.name.encode()).hexdigest()[:12],Name='Codex Tracking Witness',ClassType='DOL.GS.GameNPC',Region=200,
                X=round(1375.4*40)+35*8192,Y=round(1243.6*40)+51*8192,Z=round(130.114*40),Model=1984,Size=50,Realm=3,Level=5,Flags=16,Speed=0,RoamingRange=0,AggroLevel=0,AggroRange=0,
                Guild='',TranslationId='',Suffix='',Brain='',PathID='',OwnerID='',PackageID='',NPCTemplateID=0,EquipmentTemplateID='',ItemsListTemplateID='',HouseNumber=0)
            names=list(witness);db.execute('INSERT INTO Mob ('+','.join('"'+n+'"' for n in names)+') VALUES ('+','.join('?' for _ in names)+')',[witness[n] for n in names])
            outdoor=dict(witness, Mob_ID=witness['Mob_ID']+'_outdoor',Name='Codex Outdoor Witness',Y=round(1257.6*40)+51*8192)
            db.execute('INSERT INTO Mob ('+','.join('"'+n+'"' for n in names)+') VALUES ('+','.join('?' for _ in names)+')',[outdoor[n] for n in names])
        if args.live_riding:
            # Copy public game definitions only into the marked private fixture.
            normal_db=args.install.resolve()/'runtime/data/opendaoc.sqlite3.db'
            with closing(sqlite3.connect('file:'+normal_db.as_posix()+'?mode=ro',uri=True)) as reference:
                reference.row_factory=sqlite3.Row;reference.execute('PRAGMA query_only=ON')
                stable=dict(reference.execute("SELECT * FROM Mob WHERE Name='Carsten' AND Region=200 AND ClassType LIKE '%Stable%' LIMIT 1").fetchone())
                ticket='HR_TirNaNog_DruimLigen';item=dict(reference.execute('SELECT * FROM ItemTemplate WHERE Id_nb=?',(ticket,)).fetchone())
                path=dict(reference.execute('SELECT * FROM Path WHERE PathID=?',(ticket,)).fetchone());points=[dict(row) for row in reference.execute('SELECT * FROM PathPoints WHERE PathID=? ORDER BY Step',(ticket,))]
                merchants=[dict(row) for row in reference.execute('SELECT * FROM MerchantItem WHERE ItemListID=?',(stable['ItemsListTemplateID'],))]
                route_items=[dict(reference.execute('SELECT * FROM ItemTemplate WHERE Id_nb=?',(r['ItemTemplateID'],)).fetchone()) for r in merchants]
                template=dict(reference.execute('SELECT * FROM NpcTemplate WHERE TemplateId=?',(item['Color'],)).fetchone())
            assert points and all(35*8192<=row['X']<43*8192 and 51*8192<=row['Y']<59*8192 for row in points)
            stable['Mob_ID']='codex_riding_stable_'+hashlib.sha256(RUN.name.encode()).hexdigest()[:12]
            stable['ItemsListTemplateID']=stable['Mob_ID']
            for i,merchant in enumerate(merchants):merchant['ItemListID']=stable['ItemsListTemplateID'];merchant['MerchantItem_ID']=stable['Mob_ID']+'_'+str(i)
            for table,rows in [('Mob',[stable]),('ItemTemplate',route_items),('Path',[path]),('PathPoints',points),('MerchantItem',merchants),('NpcTemplate',[template])]:
                for row in rows:
                    names=list(row);db.execute('INSERT OR REPLACE INTO "'+table+'" ('+','.join('"'+n+'"' for n in names)+') VALUES ('+','.join('?' for _ in names)+')',[row[n] for n in names])
            start=[(stable['X']-35*8192)*.025,stable['Z']*.025,(stable['Y']-51*8192)*.025+2]
            db.execute("UPDATE DOLCharacters SET Xpos=?,Ypos=?,Zpos=?,Gold=5 WHERE Name='Codexdruid'",(round(start[0]*40)+35*8192,round(start[2]*40)+51*8192,round(start[1]*40)))
        db.commit()
    cfg=json.loads(config_before);cfg['initial_spawn_m']=start;config.write_text(json.dumps(cfg),encoding='utf-8')
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
    if args.live_riding:command.append('--bridge-travel-catalog='+str(workspace/'LiveRidingLab/travel_routes.json'))
    if args.server_sounds:command.append('--bridge-server-sound-catalog='+str(workspace/'ServerSoundAudioLab/OriginalServerSoundAudio_v01/sounds.json'))
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
        ids=['player:local']
        if args.target_tracking:
            wait(lambda:any(row.get('name')=='Codex Tracking Witness' for row in snapshot['entities']),'Private tracking witness spawns')
            witness_id=next(row['id'] for row in snapshot['entities'] if row.get('name')=='Codex Tracking Witness');ids.append(witness_id)
            wait(lambda:any(row.get('name')=='Codex Outdoor Witness' for row in snapshot['entities']),'Private outdoor witness spawns')
            outdoor_id=next(row['id'] for row in snapshot['entities'] if row.get('name')=='Codex Outdoor Witness');ids.append(outdoor_id)
        relay=module.NativeSightRelay(peer,workspace,session,snapshot,output=output,duration=180 if args.live_riding and args.riding_full_route else 120 if args.live_riding else 90 if args.target_tracking else 60,entity_ids=None if args.live_riding else ids,render=True,candidate_lab='KeyConfigurationLab' if args.key_configuration_candidate else None,native_profile='live_riding' if args.live_riding else 'target_tracking' if args.target_tracking else ('keys_water_crossing' if args.water_regression else 'keys_water_walk') if args.keys_candidate else 'movement_keys' if args.movement_keys else ('jump_water_crossing' if args.water_regression else 'jump_water_walk') if args.jump_candidate else 'jump_landing' if args.jump_landing else 'water_crossing' if args.water_regression else 'water_walk' if args.water_motion else 'server_sound' if args.server_sounds else 'footstep_walk' if args.footsteps else 'door_crossing' if args.crossing else 'door_audio');peer=relay
        wait(lambda:relay.read_report().get('spell_audio',{}).get('door_ready'),'Native original door catalog ready',90);settle(3)
        if args.crossing or args.water_motion or args.jump_landing or args.movement_keys or args.target_tracking or args.live_riding:wait(lambda:not relay.geometry_gate and relay.read_report().get('test_elapsed',0)>0,'Current-map terrain and both door groups loaded before movement',100)
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
    if not args.crossing and not args.water_motion and not args.jump_landing and not args.movement_keys and not args.target_tracking and not args.live_riding:
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
    if args.live_riding:
        wait(lambda:any(row.get('name')=='Carsten' for row in snapshot['entities']),'Original stable master fixture spawns')
        stable_id=next(row['id'] for row in snapshot['entities'] if row.get('name')=='Carsten')
        send('target',entity_id=stable_id);settle(.3);send('interact',entity_id=stable_id)
        wait(lambda:bool(snapshot.get('interaction',{}).get('merchant',{}).get('pages')),'Original merchant window receives real route ticket')
        shop=snapshot['interaction']['merchant'];offers=[(int(page),row) for page,rows in shop['pages'].items() for row in rows if row.get('name')==item['Name']]
        assert len(offers)==1;page,offer=offers[0]
        unavailable=[(int(p),r) for p,rows in shop['pages'].items() for r in rows if r.get('travel_available') is False]
        assert unavailable,'Original shop must include its unsupported destinations'
        blocked_page,blocked=unavailable[0];money_before=snapshot['inventory']['money'];items_before=snapshot['inventory']['items']
        send('merchant_buy',merchant_id=stable_id,merchant_revision=shop['catalog_revision'],inventory_revision=snapshot['inventory']['state_revision'],page=blocked_page,index=blocked['index'],count=1)
        wait(lambda:'not available in the loaded world' in snapshot.get('inventory',{}).get('feedback',''),'Unsupported route rejected before original BuyItem')
        settle(.5);assert snapshot['inventory']['money']==money_before and snapshot['inventory']['items']==items_before and not snapshot['inventory']['pending'] and not snapshot['riding']['mounted']
        result['checks']['unsupported_route_no_charge_no_item_no_mount']=True

        send('merchant_buy',merchant_id=stable_id,merchant_revision=shop['catalog_revision'],inventory_revision=snapshot['inventory']['state_revision'],page=page,index=offer['index'],count=1)
        wait(lambda:snapshot.get('riding',{}).get('mounted',False),'Original server confirms ticket purchase and mount',15)
        wait(lambda:relay.read_report().get('riding',{}).get('seat_ready',False),'Native resolves actual server mount saddle',15)
        native=relay.read_report();origin=native['position_m'];assert native.get('local_animation')=='ride_horse',native.get('local_animation')
        result['checks']['original_ticket_buy_mount_ack_and_pose']=True
        wait(lambda:((relay.read_report()['position_m'][0]-origin[0])**2+(relay.read_report()['position_m'][2]-origin[2])**2)**.5>8,'Actual server horse carries native rider',20)
        assert snapshot['riding']['state_flags']==0x18 and any(row.get('speed_mps',0)>10 for row in relay.movement_forwarded)
        result['checks']['actual_server_route_movement']=True
        wait(lambda:relay.read_report().get('spell_audio',{}).get('riding_hoof_pcm_consumed_bytes',0)>0,'Original hoof PCM consumed during actual server travel',15)
        result['checks']['original_gallop_pcm_consumed_during_real_route']=True

        if args.riding_full_route:
            wait(lambda:not snapshot.get('riding',{}).get('mounted',True),'Original server ends full route and acknowledges dismount',200)
            expected=[(points[-1]['X']-35*8192)*.025,points[-1]['Z']*.025,(points[-1]['Y']-51*8192)*.025]
            actual=relay.read_report()['position_m'];distance=((actual[0]-expected[0])**2+(actual[2]-expected[2])**2)**.5
            assert distance<12,(actual,expected,distance)
            result['checks']['original_route_reaches_final_path_point']=True
            result['route_end_error_m']=distance
        elif args.riding_space:
            (output/'Space.request').write_text('Press and release Space via native input',encoding='utf-8')
            wait(lambda:relay.read_report().get('riding',{}).get('qa_space_key_sent',False),'Actual native Space input injected',10)
            wait(lambda:not snapshot.get('riding',{}).get('mounted',True),'Original server acknowledges native Space dismount',15)
            result['checks']['actual_space_key_dismount_request_and_ack']=True
        else:
            send('chat',text='/dismount')
            wait(lambda:not snapshot.get('riding',{}).get('mounted',True),'Original server acknowledges dismount',15)
        wait(lambda:not relay.read_report().get('riding',{}).get('mounted',True) and relay.read_report().get('character_grounded',False),'Native restores grounded character collision',15)
        result['checks']['actual_dismount_ack_and_grounded_collision']=True
        settle(1);hoof_before=relay.read_report().get('spell_audio',{}).get('riding_hoof_clips',0);assert hoof_before>0
        settle(1);assert relay.read_report().get('spell_audio',{}).get('riding_hoof_clips',0)==hoof_before
        result['checks']['no_new_hoof_sounds_after_dismount']=True

        result['route_ticket']=ticket;result['mounted_origin']=origin;result['end_position']=relay.read_report()['position_m'];result['native_move_commands']=relay.movement_forwarded
    if args.target_tracking:
        send('chat',text='/follow');settle(.5)
        assert any('You must select a target to follow!' in row.get('text','') for row in snapshot.get('chat',{}).get('entries',[]))
        send('target_self');send('chat',text='/stick');settle(.5)
        assert any("You can't stick yourself!" in row.get('text','') for row in snapshot.get('chat',{}).get('entries',[]))
        send('target',entity_id=witness_id);settle(.5)
        send('door',door_id=door,open=False)
        wait(lambda:any(row['id']==door and not row['open'] for row in snapshot.get('doors',[])),'Original server acknowledges closed fixture door',15)
        wait(lambda:any(row['id']==door and not row['open'] and row['alpha']<.05 for row in relay.read_report().get('doors',[])),'Native closed leaf collider ready',10)
        origin=relay.read_report()['position_m']
        send('chat',text='/face')
        wait(lambda:relay.read_report().get('target_tracking',{}).get('active') and relay.read_report()['target_tracking']['mode']=='face','Native faces the original selected target')
        settle(1);face_position=relay.read_report()['position_m'];assert sum((a-b)**2 for a,b in zip(origin,face_position))<.04
        facing=relay.movement_forwarded[-1]['forward_xz'];assert abs(facing[0])<.05 and facing[1]<-.99,facing
        result['checks']['actual_face_keeps_position']=True
        send('chat',text='/follow')
        wait(lambda:relay.read_report().get('target_tracking',{}).get('mode')=='follow','Native follow starts')
        settle(3);blocked=relay.read_report()
        catalog=json.loads((workspace/'collision_catalog.json').read_text());fixture=next(f for m in catalog['models'].values() for f in m.get('door_fixtures',[]) if door in f['groups'].values());plane=fixture['position_m'][2]
        assert blocked['position_m'][2]>plane+.05 and blocked['target_tracking']['active'],blocked['position_m']
        result['checks']['follow_respects_closed_real_door']=True
        # Tracking is direct movement, not pathfinding. Opening a swinging leaf while
        # pushing into it can legitimately displace the capsule against a jamb.
        # Keep the obstacle check separate from gap tests on unobstructed ground.
        send('target',entity_id=outdoor_id);settle(.5);send('chat',text='/follow')
        wait(lambda:relay.read_report().get('target_tracking',{}).get('target_entity_id')==outdoor_id,'Tracking switches to the newly selected outdoor target')
        def gap():
            pos=relay.read_report().get('position_m',[0,0,0]);return ((pos[0]-1375.4)**2+(pos[2]-1257.6)**2)**.5
        wait(lambda:gap()<=3.1 and relay.read_report().get('water_movement',{}).get('speed_mps',1)<.05,'Follow stops at original three metre gap',20)
        follow_gap=gap();assert 2.6<follow_gap<=3.1;result['checks']['actual_follow_switches_target_and_stops']=True
        send('chat',text='/stick');wait(lambda:relay.read_report().get('target_tracking',{}).get('mode')=='stick','Native stick starts')
        wait(lambda:gap()<=1.5 and relay.read_report().get('water_movement',{}).get('speed_mps',1)<.05,'Stick stops at original 1.4 metre gap',15)
        stick_gap=gap();assert 1.0<stick_gap<=1.5;result['checks']['actual_stick_stops_at_close_gap']=True
        send('chat',text='/face');wait(lambda:relay.read_report().get('target_tracking',{}).get('mode')=='face','Face works after switching tracking modes')
        # Delete only the unique fixture selected above, inside the marked private server.
        assert outdoor['Name']=='Codex Outdoor Witness' and outdoor['Mob_ID'].startswith('codex_target_tracking_')
        send('chat',text='/mob remove')
        wait(lambda:not any(row['id']==outdoor_id for row in snapshot.get('entities',[])),'Private witness is removed by its original server')
        wait(lambda:not relay.read_report().get('target_tracking',{}).get('active',True),'Native clears tracking after despawn',10)
        result['checks']['actual_target_despawn_cancels_tracking']=True
        result['tracking_gaps_m']={'follow':follow_gap,'stick':stick_gap};result['native_move_commands']=relay.movement_forwarded
    if args.movement_keys:
        wait(lambda:motion and motion[-1].get('test_elapsed',0)>21,'Native runs automatically, walks, backpedals and stops',35)
        windows=[('run',9,11,4.775),('walk',13,14.9,1.67125),('back',16,17.9,3.10375)]
        witnesses={}
        for name,lo,hi,speed in windows:
            sample=[m for m in motion if lo<m.get('test_elapsed',0)<hi]
            assert sample,(name,'missing motion samples')
            assert all(abs(m['movement_keys']['ground_speed_limit_mps']-speed)<.02 for m in sample),(name,sample)
            assert any(abs(m['water_movement']['speed_mps']-speed)<.12 for m in sample),(name,'actual velocity differs')
            witnesses[name]=sample
        assert any(m.get('local_animation')=='walk_back' for m in witnesses['back'])
        assert all(not m['movement_keys']['run_lock'] for m in motion if m.get('test_elapsed',0)>19)
        assert any(m['water_movement']['speed_mps']<.05 for m in motion if m.get('test_elapsed',0)>20)
        result['movement_witnesses']=witnesses;result['checks']['actual_run_walk_back_and_stop']=True
    if args.jump_landing:
        wait(lambda:motion and motion[-1].get('test_elapsed',0)>11,'Native completes original jump',25)
        moves=relay.movement_forwarded
        airborne=[m for m in moves if not m.get('on_ground',True) and not m.get('swimming')]
        assert airborne and any(m.get('vertical_speed_mps',0)>2 for m in airborne)
        landings=[m for m in moves if m.get('on_ground') and m.get('vertical_speed_mps',0)<-2]
        assert len(landings)==1,landings
        assert 3<-landings[0]['vertical_speed_mps']<6
        assert any(m.get('on_ground') and m.get('vertical_speed_mps')==0 for m in moves[moves.index(landings[0])+1:])
        result['checks']['actual_jump_airborne_and_single_landing_packet']=True
        before=len(moves);pos=relay.read_report()['position_m']
        send('chat',text='/jump to %d %d %d 200'%(round(pos[0]*40)+35*8192,round(pos[2]*40)+51*8192,round((pos[1]+9)*40)))
        wait(lambda:any(m.get('on_ground') and m.get('vertical_speed_mps',0)<-15 for m in relay.movement_forwarded[before:]),'Actual fall sends impact speed with ground flag',20)
        result['checks']['actual_nine_metre_fall_packet']=True
        result['native_move_commands']=relay.movement_forwarded
    if args.water_motion:
        wait(lambda:motion and motion[-1].get('test_elapsed',0)>29,'Native enters deep water, stops, and returns to shore',40)
        swim=[row for row in motion if row.get('water_movement',{}).get('swimming')]
        assert swim,'No actual surface swimming recorded'
        stable=[row for row in swim if row['test_elapsed']>12.5 and row['test_elapsed']<16]
        assert stable,'No stationary swim witness'
        assert all(not row['water_movement']['on_ground'] for row in stable)
        assert all(abs(row['water_movement']['feet_m'][1]-116.95)<.4 for row in stable)
        assert any(row['water_movement']['animation']=='swim' for row in swim)
        assert max(row['water_movement']['speed_mps'] for row in stable)<.3
        assert any(row.get('water_movement',{}).get('surface')=='water' for row in motion)
        assert not motion[-1]['water_movement']['swimming']
        assert abs(motion[-1]['position_m'][0]-start[0])<1
        assert relay.read_report()['spell_audio'].get('swim_step_clips',0)>0
        moves=relay.movement_forwarded;assert any(row.get('swimming') and not row.get('on_ground') for row in moves)
        result['checks']['actual_surface_swim_pose_buoyancy_and_return']=True
        result['water_swim_samples']=len(swim);result['water_stationary_samples']=len(stable)
        result['native_move_commands']=moves
        # Actual original Elf Bridge, above the same river mask: standing on its
        # deck must remain ordinary grounded movement, not surface swimming.
        send('chat',text='/jump to %d %d %d 200'%(round(1206.4*40)+35*8192,round(742.4*40)+51*8192,round(140*40)))
        wait(lambda:relay.read_report().get('position_m') and abs(relay.read_report()['position_m'][0]-1206.4)<3 and abs(relay.read_report()['position_m'][2]-742.4)<3,'Native reaches the actual river bridge',20)
        wait(lambda:relay.read_report().get('water_movement',{}).get('on_ground') and not relay.read_report()['water_movement']['swimming'] and relay.read_report()['water_movement']['feet_m'][1]>117.3,'Native lands on the bridge deck above the original river',18)
        bridge=relay.read_report()['water_movement']
        assert bridge['on_ground'] and not bridge['swimming'] and bridge['feet_m'][1]>117.3,bridge
        result['bridge_water_witness']=bridge;result['checks']['actual_river_bridge_remains_grounded']=True
    if args.server_sounds:
        wait(lambda:relay.read_report().get('spell_audio',{}).get('active_voices',-1)==0,'Earlier door voices finish before event PCM witness',15)
        server_pcm_before=relay.read_report()['spell_audio']['pcm_consumed_bytes']
        for sid in [7,11,12]:
            before=len(sound_trace);send('chat',text='/cast sound '+str(sid))
            wait(lambda:len(sound_trace)>before,'Real server sound packet '+str(sid))
            assert sound_trace[-1]['sound_id']==sid and not sound_trace[-1]['placed']
        settle(2);assert len(sound_trace)==3;result['checks']['actual_server_sound_packets']=True
        wait(lambda:relay.read_report().get('spell_audio',{}).get('server_sound_clips',0)==3,'Native plays all three actual server sounds',15)
        wait(lambda:relay.read_report()['spell_audio']['pcm_consumed_bytes']>server_pcm_before,'Actual server event PCM consumed',15)
        result['server_sound_pcm_bytes']=relay.read_report()['spell_audio']['pcm_consumed_bytes']-server_pcm_before
    if relay:
        if not args.jump_landing and not args.movement_keys and not args.live_riding:wait(lambda:relay.read_report().get('spell_audio',{}).get('pcm_consumed_bytes',0)>0,'Actual server door samples consumed by UE audio',15)
        wait(lambda:relay.read_report().get('spell_audio',{}).get('played_clips',0)>=len(trace),'Native consumes every actual door transition',10)
        audio=relay.read_report()['spell_audio'];assert audio['played_clips']==len(trace)+audio.get('footstep_clips',0)+audio.get('server_sound_clips',0)+audio.get('riding_hoof_clips',0) and audio['invalid_resources']==audio['unresolved_references']==0,audio
        if args.footsteps or args.water_motion:
            steps=relay.read_report()['footsteps'];assert steps['contacts_crossed']>=4 and audio['footstep_clips']>=4 and audio['footstep_pcm_consumed_bytes']>0
            result['footsteps']=steps;result['checks']['actual_native_local_steps_and_pcm']=True
        result['native_audio']=audio;result['checks']['real_server_door_pcm_consumed_by_engine']=not (args.jump_landing or args.movement_keys or args.live_riding)
        result['native_inputs']={str(p):digest(p) for p in [relay_source,workspace/('KeyConfigurationLab/native_build.json' if args.key_configuration_candidate else 'LiveRidingLab/native_build.json' if args.live_riding else 'TargetTrackingLab/native_build.json' if args.target_tracking else 'MovementKeysLab/native_build.json' if args.movement_keys or args.keys_candidate else 'JumpLandingLab/native_build.json' if args.jump_landing or args.jump_candidate else 'WaterMovementLab/native_build.json' if args.water_motion or args.water_regression else 'ServerSoundAudioLab/native_build.json' if args.server_sounds else 'FootstepAudioLab/native_build.json' if args.footsteps else 'DoorAudioLab/native_build.json'),workspace/'DoorAudioLab/OriginalDoorAudio_v01/sounds.json']}
        peer=relay.backend;peer.settimeout(.1)
    if args.movement_keys or args.keys_candidate:
        catalog=workspace/'MovementKeysLab/movement.json';result['native_inputs'][str(catalog)]=digest(catalog)
    if args.live_riding:
        for path in [workspace/'LiveRidingLab'/name for name in ['riding.json','models.json','travel_routes.json','audio_resources.json']]:result['native_inputs'][str(path)]=digest(path)
        riding_audio=json.loads((workspace/'LiveRidingLab/audio_resources.json').read_text(encoding='utf-8-sig'))
        for path in [riding_audio['catalog']]+list(riding_audio['files']):result['native_inputs'][path]=digest(Path(path))
    if args.water_motion or args.water_regression:
        approved=relay.read_report()['approved_environment']['bindings'];assert len(approved)==1
        layer=approved[0];assert layer['loaded'] and layer['references']==1 and layer['old_water_hidden'] and layer['visible_components']>0,layer
        result['approved_environment']=approved;result['checks']['approved_river_layer_active']=True
        # Preserve the newer shared ground-cover material; the environment
        # binding deliberately refuses to replace a different authored material.
        terrain=workspace/'WaterMovementLab/terrain_inspection.json'
        observed=json.loads(terrain.read_text(encoding='utf-8-sig'))
        saved=[row for row in observed if row['mesh'].endswith('/Connacht_Terrain_Original_257.Connacht_Terrain_Original_257')]
        assert len(saved)==1 and saved[0]['materials']==['/Game/DAoC/Connacht_Ground_Cover_v02/Materials/M_Connacht_Ground_v02.M_Connacht_Ground_v02']
        result['preserved_newer_terrain_material']=saved[0];result['checks']['shared_terrain_material_preserved']=True
        result['native_inputs'][str(terrain)]=digest(terrain)
        for path in [workspace/'environment_catalog.json',workspace/'WaterMovementLab/NativeHost/Config/DefaultEngine.ini']:result['native_inputs'][str(path)]=digest(path)
        catalog=workspace/'WaterMovementLab/water_field.json';result['native_inputs'][str(catalog)]=digest(catalog)
    if args.server_sounds:
        catalog=workspace/'ServerSoundAudioLab/OriginalServerSoundAudio_v01/sounds.json';result['native_inputs'][str(catalog)]=digest(catalog)
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
    result.update(events=trace,server_sound_events=sound_trace,states=states,source_inputs=inputs,normal_shutdown=bool(client and server and client.returncode==server.returncode==0))
    if motion:(output/'crossing_samples.json').write_text(json.dumps(motion),encoding='utf-8')
    result['passed']=result['passed'] and result['normal_shutdown'] and not result['errors']
    (output/'verified.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'passed':result['passed'],'checks':result['checks'],'errors':result['errors'],'output':str(output)}));assert result['passed']
