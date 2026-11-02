from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
from pathlib import Path
import json,socket,subprocess,time,select,sys
R=Path(__file__).resolve().parent;D=R/'Reports/training_staff_fx_pets'
render='--render' in sys.argv
snapshot=json.loads((D/'appearance_real_snapshot.json').read_text(encoding='utf-8'))
snapshot['entities']=[e for e in snapshot['entities'] if e['id']=='player:local' or e.get('name')=='Codex Appearance NPC']
assert len(snapshot['entities'])==2
report=D/('appearance_render_current.json' if render else 'appearance_native_current.json');report.unlink(missing_ok=True)
shot=D/'Appearance_Original_Entry.png';shot.unlink(missing_ok=True) if render else None
listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1);listener.settimeout(90)
cmd=[str(ENGINE / 'Binaries/Win64/UnrealEditor-Cmd.exe'),str(R/'Client/DAoCBridgeClient.uproject'),'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeReadOnly','-DaocBridgePort='+str(listener.getsockname()[1]),'-DaocBridgeCatalog='+str(R/'models.json'),'-DaocBridgeEquipmentCatalog='+str(R/'equipment_catalog_v01.json'),'-DaocBridgeReport='+str(report),'-DaocBridgeQuality=accessible','-DaocBridgeProfile','-DaocBridgeProfileFixed','-DaocBridgeProfileSeconds=30','-nosplash','-nosound','-unattended']
cmd+=['-windowed','-ResX=1280','-ResY=720','-d3d11','-DaocBridgeCapture='+str(shot),'-ExecCmds=viewmode unlit,t.MaxFPS 20'] if render else ['-nullrhi','-ExecCmds=t.MaxFPS 20']
with (D/('appearance_render.log' if render else 'appearance_native_replay.log')).open('w',encoding='utf-8') as log:
    p=subprocess.Popen(cmd,cwd=R,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    peer=None
    try:
        peer,_=listener.accept();peer.sendall((json.dumps(dict(type='hello',protocol='daoc-visual-bridge',version=1,session=snapshot['session']))+'\n').encode());peer.setblocking(False)
        pending=b'';latest=b'';deadline=time.monotonic()+100;sent=0;seq=snapshot.get('seq',1)
        while p.poll() is None and time.monotonic()<deadline:
            now=time.monotonic()
            if now-sent>.2:
                seq+=1;snapshot['seq']=seq;latest=(json.dumps(snapshot)+'\n').encode();sent=now
            if not pending and latest:pending=latest;latest=b''
            readable,writable,_=select.select([peer],[peer] if pending else [],[],.02)
            if peer in writable:
                try:pending=pending[peer.send(pending):]
                except BlockingIOError:pass
                except (BrokenPipeError,ConnectionResetError):break
            if peer in readable:
                try:
                    if not peer.recv(65536):break
                except BlockingIOError:pass
                except ConnectionResetError:break
        p.wait(timeout=30)
    finally:
        if peer:peer.close()
        listener.close()
        if p.poll() is None:p.terminate();p.wait(timeout=15)
assert p.returncode==0 and report.exists(),p.returncode
b=report.read_bytes();v=json.loads(b.decode('utf-16' if b[:2] in [b'\xff\xfe',b'\xfe\xff'] else 'utf-8-sig'))
equipment=v['equipment_visual'];fx=v['spell_visuals'];assert equipment['visible_count']==2 and equipment['remote_visible_count']==2,equipment
assert equipment['missing_models']==0 and equipment['remote_missing_models']==0,equipment
assert fx['weapon_effects']==2 and fx['active_particles']>0,fx
sword=next(b for b in equipment['bindings'] if b['slot']==10)
shield=next(b for b in equipment['bindings'] if b['slot']==11)
assert sword['dye']==2 and sword['dyed_materials']>0 and shield['dye']==1 and shield['dyed_materials']>0,equipment
result={'passed':True,'real_protocol_snapshot':True,'installed_client':True,'rendered':render,'local_weapons':2,'npc_weapons':2,'permanent_effects':2,'active_particles':fx['active_particles'],'live_account':False}
if render:assert shot.exists();result['capture']=str(shot)
(D/('appearance_render.json' if render else 'appearance_native_replay.json')).write_text(json.dumps(result,indent=2),encoding='utf-8');print(result)
