"""Bounded GM melee protocol check against an existing neutral low-level worm.
No spawn, grant, balance change, DB edits, inventory operation or simulated hit.
"""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json,socket,subprocess,time,math,traceback
from pathlib import Path
R=Path(__file__).resolve().parent;O=R/'Reports/combat_visual';O.mkdir(exist_ok=True);LIVE=R/'Reports/live'
DOTNET=str(ENGINE / 'Binaries/ThirdParty/DotNet/10.0/win-x64/dotnet.exe')
snapshot={};buffer=b'';session='';serial=0;sock=None;process=None;baseline={};target_id='';trace=[];own={};original_pos=None
result={'real_server':True,'native_visual_session':False,'character':'BridgeFighter','errors':[],'steps':[],'normal_logout':False,'no_resource_grants':True}
def save():(O/'real_melee.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
def pump(duration=.15):
 global buffer,session,snapshot
 end=time.monotonic()+duration
 while time.monotonic()<end:
  try:data=sock.recv(1048576)
  except socket.timeout:continue
  if not data:raise RuntimeError('Bridge closed')
  buffer+=data
  while b'\n'in buffer:
   line,buffer=buffer.split(b'\n',1);value=json.loads(line)
   if value.get('type')=='hello':session=value['session']
   if value.get('type')=='snapshot':
    snapshot=value
    if target_id:
     rows=[r for r in value.get('entities',[])if r['id']in['player:local',target_id]]
     trace.append({'type':'snapshot','protocol':'daoc-visual-bridge','version':1,'session':'recorded-real-melee','seq':len(trace)+1,'zone_id':207,'origin_m':[1364,130,1263],'entities':rows,'player_status':value.get('player_status',{}),'inventory':value.get('inventory',{}),'at_s':time.monotonic()-started})
def wait(predicate,label,timeout=18):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  pump()
  if predicate():return
 raise RuntimeError('Timeout '+label)
def send(action,**values):
 global serial
 serial+=1;sock.sendall((json.dumps(dict(values,type='command',session=session,id='real-melee:'+str(serial),action=action))+'\n').encode())
def state():return snapshot.get('player_status',{})
def rows():return {r['id']:r for r in snapshot.get('entities',[])}
def personal():
 inv=snapshot.get('inventory',{});return {'items':inv.get('items',[]),'money':inv.get('money',{})}
def mark(text):result['steps'].append(text);save();print(text,flush=True)
def jump(point):send('chat',text='/jump to %d %d %d 200'%(round(point[0]*40)+35*8192,round(point[2]*40)+51*8192,round(point[1]*40)))
def estimate(row):
 p=list(row['position_m']);m=row.get('motion',{});goal=m.get('destination_m');speed=max(0,float(m.get('speed_mps',row.get('speed_mps',0))))
 if goal and len(goal)==3:
  delta=[goal[i]-p[i]for i in range(3)];distance=math.hypot(delta[0],delta[2]);travel=min(distance,speed*min(6,max(0,float(m.get('age_ms',0))/1000)))
  if distance>.001:p[0]+=delta[0]/distance*travel;p[2]+=delta[2]/distance*travel
 return p
started=time.monotonic()
try:
 with(O/'real_melee_stdout.log').open('w')as log:
  process=subprocess.Popen([DOTNET,str(R/'Launcher/bin/Release/net10.0/BridgeLauncher.dll'),'--character=BridgeFighter','--session-only'],cwd=R,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  end=time.monotonic()+80
  while time.monotonic()<end:
   if process.poll()is not None:raise RuntimeError('Launcher exited before bridge ready')
   try:sock=socket.create_connection(('127.0.0.1',19727),timeout=.2);break
   except OSError:time.sleep(.2)
  if sock is None:raise RuntimeError('No bridge listener')
  sock.settimeout(.12);wait(lambda:bool(session)and snapshot.get('in_game')and state().get('ready')and snapshot.get('inventory',{}).get('ready'),'real character state',80);pump(1)
  baseline=personal();original_pos=list(rows()['player:local']['position_m']);original_forward=list(rows()['player:local']['forward_xz']);original_sit=state()['vitals']['sitting']
  if original_sit:
   send('player_sit',on=False,player_generation=state()['generation']);wait(lambda:not state()['vitals']['sitting']and not state().get('posture_pending'),'standing')
  candidates=[r for r in rows().values()if r.get('kind')=='npc'and int(r.get('model_id',-1))==123 and int(r.get('realm',-1))==0 and int(r.get('level',127))<=2 and r.get('targetable',True)and float(r.get('health',0))>0]
  if not candidates:raise RuntimeError('No eligible existing neutral worm of level <=2; no substitute spawned')
  target=min(candidates,key=lambda r:(abs(float(r.get('speed_mps',0)))>.1,math.dist(r['position_m'],original_pos)));target_id=target['id'];target_oid=int(target_id.split(':')[1]);result['target']={k:target.get(k)for k in['id','name','model_id','level','realm']};mark('Existing neutral low-level worm selected from real server data')
  point=estimate(target);point[0]-=1.3;jump(point);wait(lambda:'player:local'in rows()and math.dist(rows()['player:local']['position_m'],point)<.5,'normal GM transfer beside target')
  send('target',entity_id=target_id);wait(lambda:snapshot.get('interaction',{}).get('target',{}).get('id')==target_id,'actual selected target')
  baseline_health=float(rows()[target_id]['health']);minimum_health=baseline_health;death_seen=False
  def face():
   data=rows();me=data['player:local'];t=data.get(target_id)
   if not t:return
   goal=estimate(t);p=me['position_m'];delta=[goal[0]-p[0],goal[2]-p[2]];length=math.hypot(*delta);forward=[v/length for v in delta]if length>.01 else[1,0]
   send('move',position_m=p,forward_xz=forward,speed_mps=0,target_entity_id=target_id,target_in_view=math.dist(p,goal)<=6)
  face();pump(.5);send('combat_attack',on=True,entity_id=target_id,player_generation=state()['generation']);mark('Original attack request sent; waiting for actual results')
  end=time.monotonic()+30
  while time.monotonic()<end:
   pump(.18);data=rows();t=data.get(target_id);local=data.get('player:local',{})
   for e in local.get('combat_visual',{}).get('events',[]):
    if e.get('kind')in['attack','style']and int(e.get('source_defender',0))==target_oid:own[int(e['seq'])]=e
   if t:
    minimum_health=min(minimum_health,float(t['health']));death_seen|=t.get('state')=='dead'or float(t['health'])<=0
   if death_seen or len(own)>=2 and minimum_health<baseline_health:break
   if not t:break
   if int(state().get('vitals',{}).get('health_pct',0))<70:raise RuntimeError('Bounded test stopped because player health fell below 70%')
   face()
  send('combat_attack',on=False);wait(lambda:not state().get('attack_on')and not state().get('attack_pending')and not state().get('attack_uncertain'),'server confirms attack stopped')
  result.update(actual_own_attack_announcements=len(own),attack_events=list(own.values()),target_initial_health=baseline_health,target_minimum_health=minimum_health,target_death_seen=death_seen,inventory_unchanged=personal()==baseline)
  result['passed']=bool(own and minimum_health<baseline_health)
  mark('Real combat collection ended; no local damage or results simulated')
except Exception:
 result['errors'].append(traceback.format_exc());result['passed']=False
finally:
 if sock is not None and session:
  try:
   send('combat_attack',on=False);pump(.4);send('target',entity_id='')
   if original_pos is not None:
    jump(original_pos);wait(lambda:'player:local'in rows()and math.dist(rows()['player:local']['position_m'],original_pos)<.6,'restore original GM location');send('move',position_m=rows()['player:local']['position_m'],forward_xz=original_forward,speed_mps=0,target_entity_id='',target_in_view=False)
    if original_sit:send('player_sit',on=True,player_generation=state()['generation']);pump(.5)
    result['original_position_restored']=True
   result['final_inventory']=personal();send('logout')
  except Exception:result['errors'].append('Cleanup: '+traceback.format_exc())
 (LIVE/'logout.request').write_text('logout')
 if process is not None:
  try:process.wait(timeout=100)
  except subprocess.TimeoutExpired:result['errors'].append('Normal logout pending; authenticated process preserved')
 if sock is not None:sock.close()
 try:
  final=json.loads((LIVE/'godot_session.json').read_text(encoding='utf-8-sig'));result['normal_logout']=not final.get('playing',True)and'protocolo normal'in final.get('status','');result['bridge_rejected']=final.get('bridge_rejected');result['move_rejected']=final.get('move_rejected');result['inventory_requests']=final.get('inventory',{}).get('requests');result['feedback']=final.get('messages',[]);result['combat_visual']=final.get('combat_visual')
 except Exception:result['errors'].append('Missing final session report')
 result['passed']=bool(result.get('passed')and result['normal_logout']and result.get('original_position_restored')and not result['errors']);save();(O/'real_melee_trace.json').write_text(json.dumps(trace));print(json.dumps({k:v for k,v in result.items()if k not in['final_inventory','attack_events']},ensure_ascii=False),flush=True)
 if not result['passed']:raise SystemExit(1)
