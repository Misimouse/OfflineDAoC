"""Test-only relay: real UE geometry answers server LOS; all other native commands are ignored."""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json,socket,select,subprocess,time
from pathlib import Path
class NativeSightRelay:
 def __init__(self,backend,root,session,snapshot,*,project=None,world=None,report_dir=None,offscreen=False,enabled_plugins=(),navigation_probe=False,headless_geometry=False):
  self.backend=backend;self.root=root;self.session=session;self.ue=None;self.bbuf=b'';self.ubuf=b'';self.answers=[];self.questions={};self.probes=[];self.probe=None;self.probe_result=None;self.probe_serial=0;self.report=(report_dir or root/'Reports/magic_roundtrip')/'live_native_current.json';self.report.parent.mkdir(parents=True,exist_ok=True)
  self.listener=socket.socket();self.listener.bind(('127.0.0.1',0));self.listener.listen(1);self.listener.settimeout(100);port=self.listener.getsockname()[1]
  self.log=(self.report.parent/'live_native.log').open('w',encoding='utf-8');I=Path(str(INSTALL / 'new-client/godot'))
  cmd=[str(ENGINE / 'Binaries/Win64/UnrealEditor-Cmd.exe'),str(project or root/'GMCombatTest/NativeHost/BridgeGmHost.uproject'),world or '/Game/DAoC/Connacht_v01/Ardee_Nwiro_Prueba','-game','-DaocBridge','-DaocBridgeReadOnly','-DaocBridgeSpellVisualTest','-DaocBridgePort='+str(port),'-DaocBridgeCatalog='+str(root/'models.json'),'-DaocBridgeEquipmentCatalog='+str(root/'equipment_catalog_v01.json'),'-DaocBridgeCollisionCatalog='+str(root/'collision_catalog.json'),'-DaocBridgeHeights='+str(I/'content/zones/zone207/heights.f32'),'-DaocBridgeReport='+str(self.report),'-DaocBridgeCapture='+str(self.report.parent/'Live_Spell.png'),'-DaocBridgeQuality=accessible','-DaocBridgeProfile','-DaocBridgeProfileFixed','-DaocBridgeProfileSeconds=120','-windowed','-ResX=1280','-ResY=720','-d3d11','-nosplash','-nosound','-unattended']
  if offscreen:cmd.append('-RenderOffscreen')
  if enabled_plugins:cmd.append('-EnablePlugins='+','.join(enabled_plugins))
  for file,flag in [('environment_catalog.json','-DaocBridgeEnvironmentCatalog='),('foliage_lods.json','-DaocBridgeFoliageCatalog=')]:
   if (root/file).is_file():cmd.append(flag+str(root/file))
  if navigation_probe:cmd.append('-DaocBridgeNavigationProbe')
  if headless_geometry:
   cmd.remove('-d3d11');cmd.remove('-DaocBridgeSpellVisualTest');cmd.append('-nullrhi')
  cmd.append('-abslog='+str(self.report.parent/'Unreal.log'))
  self.process=subprocess.Popen(cmd,cwd=Path(project).parent if project else root,stdout=self.log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  try:
   deadline=time.monotonic()+300;self.listener.settimeout(.5)
   while True:
    if self.process.poll() is not None:raise RuntimeError('Native sight viewer exited before connecting')
    if time.monotonic()>=deadline:raise TimeoutError('Native sight viewer did not connect within 300 seconds')
    try:self.ue,_=self.listener.accept();break
    except socket.timeout:continue
   self.ue.settimeout(10);self.ue.sendall((json.dumps(dict(type='hello',protocol='daoc-visual-bridge',version=1,session=session))+'\n'+json.dumps(snapshot)+'\n').encode());self.ue.settimeout(.001)
  except BaseException:
   self.listener.close()
   if self.ue:self.ue.close()
   if self.process.poll() is None:
    self.process.terminate()
    try:self.process.wait(timeout=20)
    except subprocess.TimeoutExpired:self.process.kill();self.process.wait()
   self.log.close();raise
 def sendall(self,data):self.backend.sendall(data)
 def settimeout(self,value):self.backend.settimeout(value)
 def recv(self,size):
  ready,_,_=select.select([self.backend,self.ue],[],[],.08)
  if self.ue in ready:
   b=self.ue.recv(1048576)
   if not b:raise RuntimeError('Native LOS client closed')
   self.ubuf+=b
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
   self.ue.settimeout(10);self.ue.sendall((json.dumps(v)+'\n').encode());self.ue.settimeout(.001)
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
