"""Real existing caster, original quickbar spell use, server cast/interrupt/buff/damage evidence."""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json,socket,subprocess,time,hashlib,traceback,math
from pathlib import Path
from native_sight_relay import NativeSightRelay
R=Path(__file__).resolve().parent;D=R/'Reports/spell_casting';L=R/'Reports/live';session='';snapshot={};buffer=b'';serial=0;sock=None;p=None;trace=[];saved_file=None;saved_bytes=None;had_file=False;home=None;jumped=False;relay=None;track_target='';last_sight=0.0
result={'passed':False,'real_server':True,'character':'BridgeCaster','normal_logout':False,'errors':[]}
def pump():
 global buffer,snapshot,session
 try:b=sock.recv(1048576)
 except socket.timeout:return
 if not b:raise RuntimeError('Bridge closed')
 buffer+=b
 while b'\n' in buffer:
  line,buffer=buffer.split(b'\n',1);v=json.loads(line)
  if v.get('type')=='hello':session=v['session']
  if v.get('type')=='snapshot':
   snapshot=v;c=json.loads(json.dumps(v));target=v.get('interaction',{}).get('target',{}).get('id');c['entities']=[x for x in c.get('entities',[]) if x['id']=='player:local' or x['id']==target];trace.append({'at':time.monotonic(),'snapshot':c})
def heartbeat():
 global last_sight
 if not track_target or time.monotonic()-last_sight<.25:return
 target=next((e for e in snapshot.get('entities',[]) if e['id']==track_target),None)
 if not target:return
 q=relay.read_report().get('position_m',pos());assert len(q)==3 and math.dist(q,pos())<5,'Native capsule moved beyond allowed server correction';dx=target['position_m'][0]-q[0];dz=target['position_m'][2]-q[2];length=max(.001,math.hypot(dx,dz));visible=math.dist(q,target['position_m'])<=6
 send('move',position_m=q,forward_xz=[dx/length,dz/length],speed_mps=0,target_in_view=visible,target_entity_id=track_target);last_sight=time.monotonic()
def wait(fn,label,timeout=20):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  pump()
  heartbeat()
  if fn():return
 raise RuntimeError('Timeout '+label+'; messages: '+repr(snapshot.get('messages',[])))
def settle(seconds):
 end=time.monotonic()+seconds
 while time.monotonic()<end:pump()
def send(action,**kw):
 global serial
 serial+=1;sock.sendall((json.dumps(dict(type='command',session=session,id='spell-real:'+str(serial),action=action,**kw))+'\n').encode())
def ui():return snapshot.get('classic_ui',{})
def cast():return ui().get('casting',{})
def pos():return next(x['position_m'] for x in snapshot['entities'] if x['id']=='player:local')
def jump(point):
 send('chat',text='/jump to %d %d %d 200'%(round(point[0]*40)+35*8192,round(point[2]*40)+51*8192,round(point[1]*40)))
def bind(e):
 send('ui_assign',bar=2,bank=ui()['banks'][2],slot=9,entry_id=e['id'],entry_token=e['token']);wait(lambda:ui()['bars'][2][ui()['banks'][2]][9].get('id')==e['id'],'binding')
