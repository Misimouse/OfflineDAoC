"""Real GM protected/combat acknowledgements and bounded NPC retaliation test."""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json,socket,subprocess,time,math,traceback
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/gm_mode';LIVE=R/'Reports/live';session='';snapshot={};buffer=b'';serial=0;sock=None;proc=None;original=None;original_forward=None;initial_inventory=None;target=''
result={'passed':False,'real_server':True,'native_visual_session':False,'errors':[],'steps':[],'normal_logout':False,'no_grants':True,'inventory_requests':0}
def save():(D/'live_verification.json').write_text(json.dumps(result,indent=2))
def step(label):result['steps'].append(label);save();print(label,flush=True)
def pump(seconds=.15):
 global buffer,session,snapshot
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  try:data=sock.recv(1048576)
  except socket.timeout:continue
  if not data:raise RuntimeError('Bridge session closed')
  buffer+=data
  while b'\n' in buffer:
   raw,buffer=buffer.split(b'\n',1);v=json.loads(raw)
   if v.get('type')=='hello':session=v['session']
   if v.get('type')=='snapshot':snapshot=v

def send(action,**values):
 global serial
 serial+=1;sock.sendall((json.dumps(dict(type='command',session=session,id='gm-live:'+str(serial),action=action,**values))+'\n').encode())
def wait(fn,label,timeout=25):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  pump()
  if fn():return
 raise RuntimeError('Timeout '+label)
def state():return snapshot.get('player_status',{})
def gm():return state().get('gm_mode',{})
def rows():return {x['id']:x for x in snapshot.get('entities',[])}
def hp():return int(state().get('vitals',{}).get('health_pct',0))
def jump(p):send('chat',text='/jump to %d %d %d 200'%(round(p[0]*40)+35*8192,round(p[2]*40)+51*8192,round(p[1]*40)))
def mode(combat):
 send('gm_test_mode',on=combat,player_generation=state()['generation']);wait(lambda:gm().get('ready') and not gm().get('pending'),'mode reply')
 if bool(gm().get('combat_test'))!=combat:raise RuntimeError('Server refused mode: '+str(gm().get('feedback')))
def estimate(row):
 p=list(row['position_m']);m=row.get('motion',{});goal=m.get('destination_m');speed=max(0,float(m.get('speed_mps',row.get('speed_mps',0))))
 if goal and len(goal)==3:
  dx=goal[0]-p[0];dz=goal[2]-p[2];n=math.hypot(dx,dz);travel=min(n,speed*min(6,max(0,float(m.get('age_ms',0))/1000)))
  if n>.001:p[0]+=dx/n*travel;p[2]+=dz/n*travel
 return p

def face():
 p=rows()['player:local']['position_m'];t=estimate(rows()[target]) if target in rows() else p;dx=t[0]-p[0];dz=t[2]-p[2];n=max(math.hypot(dx,dz),.001)
 send('move',position_m=p,forward_xz=[dx/n,dz/n],speed_mps=0,target_entity_id=target,target_in_view=n<=6)
