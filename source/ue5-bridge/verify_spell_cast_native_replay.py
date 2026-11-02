"""Render the actual successful spell trace in the installed client, without a live account."""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json,socket,subprocess,time,bisect,math,copy
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/spell_casting';proof=json.loads((D/'real_spell_verification.json').read_text(encoding='utf-8'));assert proof['passed'] and proof['damage_applied'];raw=json.loads((D/'real_spell_trace.json').read_text(encoding='utf-8'));trace=[v for v in raw if v['snapshot'].get('in_game') and any(e['id']=='player:local' for e in v['snapshot'].get('entities',[]))]
first=trace[0]['at'];last_cast=max(v['at'] for v in trace if v['snapshot'].get('classic_ui',{}).get('casting'));duration=min(trace[-1]['at']-first,last_cast-first+4);times=[v['at']-first for v in trace];profile=max(45,math.ceil(duration+25));report=D/'native_spell_current.json';start=time.time();samples=[];seq=0
listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1);listener.settimeout(100);port=listener.getsockname()[1]
I=Path(str(INSTALL / 'new-client/godot'))
cmd=[str(ENGINE / 'Binaries/Win64/UnrealEditor-Cmd.exe'),str(R/'Client/DAoCBridgeClient.uproject'),'/Game/DAoC/Connacht_v01/Ardee_Nwiro_Prueba','-game','-DaocBridge','-DaocBridgeReadOnly','-DaocBridgeSpellVisualTest','-DaocBridgePort='+str(port),'-DaocBridgeCatalog='+str(R/'models.json'),'-DaocBridgeEquipmentCatalog='+str(R/'equipment_catalog_v01.json'),'-DaocBridgeCollisionCatalog='+str(R/'collision_catalog.json'),'-DaocBridgeHeights='+str(I/'content/zones/zone207/heights.f32'),'-DaocBridgeReport='+str(report),'-DaocBridgeCapture='+str(D/'Spell_Overview.png'),'-DaocBridgeQuality=accessible','-DaocBridgeProfile','-DaocBridgeProfileFixed','-DaocBridgeProfileSeconds='+str(profile),'-windowed','-ResX=1920','-ResY=1080','-d3d11','-nosplash','-nosound','-unattended']
def read():
 try:
  b=report.read_bytes();return json.loads(b.decode('utf-16' if b[:2] in [b'\xff\xfe',b'\xfe\xff'] else 'utf-8-sig'))
 except (OSError,ValueError):return {}
def send(v):
 global seq
 seq+=1;s=copy.deepcopy(v);s['session']='actual-spell-replay';s['seq']=seq;peer.settimeout(10);peer.sendall((json.dumps(s)+'\n').encode());peer.settimeout(.001)
 try:peer.recv(65536)
 except socket.timeout:pass
 samples.append(read())
with(D/'native_spell_replay.log').open('w',encoding='utf-8') as log:
 p=subprocess.Popen(cmd,cwd=R,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);peer=None
 try:
  peer,_=listener.accept();peer.settimeout(10);peer.sendall((json.dumps(dict(type='hello',protocol='daoc-visual-bridge',version=1,session='actual-spell-replay'))+'\n').encode());warm=time.monotonic();ready=None
  while p.poll() is None and time.monotonic()-warm<40:
   send(trace[0]['snapshot'])
   if read().get('local_animation'):
    if ready is None:ready=time.monotonic()
    if time.monotonic()-ready>2:break
   time.sleep(.1)
  began=time.monotonic()
  while p.poll() is None and time.monotonic()-began<duration:
   index=max(0,bisect.bisect_right(times,time.monotonic()-began)-1);send(trace[index]['snapshot']);time.sleep(.04)
  idle=trace[min(len(trace)-1,max(0,bisect.bisect_right(times,duration)-1))]['snapshot']
  while p.poll() is None and time.time()-start<200:
   try:send(idle)
   except OSError:break
   time.sleep(.1)
  p.wait(timeout=35)
 finally:
  if peer:peer.close()
  listener.close()
shots=[p.name for p in D.glob('Spell_*_*.png') if p.stat().st_mtime>=start];animations=sorted(set(s.get('local_animation','') for s in samples));phases=sorted(set(s.get('classic_ui',{}).get('casting',{}).get('phase','') for s in samples));result={'passed':p.returncode==0 and len(shots)>=3 and any(a.startswith('cast_') for a in animations) and 'casting' in phases and 'interrupted' in phases and 'released' in phases,'real_server_trace':True,'live_native_account':False,'native_exit':p.returncode,'trace_seconds':duration,'animations':animations,'phases':phases,'captures':shots};(D/'native_spell_samples.json').write_text(json.dumps(samples),encoding='utf-8');(D/'native_spell_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result),flush=True);assert result['passed']