try:
 with socket.socket() as guard:guard.bind(('127.0.0.1',19727))
 log=(D/'native_live_launcher.log').open('w',encoding='utf-8');p=subprocess.Popen([str(ENGINE / 'Binaries/ThirdParty/DotNet/10.0/win-x64/dotnet.exe'),str(R/'Launcher/bin/Release/net10.0/BridgeLauncher.dll'),'--character=BridgeCaster','--session-only'],cwd=R,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 end=time.monotonic()+85
 while time.monotonic()<end:
  try:sock=socket.create_connection(('127.0.0.1',19727),timeout=.2);break
  except OSError:time.sleep(.2)
 assert sock;sock.settimeout(.08);wait(lambda:ui().get('skills_ready') and snapshot.get('inventory',{}).get('ready') and snapshot.get('player_status',{}).get('ready'),'caster ready',85)
 relay=NativeSightRelay(sock,R,session,snapshot);sock=relay;wait(lambda:relay.read_report().get('local_animation')!='' and bool(relay.read_report().get('local_animation')),'native scene ready',80)
 home=list(pos());baseline=snapshot['inventory']['items'];baseline_points=ui()['points'];saved_file=R/'Client/Saved/ClassicUI'/(hashlib.sha256(ui()['character'].lower().encode()).hexdigest()+'.json');had_file=saved_file.exists();saved_bytes=saved_file.read_bytes() if had_file else None
 buff=next(e for e in ui()['entries'] if e['name']=='Lesser Powerward');damage=next(e for e in ui()['entries'] if e['name']=='Gleam Ray');old=ui()['bars'][2][ui()['banks'][2]][9];bank=ui()['banks'][2]
 send('chat',text='/gmstealth off');settle(.5);send('target',entity_id='');bind(buff)
 moving_effects=list(ui().get('effects',[]));moving_mana=snapshot['player_status']['vitals']['mana'];moving_started=time.monotonic();q=list(pos());q[0]+=.25;send('move',position_m=q,forward_xz=[1,0],speed_mps=1,target_in_view=False,target_entity_id='');send('ui_use_slot',bar=2,slot=9);saw_release=False
 while time.monotonic()-moving_started<1.2:
  settle(.2);saw_release=saw_release or cast().get('phase')=='released';q=list(pos());q[0]+=.2;send('move',position_m=q,forward_xz=[1,0],speed_mps=1,target_in_view=False,target_entity_id='')
 send('move',position_m=q,forward_xz=[1,0],speed_mps=0,target_in_view=False,target_entity_id='');settle(.3)
 result['cast_while_moving_blocked']=not saw_release and ui().get('effects',[])==moving_effects and snapshot['player_status']['vitals']['mana']>=moving_mana and any('move and interrupt' in m.lower() for m in snapshot.get('messages',[]))
 assert result['cast_while_moving_blocked'],'A normal spell must not complete while walking'

 send('ui_use_slot',bar=2,slot=9);wait(lambda:cast().get('phase')=='casting','first real buff cast')
 result['cast_duration_ms']=cast()['duration_ms'];q=list(pos());q[0]+=.25;send('move',position_m=q,forward_xz=[0,1],speed_mps=1,target_in_view=False,target_entity_id='');settle(.2);send('move',position_m=q,forward_xz=[0,1],speed_mps=0,target_in_view=False,target_entity_id='')
 wait(lambda:cast().get('phase')=='interrupted','movement interrupt');result['movement_interrupted']=True;settle(1)
 before_effects=list(ui().get('effects',[]));before_stats=ui()['weapon_stats'];before_mana=snapshot['player_status']['vitals']['mana']
 send('ui_use_slot',bar=2,slot=9);wait(lambda:cast().get('phase')=='casting','completed buff start');wait(lambda:cast().get('phase')=='released','original buff release');wait(lambda:bool(ui().get('effects')) and ui()['effects']!=before_effects,'real buff icon')
 result['buff']={'effects':ui()['effects'],'mana_before':before_mana,'mana_after':snapshot['player_status']['vitals']['mana'],'stats_before':before_stats,'stats_after':ui()['weapon_stats']};result['buff_applied']=True
 # Use a real nearby mob; a point within 6 m is visible by the original client's near-distance rule.
 targets=[e for e in snapshot['entities'] if e['id'].startswith('npc:') and e.get('kind')=='npc' and e.get('model_id')==118 and e.get('health',1)>0]
 if targets:
  target=min(targets,key=lambda e:math.dist(pos(),e['position_m']));point=list(target['position_m']);point[0]+=3;jump(point);jumped=True;settle(.8);send('chat',text='/gmstealth off');send('target',entity_id=target['id']);wait(lambda:snapshot.get('interaction',{}).get('target',{}).get('id')==target['id'],'real frog selected');bind(damage)
  q=list(pos());target=next(e for e in snapshot['entities'] if e['id']==target['id']);relay.start_probe(target['id']);wait(lambda:relay.probe_result is not None,'actual UE ray result')
  if not relay.probe_result:
   point=list(target['position_m']);point[2]-=3;jump(point);settle(1);relay.start_probe(target['id']);wait(lambda:relay.probe_result is not None,'alternate actual UE ray result')
  assert relay.probe_result,'Both casting positions are blocked by actual UE geometry'
  result['native_geometry_clear']=True;q=relay.read_report().get('position_m',pos());assert len(q)==3 and math.dist(q,pos())<5,'Native capsule and server pose differ too much'
  dx=target['position_m'][0]-q[0];dz=target['position_m'][2]-q[2];length=max(.001,math.hypot(dx,dz));send('move',position_m=q,forward_xz=[-dx/length,-dz/length],speed_mps=0,target_in_view=False,target_entity_id=target['id']);send('ui_use_slot',bar=2,slot=9);settle(.7)
  result['facing_away_rejected']=any('not visible' in m.lower() or 'see your target from here' in m.lower() for m in snapshot.get('messages',[])) and not (cast().get('name')=='Gleam Ray' and cast().get('phase') in ['casting','released'])
  assert result['facing_away_rejected'],'Enemy spell must not cast with the target behind the character'
  q=relay.read_report().get('position_m',pos())
  dx=target['position_m'][0]-q[0];dz=target['position_m'][2]-q[2];length=max(.001,math.hypot(dx,dz));send('move',position_m=q,forward_xz=[dx/length,dz/length],speed_mps=0,target_in_view=True,target_entity_id=target['id']);track_target=target['id'];before=float(target.get('health',1));send('ui_use_slot',bar=2,slot=9)
  try:wait(lambda:cast().get('phase')=='casting','damage cast start',3)
  except RuntimeError:
   if not any('invulnerability timer' in m.lower() for m in snapshot.get('messages',[])):raise
   wait(lambda:any('temporary invulnerability timer has expired' in m.lower() for m in snapshot.get('messages',[])),'normal immunity expiry',25);send('ui_use_slot',bar=2,slot=9);wait(lambda:cast().get('phase')=='casting','damage cast after normal immunity')
  wait(lambda:cast().get('phase')=='released','damage release');wait(lambda:any(e['id']==target['id'] and float(e.get('health',1))<before for e in snapshot['entities']) or any('Gleam Ray'in m and ('damage'in m or 'hit'in m) for m in snapshot.get('messages',[])),'real spell damage')
  result['damage']={'target':target['id'],'health_before':before,'health_after':next((e.get('health') for e in snapshot['entities'] if e['id']==target['id']),None),'messages':snapshot.get('messages',[])};result['damage_applied']=True
 else:result['damage_applied']=False;result['damage_limit']='No existing frog available in this snapshot'
 result['native_los_answers']=len(relay.answers);result['native_los_positive_answers']=sum(v.get('visible') is True for v in relay.answers)
 result['inventory_unchanged']=snapshot['inventory']['items']==baseline;result['passed']=result.get('movement_interrupted') and result.get('buff_applied') and result['inventory_unchanged']
except Exception:result['errors'].append(traceback.format_exc())
finally:
 if sock and session:
  try:
   track_target=''
   if jumped and home:jump(home);settle(.5)
   send('gm_test_mode',on=False,player_generation=snapshot.get('player_status',{}).get('generation',-1));settle(.5);send('logout')
  except Exception:result['errors'].append('Cleanup request failed');(L/'logout.request').write_text('logout',encoding='utf-8')
 elif p and p.poll() is None:(L/'logout.request').write_text('logout',encoding='utf-8')
 if p:
  try:p.wait(timeout=100)
  except subprocess.TimeoutExpired:result['errors'].append('Normal logout still pending; process preserved')
 if sock:sock.close()
 if relay:
  result['native_geometry_answers']=relay.answers;result['geometry_probes']=relay.probes
  try:result['native_exit']=relay.finish()
  except subprocess.TimeoutExpired:result['errors'].append('Native observer shutdown still pending')
 if saved_file:
  if had_file:saved_file.write_bytes(saved_bytes)
  elif saved_file.exists():saved_file.unlink()
  result['shortcuts_restored']=True
 try:
  f=json.loads((L/'godot_session.json').read_text(encoding='utf-8'));result.update(normal_logout=not f.get('playing',True),inventory_requests=f.get('inventory',{}).get('requests'),bridge_rejected=f.get('bridge_rejected'),move_rejected=f.get('move_rejected'),spell_packets=f.get('spell_cast_packets'),line_of_sight=f.get('line_of_sight'))
 except Exception:result['errors'].append('Final report missing')
 result['passed']=bool(result['passed'] and result.get('native_geometry_clear') and result.get('native_los_answers',0)>0 and result.get('damage_applied') and result.get('native_exit')==0 and result['normal_logout'] and result['inventory_requests']==0 and result['bridge_rejected']==0 and not result['errors']);(D/'native_live_spell_trace.json').write_text(json.dumps(trace),encoding='utf-8');(D/'native_live_spell_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result),flush=True)
 if not result['passed']:raise SystemExit(1)
