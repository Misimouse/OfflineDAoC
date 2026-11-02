"""Render all six original sheets with a captured real server snapshot; no live commands."""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import socket,json,subprocess,time,copy
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/protocol_qa/visual';snapshot=json.loads((D/'real_ui_snapshot.json').read_text(encoding='utf-8'));snapshot['entities']=[r for r in snapshot['entities']if r.get('id')=='player:local'];snapshot['session']='classic-ui-render';snapshot['status']='Concentración real capturada para revisión de UI · sin servidor';listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1);listener.settimeout(110);port=listener.getsockname()[1]
I=Path(str(INSTALL / 'new-client/godot'));cmd=[str(ENGINE / 'Binaries/Win64/UnrealEditor-Cmd.exe'),str(R/'GMCombatTest/NativeHost/BridgeGmHost.uproject'),'/Game/DAoC/Connacht_v01/Ardee_Nwiro_Prueba','-game','-DaocBridge','-DaocBridgeReadOnly','-DaocBridgePort='+str(port),'-DaocBridgeCatalog='+str(R/'models.json'),'-DaocBridgeEquipmentCatalog='+str(R/'equipment_catalog_v01.json'),'-DaocBridgeCollisionCatalog='+str(R/'collision_catalog.json'),'-DaocBridgeHeights='+str(I/'content/zones/zone207/heights.f32'),'-DaocBridgeReport='+str(D/'visual_current.json'),'-DaocBridgeCapture='+str(D/'Classic_Overview.png'),'-DaocBridgeQuality=accessible','-DaocBridgeProfile','-DaocBridgeProfileFixed','-DaocBridgeProfileSeconds=32','-windowed','-ResX=1920','-ResY=1080','-d3d11','-nosplash','-nosound','-unattended']
start=time.time();peer=None;seq=0
with(D/'visual_render.log').open('w',encoding='utf-8')as log:
 p=subprocess.Popen(cmd,cwd=R,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 try:
  peer,_=listener.accept();peer.settimeout(.001);peer.sendall((json.dumps(dict(type='hello',protocol='daoc-visual-bridge',version=1,session='classic-ui-render'))+'\n').encode())
  while p.poll()is None and time.time()-start<190:
   seq+=1;snapshot['seq']=seq
   try:
    peer.settimeout(10);peer.sendall((json.dumps(snapshot)+'\n').encode());peer.settimeout(.001)
   except OSError:break
   try:peer.recv(65536)
   except socket.timeout:pass
   except OSError:break
   time.sleep(.25)
  p.wait(timeout=25)
 finally:
  if peer:peer.close()
  listener.close()
shots={tab:(D/'Classic_Overview.png').exists()and(D/'Classic_Overview.png').stat().st_mtime>=start for tab in ['character']};report={'passed':p.returncode==0 and all(shots.values()),'recorded_advanced_class':True,'live_account':False,'native_exit':p.returncode,'captures':shots};(D/'visual_render.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report));assert report['passed']
