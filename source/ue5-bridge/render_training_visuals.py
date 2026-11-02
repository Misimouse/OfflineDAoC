"""Render all six original sheets with a captured real server snapshot; no live commands."""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import socket,json,subprocess,time,copy
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/training_staff_fx_pets/visual';D.mkdir(exist_ok=True);snapshot=json.loads((R/'Reports/chat_channels/real_snapshot_0.json').read_text(encoding='utf-8'));snapshot['entities']=[r for r in snapshot['entities']if r.get('id')=='player:local'];snapshot['session']='classic-ui-render';snapshot['status']='Recorded session: widescreen UI verification';listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1);listener.settimeout(110);port=listener.getsockname()[1]
I=Path(str(INSTALL / 'new-client/godot'));cmd=[str(ENGINE / 'Binaries/Win64/UnrealEditor-Cmd.exe'),str(R/'GMCombatTest/NativeHost/BridgeGmHost.uproject'),'/Game/DAoC/Connacht_v01/Ardee_Nwiro_Prueba','-game','-DaocBridge','-DaocBridgeReadOnly','-DaocBridgePort='+str(port),'-DaocBridgeCatalog='+str(R/'models.json'),'-DaocBridgeEquipmentCatalog='+str(R/'equipment_catalog_v01.json'),'-DaocBridgeCollisionCatalog='+str(R/'collision_catalog.json'),'-DaocBridgeHeights='+str(I/'content/zones/zone207/heights.f32'),'-DaocBridgeReport='+str(D/'visual_current.json'),'-DaocBridgeCapture='+str(D/'Staff_FX_OriginalUI.png'),'-DaocBridgeQuality=accessible','-DaocBridgeProfile','-DaocBridgeProfileFixed','-DaocBridgeProfileSeconds=32','-windowed','-ResX=2560','-ResY=1080','-d3d11','-nosplash','-nosound','-unattended']
local=snapshot['entities'][0]
snapshot['inventory']['items'].append(dict(slot=12,model=19,hand=1,weapon_stance='staff'))
snapshot['inventory']['weapon_set']='twohand';snapshot['inventory']['state_revision']+=1
snapshot['player_status']['weapon_stance']='staff'
npc=copy.deepcopy(local);npc.update(id='npc:visual-equipped',kind='npc',name='Recorded equipment sample',model_id=97,position_m=[local['position_m'][0]+3,local['position_m'][1],local['position_m'][2]],equipment=dict(revision=1,weapon_slots=0x10,items=[dict(slot=10,model=445),dict(slot=11,model=59)]))
snapshot['entities'].append(npc)
start=time.time();peer=None;seq=0
with(D/'visual_render.log').open('w',encoding='utf-8')as log:
 p=subprocess.Popen(cmd,cwd=R,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 try:
  peer,_=listener.accept();peer.settimeout(.001);peer.sendall((json.dumps(dict(type='hello',protocol='daoc-visual-bridge',version=1,session='classic-ui-render'))+'\n').encode())
  while p.poll()is None and time.time()-start<190:
   seq+=1;snapshot['seq']=seq
   # Visual fixture uses original effect IDs; no game rules or live account.
   snapshot['spell_visuals']=[dict(seq=seq*2,kind='cast',caster='player:local',effect_id=4101,duration_ms=3000,age_ms=300),dict(seq=seq*2+1,kind='release',caster='npc:visual-equipped',target='npc:visual-equipped',effect_id=4301,age_ms=300)] if seq%6==1 else []
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
shots={tab:(D/'Staff_FX_OriginalUI.png').exists()and(D/'Staff_FX_OriginalUI.png').stat().st_mtime>=start for tab in ['character']};report={'passed':p.returncode==0 and all(shots.values()),'recorded_chat':True,'live_account':False,'native_exit':p.returncode,'captures':shots};(D/'visual_render.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report));assert report['passed']
