"""Render the actual server death/release trace; no account, artificial health or commands."""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json,socket,subprocess,time,math,copy
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/release_roundtrip';trace=json.loads((D/'actual_release_trace.json').read_text(encoding='utf-8'));proof=json.loads((D/'live_verification.json').read_text(encoding='utf-8'));assert proof['passed']
def hp(v):return v.get('player_status',{}).get('vitals',{}).get('health_pct',-1)
def me(v):return next((x for x in v.get('entities',[])if x['id']=='player:local'),None)
dead=next(i for i,v in enumerate(trace)if hp(v)==0 and v.get('player_status',{}).get('ready'))
returned=next(i for i in range(dead+1,len(trace))if hp(trace[i])>0 and trace[i].get('player_status',{}).get('ready')and me(trace[i])and math.dist(me(trace[i])['position_m'],proof['returned_position'])<.5)
outside=next((i for i in range(dead+1,returned)if hp(trace[i])>0 and not me(trace[i])),None)
phases=[('before_death',trace[dead-1],6),('dead',trace[dead],6)]
if outside is not None:phases.append(('released_outside_connacht',trace[outside],4))
phases.append(('returned',trace[returned],13))
listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1);listener.settimeout(110);port=listener.getsockname()[1]
report=D/'native_replay_current.json';start=time.time();captures={};seq=0
I=Path(str(INSTALL / 'new-client/godot'))
cmd=[str(ENGINE / 'Binaries/Win64/UnrealEditor-Cmd.exe'),str(R/'Client/DAoCBridgeClient.uproject'),'/Game/DAoC/Connacht_v01/Ardee_Nwiro_Prueba','-game','-DaocBridge','-DaocBridgeReadOnly','-DaocBridgePort='+str(port),'-DaocBridgeCatalog='+str(R/'models.json'),'-DaocBridgeEquipmentCatalog='+str(R/'equipment_catalog_v01.json'),'-DaocBridgeCollisionCatalog='+str(R/'collision_catalog.json'),'-DaocBridgeHeights='+str(I/'content/zones/zone207/heights.f32'),'-DaocBridgeReport='+str(report),'-DaocBridgeQuality=accessible','-DaocBridgeProfile','-DaocBridgeProfileFixed','-DaocBridgeProfileSeconds=32','-DaocBridgeCapture='+str(D/'Native_Release_Return.png'),'-windowed','-ResX=1280','-ResY=720','-d3d11','-nosplash','-nosound','-unattended']
def read():
 try:
  b=report.read_bytes();return json.loads(b.decode('utf-16'if b[:2]in[b'\xff\xfe',b'\xfe\xff']else'utf-8-sig'))
 except (OSError,ValueError):return {}
with(D/'native_replay.log').open('w',encoding='utf-8')as log:
 p=subprocess.Popen(cmd,cwd=R,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 peer=None
 try:
  peer,_=listener.accept();peer.settimeout(.001);peer.sendall((json.dumps(dict(type='hello',protocol='daoc-visual-bridge',version=1,session='actual-release-replay'))+'\n').encode())
  for name,value,seconds in phases:
   v=copy.deepcopy(value);v['session']='actual-release-replay';v.pop('recorded_at_s',None);end=time.monotonic()+seconds
   while time.monotonic()<end and p.poll()is None:
    seq+=1;v['seq']=seq;peer.sendall((json.dumps(v)+'\n').encode())
    try:peer.recv(65536)
    except socket.timeout:pass
    time.sleep(.1)
   captures[name]=read();print('Native phase',name,flush=True)
  last=copy.deepcopy(phases[-1][1]);last['session']='actual-release-replay'
  while p.poll()is None and time.time()-start<160:
   seq+=1;last['seq']=seq
   try:peer.sendall((json.dumps(last)+'\n').encode())
   except (ConnectionError,OSError):break
   time.sleep(.1)
  p.wait(timeout=30)
 finally:
  if peer:peer.close()
  listener.close()
(D/'native_replay_phases.json').write_text(json.dumps(captures,indent=2),encoding='utf-8')
final=captures.get('returned',{});position=final.get('position_m',[]);camera=final.get('camera_position_m',[])
result={'passed':False,'real_server_trace':True,'live_native_account':False,'phase_count':len(captures),'native_exit':p.returncode,'returned_position':position,'camera_position':camera,'view_target_is_bridge_camera':final.get('view_target_is_bridge_camera'),'camera_attached_to_player':final.get('camera_attached_to_player'),'recorded_death_position':proof['death_position'],'recorded_return_position':proof['returned_position']}
if len(position)==3 and len(camera)==3:
 result['camera_to_player_m']=math.dist(position,camera);result['player_to_server_return_m']=math.dist(position,proof['returned_position']);result['camera_to_death_m']=math.dist(camera,proof['death_position'])
 result['passed']=bool(p.returncode==0 and result['view_target_is_bridge_camera']and result['camera_attached_to_player']and result['camera_to_player_m']<6 and result['player_to_server_return_m']<1 and result['camera_to_death_m']>15)
(D/'native_actual_trace_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result),flush=True);assert result['passed']
