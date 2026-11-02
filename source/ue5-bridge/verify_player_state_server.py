"""Reversible normal-protocol posture/weapon-mode check, without attacking a target."""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json,socket,subprocess,time,traceback
from pathlib import Path
R=Path(__file__).resolve().parent;O=R/'Reports/player_state';O.mkdir(exist_ok=True);LIVE=R/'Reports/live'
DOTNET=str(ENGINE / 'Binaries/ThirdParty/DotNet/10.0/win-x64/dotnet.exe')
snapshot={};buffer=b'';session='';serial=0;sock=None;process=None;baseline={}
result={'real_server':True,'character':'BridgeFighter','steps':[],'errors':[],'normal_logout':False}
def save():(O/'server_verification.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
def pump(duration=.15):
 global buffer,session,snapshot
 end=time.monotonic()+duration
 while time.monotonic()<end:
  try:data=sock.recv(1048576)
  except socket.timeout:continue
  if not data:raise RuntimeError('Bridge closed')
  buffer+=data
  while b'\n' in buffer:
   line,buffer=buffer.split(b'\n',1);value=json.loads(line)
   if value.get('type')=='hello':session=value['session']
   if value.get('type')=='snapshot':snapshot=value
def state():return snapshot.get('player_status',{})
def wait(predicate,label,timeout=18):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  pump()
  if predicate():return
 raise RuntimeError('Timeout '+label+': '+state().get('feedback',''))
def send(action,**values):
 global serial
 serial+=1;sock.sendall((json.dumps(dict(values,type='command',session=session,id='state-probe:'+str(serial),action=action))+'\n').encode())
def mark(label):
 result['steps'].append({'step':label,'state':state()});save();print(label,flush=True)
def personal():
 inv=snapshot.get('inventory',{})
 return {'items':inv.get('items',[]),'money':inv.get('money',{})}
def posture(on):
 send('player_sit',on=on,player_generation=state()['generation'])
 wait(lambda:not state().get('posture_pending') and not state().get('posture_uncertain') and state().get('vitals',{}).get('sitting')==on,'posture '+str(on))
def attack(on):
 send('combat_attack',on=on,entity_id='',player_generation=state()['generation'])
 wait(lambda:not state().get('attack_pending') and not state().get('attack_uncertain') and state().get('attack_on')==on,'attack mode '+str(on))
try:
 with (O/'server_probe_stdout.log').open('w')as log:
  process=subprocess.Popen([DOTNET,str(R/'Launcher/bin/Release/net10.0/BridgeLauncher.dll'),'--character=BridgeFighter','--session-only'],cwd=R,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  end=time.monotonic()+80
  while time.monotonic()<end:
   if process.poll()is not None:raise RuntimeError('Launcher exited before bridge ready')
   try:sock=socket.create_connection(('127.0.0.1',19727),timeout=.2);break
   except OSError:time.sleep(.2)
  if sock is None:raise RuntimeError('No bridge listener')
  sock.settimeout(.12)
  wait(lambda:bool(session) and snapshot.get('in_game') and state().get('ready') and snapshot.get('inventory',{}).get('ready'),'authoritative state',80)
  pump(1);baseline=personal();original_sit=state()['vitals']['sitting'];mark('Real vitals and inventory received')
  send('target',entity_id='');pump(.4)
  posture(True);mark('Sitting confirmed by server')
  if snapshot.get('max_speed_mps',-1)!=0:raise RuntimeError('Seated speed is not zero')
  posture(False);mark('Standing confirmed by server')
  attack(True);mark('Weapon mode enabled without a target')
  attack(False);mark('Weapon mode stopped by server')
  if original_sit:posture(True)
  result['inventory_unchanged']=personal()==baseline
  result['passed']=result['inventory_unchanged']
except Exception:
 result['errors'].append(traceback.format_exc());result['passed']=False
finally:
 if sock is not None and session:
  try:
   send('combat_attack',on=False)
   if baseline and state().get('ready'):posture(original_sit)
   result['final_inventory_unchanged']=personal()==baseline if baseline else False
   send('logout')
  except Exception:result['errors'].append('Cleanup: '+traceback.format_exc())
 (LIVE/'logout.request').write_text('logout')
 if process is not None:
  try:process.wait(timeout=100)
  except subprocess.TimeoutExpired:result['errors'].append('Normal logout pending; process preserved')
 if sock is not None:sock.close()
 try:
  final=json.loads((LIVE/'godot_session.json').read_text(encoding='utf-8-sig'));result['normal_logout']=not final.get('playing',True) and 'protocolo normal' in final.get('status','');result['player_status']=final.get('player_status');result['bridge_rejected']=final.get('bridge_rejected');result['player_state_requests']=final.get('player_state_requests');result['player_state_rejected']=final.get('player_state_rejected')
 except Exception:result['errors'].append('Missing final session report')
 result['passed']=bool(result.get('passed') and result['normal_logout'] and not result['errors']);save();print(json.dumps(result,ensure_ascii=False),flush=True)
 if not result['passed']:raise SystemExit(1)
