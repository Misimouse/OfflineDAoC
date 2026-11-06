"""Test-only relay: real UE geometry answers server LOS; all other native commands are ignored."""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json,socket,select,subprocess,time,hashlib
from pathlib import Path
class NativeSightRelay:
 def __init__(self,backend,root,session,snapshot,output=None,duration=120,entity_ids=None,render=True,native_profile=None):
  folder=Path(output) if output is not None else root/'Reports/training_staff_fx_pets'
  assert folder.resolve().is_relative_to((root/'Reports').resolve()) and 30<=duration<=180
  folder.mkdir(parents=True,exist_ok=True)
  self.native_profile=native_profile
  self.entity_ids=set(entity_ids) if entity_ids is not None else None
  self.backend=backend;self.root=root;self.session=session;self.ue=None;self.bbuf=b'';self.ubuf=b'';self.answers=[];self.questions={};self.probes=[];self.probe=None;self.probe_result=None;self.probe_serial=0;self.report=folder/'live_native_current.json';self.report.unlink(missing_ok=True)
  self.listener=socket.socket();self.listener.bind(('127.0.0.1',0));self.listener.listen(1);self.listener.settimeout(100);port=self.listener.getsockname()[1]
  self.log=(folder/'live_native.log').open('w',encoding='utf-8');I=Path(str(INSTALL / 'new-client/godot'))
  cmd=[str(ENGINE / 'Binaries/Win64/UnrealEditor-Cmd.exe'),str(root/'GMCombatTest/NativeHost/BridgeGmHost.uproject'),'/Game/DAoC/Connacht_v01/Ardee_Nwiro_Prueba','-game','-DaocBridge','-DaocBridgeReadOnly','-DaocBridgeSpellVisualTest','-DaocBridgePort='+str(port),'-DaocBridgeCatalog='+str(root/'models.json'),'-DaocBridgeEquipmentCatalog='+str(root/'equipment_catalog_v01.json'),'-DaocBridgeCollisionCatalog='+str(root/'collision_catalog.json'),'-DaocBridgeHeights='+str(I/'content/zones/zone207/heights.f32'),'-DaocBridgeReport='+str(self.report),'-DaocBridgeCapture='+str(folder/'Live_Spell.png'),'-DaocBridgeQuality=accessible','-DaocBridgeProfile','-DaocBridgeProfileFixed','-DaocBridgeProfileSeconds='+str(duration),'-windowed','-ResX=1280','-ResY=720','-d3d11','-nosplash','-nosound','-unattended']
  if not render:cmd.remove('-d3d11');cmd.extend(['-nullrhi','-ExecCmds=t.IdleWhenNotForeground 0'])
  elif output is not None:cmd.append('-RenderOffscreen')
  if native_profile is not None:
   assert native_profile in ['expansion_forms','central_expansion_forms','spell_audio'] and render and output is not None
   host=root/'ExpansionRaceLab/FormLiveHost/FormLiveHost.uproject'
   assert host.exists()
   review=root/'ExpansionRaceLab/MinotaurOwnerReview'
   if native_profile=='central_expansion_forms':
    host=root/'ExpansionRaceLab/CentralInstalledHost/CentralInstalledHost.uproject'
    plugin=root/'Client/Plugins/DAoCVisualBridge'
    digest=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
    assert host.exists()
    assert (host.parent/'Content').is_junction() and (host.parent/'Content').resolve()==(root.parent/'DAoC-Enhanced-Unreal/Content').resolve()
    assert (host.parent/'Plugins/DAoCVisualBridge/Content').is_junction() and (host.parent/'Plugins/DAoCVisualBridge/Content').resolve()==(plugin/'Content').resolve()
    for name in ['UnrealEditor-DAoCVisualBridge.dll','UnrealEditor.modules']:
     assert digest(host.parent/'Plugins/DAoCVisualBridge/Binaries/Win64'/name)==digest(plugin/'Binaries/Win64'/name)
   if native_profile=='spell_audio':
    host=root/'SpellAudioLab/NativeHost/SpellAudioHost.uproject'
    assert host.exists()
   cmd[1]=str(host);cmd[2]='/Game/DAoC/Connacht_v01/Ardee_Nwiro_Prueba_Limpieza_v01'
   cmd.remove('-DaocBridgeSpellVisualTest')
   replacements={'-DaocBridgeCatalog=':review/'models.json','-DaocBridgeEquipmentCatalog=':review/'equipment_catalog.json'}
   appearance=review/'appearance_catalog.json'
   if native_profile in ['central_expansion_forms','spell_audio']:
    plugin=root/'Client/Plugins/DAoCVisualBridge'
    replacements={'-DaocBridgeCatalog=':root/'models.json','-DaocBridgeEquipmentCatalog=':root/'equipment_catalog_v01.json'}
    appearance=plugin/'Content/ClassicUI/Pregame/appearance_catalog.json'
   if native_profile=='spell_audio':
    cmd.remove('-nosound')
    cmd.append('-AudioMixer')
    cmd.append('-DaocBridgeSoundCatalog='+str(root/'SpellAudioLab/OriginalAudio_v01/sounds.json'))
   for i,value in enumerate(cmd):
    for flag,path in replacements.items():
     if value.startswith(flag):cmd[i]=flag+str(path)
   cmd.extend(['-DaocBridgeVisualProbe','-DaocBridgeLobbyAppearance='+str(appearance)])
  self.process=subprocess.Popen(cmd,cwd=root,stdout=self.log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);self.ue,_=self.listener.accept();self.ue.settimeout(10);self.ue.sendall((json.dumps(dict(type='hello',protocol='daoc-visual-bridge',version=1,session=session))+'\n'+json.dumps(self.native_snapshot(snapshot))+'\n').encode());self.ue.setblocking(False);self.ue.setsockopt(socket.SOL_SOCKET,socket.SO_SNDBUF,65536);self.pending=b'';self.latest=b''
 def native_snapshot(self,value):
  if self.entity_ids is None:return value
  native=dict(value);native['entities']=[e for e in value.get('entities',[]) if e['id'] in self.entity_ids]
  # Limit the observer to the tested actors; the real backend/player still
  # receives the entire world. This never manufactures a visibility reply.
  native.pop('qa_skill_audit',None)
  if self.native_profile not in ['expansion_forms','central_expansion_forms','spell_audio']:native.pop('classic_ui',None)
  return native
 def sendall(self,data):self.backend.sendall(data)
 def settimeout(self,value):self.backend.settimeout(value)
 def recv(self,size):
  if not self.pending and self.latest:self.pending=self.latest;self.latest=b''
  ready,writable,_=select.select([self.backend,self.ue],[self.ue] if self.pending else [],[],.03)
  if self.ue in writable:
   try:self.pending=self.pending[self.ue.send(self.pending):]
   except BlockingIOError:pass
  if self.ue in ready:
   try:b=self.ue.recv(1048576)
   except BlockingIOError:b=None
   if b==b'':raise RuntimeError('Native LOS client closed')
   if b:self.ubuf+=b
   while b'\n' in self.ubuf:
    line,self.ubuf=self.ubuf.split(b'\n',1);v=json.loads(line)
    if v.get('action')=='los_reply':
     if str(v.get('query_id','')).startswith('probe:'):self.probe_result=v.get('visible');self.probes.append(dict(v,report_position=self.read_report().get('position_m')));self.probe=None
     else:self.answers.append(dict(v,question=self.questions.get(v.get('query_id')),report_position=self.read_report().get('position_m')));self.backend.sendall(line+b'\n')
    elif v.get('action')=='ping':self.backend.sendall(line+b'\n')
  if self.backend not in ready:raise socket.timeout()
  b=self.backend.recv(size);self.bbuf+=b
  while b'\n' in self.bbuf:
   line,self.bbuf=self.bbuf.split(b'\n',1);v=json.loads(line)
   if v.get('type')=='snapshot':
    for q in v.get('los_queries',[]):self.questions[q['id']]=q
    if self.probe:v.setdefault('los_queries',[]).append(self.probe)
    self.latest=(json.dumps(self.native_snapshot(v))+'\n').encode()
   else:
    # The QA client sends the original commands; the native observer needs only current snapshots.
    pass
  return b
 def start_probe(self,target):
  self.probe_serial+=1;self.probe_result=None;self.probe={'id':'probe:'+str(self.probe_serial),'token':'native-geometry-probe-'+str(self.probe_serial),'source_id':'player:local','target_id':target}
 def read_report(self):
  try:
   b=self.report.read_bytes();return json.loads(b.decode('utf-16' if b[:2] in [b'\xff\xfe',b'\xfe\xff'] else 'utf-8-sig'))
  except (OSError,ValueError):return {}
 def close(self):
  self.backend.close()
  if self.ue:self.ue.close()
  self.listener.close()
 def finish(self):
  self.process.wait(timeout=110);self.log.close();return self.process.returncode
