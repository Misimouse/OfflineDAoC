"""Read real item and ability details through the unchanged server Detail protocol."""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json,socket,subprocess,time,traceback
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/ui_integration';L=R/'Reports/live';session='';snapshot={};buffer=b'';serial=0;sock=None;p=None
result={'passed':False,'real_server':True,'normal_logout':False,'errors':[],'details':[]}
def pump():
 global buffer,snapshot,session
 try:b=sock.recv(1048576)
 except socket.timeout:return
 if not b:raise RuntimeError('Bridge closed')
 buffer+=b
 while b'\n' in buffer:
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
 serial+=1;sock.sendall((json.dumps(dict(type='command',session=session,id='detail-real:'+str(serial),action=action,**kw))+'\n').encode())
def ui():return snapshot.get('classic_ui',{})
try:
 with socket.socket() as guard:guard.bind(('127.0.0.1',19727))
 with(D/'real_details_launcher.log').open('w',encoding='utf-8') as log:
  p=subprocess.Popen([str(ENGINE / 'Binaries/ThirdParty/DotNet/10.0/win-x64/dotnet.exe'),str(R/'Launcher/bin/Release/net10.0/BridgeLauncher.dll'),'--character=BridgeFighter','--session-only'],cwd=R,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  end=time.monotonic()+85
  while time.monotonic()<end:
   try:sock=socket.create_connection(('127.0.0.1',19727),timeout=.2);break
   except OSError:time.sleep(.2)
  assert sock;sock.settimeout(.12);wait(lambda:ui().get('ready') and ui().get('skills_ready') and snapshot.get('inventory',{}).get('ready'),'real lists',85)
  baseline=snapshot['inventory']['items']
  for kind in ['item','ability']:
   e=next(x for x in ui()['entries'] if x['kind']==kind and (kind=='item' or x['name'].lower()=='sprint'))
   send('ui_detail',entry_id=e['id'],entry_token=e['token']);wait(lambda:ui().get('detail',{}).get('entry_id')==e['id'] and ui()['detail'].get('status')=='ready','real '+kind+' properties')
   detail=ui()['detail'];assert detail['lines'],'Empty server information'
   result['details'].append({'kind':kind,'entry':e['id'],'caption':detail['caption'],'lines':detail['lines']})
   saved=json.loads(json.dumps(snapshot));saved['session']='recorded-ui-details';(D/f'real_detail_{kind}_snapshot.json').write_text(json.dumps(saved),encoding='utf-8')
   send('ui_detail_close');wait(lambda:not ui().get('detail'),'close '+kind)
  result['inventory_unchanged']=snapshot['inventory']['items']==baseline;result['passed']=result['inventory_unchanged'] and len(result['details'])==2
except Exception:result['errors'].append(traceback.format_exc())
finally:
 if sock and session:
  try:send('logout')
  except Exception:result['errors'].append('Logout request failed')
 elif p and p.poll() is None:(L/'logout.request').write_text('logout',encoding='utf-8')
 if p:
  try:p.wait(timeout=100)
  except subprocess.TimeoutExpired:result['errors'].append('Normal logout still pending; process preserved')
 if sock:sock.close()
 try:
  f=json.loads((L/'godot_session.json').read_text(encoding='utf-8'));result['normal_logout']=not f.get('playing',True);result['inventory_requests']=f.get('inventory',{}).get('requests');result['bridge_rejected']=f.get('bridge_rejected')
 except Exception:result['errors'].append('Final report missing')
 result['passed']=bool(result['passed'] and result['normal_logout'] and result['inventory_requests']==0 and result['bridge_rejected']==0 and not result['errors']);(D/'real_details.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result),flush=True)
 if not result['passed']:raise SystemExit(1)
