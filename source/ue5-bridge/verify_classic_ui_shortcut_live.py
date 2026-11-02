"""Real known Sprint via shortcut, then restore shortcuts and stop normally. No item operations."""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json,socket,subprocess,time,hashlib,traceback
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/ui_integration';L=R/'Reports/live';session='';snapshot={};buffer=b'';serial=0;sock=None;p=None;original_file=None;file_bytes=None;had_file=False;used=False;baseline_items=None
result={'passed':False,'real_server':True,'normal_logout':False,'errors':[],'inventory_requests':0}
def pump(seconds=.1):
 global buffer,snapshot,session
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  try:b=sock.recv(1048576)
  except socket.timeout:continue
  if not b:raise RuntimeError('Bridge closed')
  buffer+=b
  while b'\n'in buffer:
   line,buffer=buffer.split(b'\n',1);v=json.loads(line)
   if v.get('type')=='hello':session=v['session']
   if v.get('type')=='snapshot':snapshot=v

def wait(fn,label,timeout=20):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  pump()
  if fn():return
 raise RuntimeError('Timeout '+label)
def send(action,**kw):
 global serial
 serial+=1;sock.sendall((json.dumps(dict(type='command',session=session,id='ui-real:'+str(serial),action=action,**kw))+'\n').encode())
def ui():return snapshot.get('classic_ui',{})
try:
 with socket.socket()as guard:guard.bind(('127.0.0.1',19727))
 log=(D/'real_shortcut_launcher.log').open('w',encoding='utf-8');p=subprocess.Popen([str(ENGINE / 'Binaries/ThirdParty/DotNet/10.0/win-x64/dotnet.exe'),str(R/'Launcher/bin/Release/net10.0/BridgeLauncher.dll'),'--character=BridgeFighter','--session-only'],cwd=R,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 end=time.monotonic()+85
 while time.monotonic()<end:
  try:sock=socket.create_connection(('127.0.0.1',19727),timeout=.2);break
  except OSError:time.sleep(.2)
 assert sock;sock.settimeout(.12);wait(lambda:ui().get('ready')and ui().get('skills_ready')and snapshot.get('inventory',{}).get('ready')and snapshot.get('player_status',{}).get('ready'),'real lists',85)
 baseline_items=snapshot['inventory']['items'];name=ui()['character'];original_file=R/'Client/Saved/ClassicUI'/(hashlib.sha256(name.lower().encode()).hexdigest()+'.json');had_file=original_file.exists();file_bytes=original_file.read_bytes()if had_file else None
 e=next(x for x in ui()['entries']if x['name'].lower()=='sprint'and x['kind']=='ability');bar=2;bank=ui()['banks'][bar];slot=9;old=ui()['bars'][bar][bank][slot]
 send('ui_assign',bar=bar,bank=bank,slot=slot,entry_id=e['id'],entry_token=e['token']);wait(lambda:ui()['bars'][bar][bank][slot].get('id')==e['id'],'binding acknowledgement')
 send('chat',text='/gmstealth off');pump(.7)
 baseline=list(snapshot.get('messages',[]));send('ui_use_slot',bar=bar,slot=slot);used=True
 wait(lambda:any('sprint'in m.lower()and 'prepar'in m.lower()and m not in baseline for m in snapshot.get('messages',[])),'original Sprint response')
 result['server_sprint_response']=[m for m in snapshot.get('messages',[])if 'sprint'in m.lower()and 'prepar'in m.lower()and m not in baseline];result['known_entry']=e['id'];result['slot_assignment_acknowledged']=True
 send('ui_use_slot',bar=bar,slot=slot);used=False;pump(.7)
 if old and old.get('token'):send('ui_assign',bar=bar,bank=bank,slot=slot,entry_id=old['id'],entry_token=old['token'])
 else:send('ui_clear',bar=bar,bank=bank,slot=slot)
 pump(.4);result['inventory_unchanged']=snapshot['inventory']['items']==baseline_items;result['passed']=bool(result['server_sprint_response']and result['inventory_unchanged'])
except Exception:result['errors'].append(traceback.format_exc())
finally:
 if sock and session:
  try:
   if used:send('ui_use_slot',bar=2,slot=9);pump(.2)
   send('gm_test_mode',on=False,player_generation=snapshot.get('player_status',{}).get('generation',-1));pump(.4)
   send('logout')
  except Exception:result['errors'].append('Normal logout request failed')
 if p:
  try:p.wait(timeout=100)
  except subprocess.TimeoutExpired:result['errors'].append('Logout still pending; process preserved')
 if sock:sock.close()
 if original_file is not None:
  if had_file:original_file.write_bytes(file_bytes)
  elif original_file.exists():original_file.unlink()
  result['original_shortcut_file_restored']=True
 try:
  final=json.loads((L/'godot_session.json').read_text(encoding='utf-8'));result['normal_logout']=not final.get('playing',True);result['inventory_requests']=final.get('inventory',{}).get('requests');result['bridge_rejected']=final.get('bridge_rejected')
 except Exception:result['errors'].append('Final report unavailable')
 result['passed']=bool(result['passed']and result['normal_logout']and result['inventory_requests']==0 and not result['errors']);(D/'real_shortcut_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result),flush=True)
 if not result['passed']:raise SystemExit(1)