try:
 with socket.socket() as s:s.settimeout(.4);assert s.connect_ex(('127.0.0.1',19727))!=0,'A game session is already active'
 log=(D/'live_launcher.log').open('w');proc=subprocess.Popen([str(ENGINE / 'Binaries/ThirdParty/DotNet/10.0/win-x64/dotnet.exe'),str(R/'Launcher/bin/Release/net10.0/BridgeLauncher.dll'),'--character=BridgeFighter','--session-only'],cwd=R,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 end=time.monotonic()+85
 while time.monotonic()<end:
  if proc.poll() is not None:raise RuntimeError('Launcher exited before connection')
  try:sock=socket.create_connection(('127.0.0.1',19727),timeout=.2);break
  except OSError:time.sleep(.2)
 assert sock is not None;sock.settimeout(.12)
 wait(lambda:bool(session) and snapshot.get('in_game') and state().get('ready') and gm().get('ready'),'normal protected GM entry',85)
 pump(2);original=list(rows()['player:local']['position_m']);original_forward=rows()['player:local']['forward_xz'];initial_inventory=snapshot.get('inventory',{}).get('items',[])
 assert not gm().get('combat_test');step('Entry confirmed GM protected by the real server')
 candidates=[x for x in rows().values() if x.get('kind')=='npc' and float(x.get('health',0))>0 and int(x.get('realm',0))!=3 and 1<=int(x.get('level',0))<=3 and any(n in x.get('name','').lower() for n in ['frog','worm','skeletal pawn','mudman'])]
 assert candidates,'No existing low-level test mob in range'
 candidates.sort(key=lambda x:(0 if 'frog' in x.get('name','').lower() else 1,abs(float(x.get('speed_mps',0))),abs(int(x.get('level',0))-2),math.dist(x['position_m'],original)))
 row=candidates[0];target=row['id'];result['target']={k:row.get(k) for k in ['id','name','model_id','level']};pos=list(row['position_m']);goal=[pos[0]-1.2,pos[1],pos[2]];jump(goal)
 wait(lambda:math.dist(rows()['player:local']['position_m'],goal)<.7,'authoritative test position');send('target',entity_id=target);wait(lambda:snapshot.get('interaction',{}).get('target',{}).get('id')==target,'server target')
 end=time.monotonic()+60
 while time.monotonic()<end:
  if not gm().get('pending'):send('gm_test_mode',on=True,player_generation=state()['generation'])
  pump(1)
  if gm().get('ready') and gm().get('combat_test') and not gm().get('pending'):break
 assert gm().get('combat_test'),'Combat mode not enabled';step('Real server confirmed combat test; GM privileges still allow return command')
 pos=estimate(rows()[target]);goal=[pos[0]-1.1,pos[1],pos[2]];jump(goal);wait(lambda:math.dist(rows()['player:local']['position_m'],goal)<.7,'fresh close position after mode acknowledgement');pump(.3)
 if not gm().get('combat_test'):mode(True)
 result['distance_at_attack_m']=math.dist(rows()['player:local']['position_m'],estimate(rows()[target]));assert result['distance_at_attack_m']<=5.5,'Test target moved away before attack'
 before=hp();result['player_health_before']=before;face();pump(.2);send('combat_attack',on=True,entity_id=target,player_generation=state()['generation']);step('One bounded attack requested against an existing mob')
 sent_stop=False;seen_hit=False;end=time.monotonic()+22
 while time.monotonic()<end:
  pump(.15);t=rows().get(target)
  if t is None or float(t.get('health',0))<=0:result['target_died_before_retaliation']=True;break
  if not sent_stop and float(t.get('health',1))<1:
   send('combat_attack',on=False);sent_stop=True;step('Player attack stopped after first actual hit; waiting for NPC retaliation')
  if hp()<before:seen_hit=True;result['player_health_after_npc_hit']=hp();break
  if hp()<40:break
  face()
 send('combat_attack',on=False);mode(False);step('Protection re-enabled and acknowledged by real server')
 protected_hp=hp();pump(2);result['health_stable_after_protection']=hp()>=protected_hp;result['npc_damage_verified']=seen_hit;result['protected_return_verified']=not gm().get('combat_test');result['inventory_unchanged']=snapshot.get('inventory',{}).get('items',[])==initial_inventory
 result['passed']=seen_hit and result['protected_return_verified'] and result['health_stable_after_protection'];save()
except Exception:result['errors'].append(traceback.format_exc())
finally:
 if sock is not None and session:
  try:
   send('combat_attack',on=False)
   if state():send('gm_test_mode',on=False,player_generation=state().get('generation',-1));pump(.7)
   send('target',entity_id='')
   if original is not None and hp()>0:
    jump(original);wait(lambda:math.dist(rows()['player:local']['position_m'],original)<.7,'restore original position');result['original_position_restored']=True
    send('move',position_m=original,forward_xz=original_forward,speed_mps=0,target_entity_id='',target_in_view=False)
   send('logout')
  except Exception:result['errors'].append('Cleanup: '+traceback.format_exc())
 if proc is not None:
  try:proc.wait(timeout=100)
  except subprocess.TimeoutExpired:result['errors'].append('Normal logout still pending; authenticated process preserved')
 if sock is not None:sock.close()
 try:
  d=json.loads((LIVE/'godot_session.json').read_text(encoding='utf-8-sig'));result['normal_logout']=not d.get('playing',True) and 'protocolo normal' in d.get('status','');result['final_gm_mode']=d.get('gm_mode');result['attack_visibility']=d.get('attack_visibility');result['messages']=d.get('interaction',{}).get('messages',[])[-8:];result['bridge_rejected']=d.get('bridge_rejected');result['inventory_requests']=d.get('inventory',{}).get('requests',0)
 except Exception:result['errors'].append('Final report unavailable')
 result['passed']=bool(result['passed'] and result['normal_logout'] and not result['errors']);save();print(json.dumps(result),flush=True)
 if not result['passed']:raise SystemExit(1)
