import sys as _bridge_sys
from pathlib import Path as _BridgePath
_bridge_sys.path.insert(0,str(_BridgePath(__file__).resolve().parents[1]))
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
from qa_runtime import *
import sqlite3,subprocess,socket,time,hashlib,shutil,traceback

class Peer:
    def __init__(self):
        self.sock=socket.create_connection(('127.0.0.1',19737),timeout=2);self.sock.settimeout(.1);self.buffer=b'';self.snapshot={};self.session=''
    def pump(self):
        try:data=self.sock.recv(1048576)
        except socket.timeout:return
        if not data:raise RuntimeError('QA bridge closed')
        self.buffer+=data
        while b'\n' in self.buffer:
            line,self.buffer=self.buffer.split(b'\n',1);v=json.loads(line)
            if v.get('type')=='hello':self.session=v['session']
            if v.get('type')=='snapshot':self.snapshot=v
    def logout(self):self.sock.sendall((json.dumps(dict(type='command',session=self.session,id='qa-appearance-logout',action='logout'))+'\n').encode())

D=ROOT/'Reports/training_staff_fx_pets';result={'passed':False,'real_protocol':True,'disposable_only':True,'errors':[]}
server=client=peer=None;handles=[];saved={};template='codex-qa-appearance-only'
def checked():
    db=sqlite3.connect(DB);assert db.execute('SELECT RunId FROM CodexQaIsolationMarker').fetchone()[0]==RUN.name;return db
def update(db,table,keyfield,key,values):
    db.execute('UPDATE '+table+' SET '+','.join('"'+k+'"=?' for k in values)+' WHERE "'+keyfield+'"=?',list(values.values())+[key])
try:
    with checked() as db:
        db.row_factory=sqlite3.Row
        char=db.execute("SELECT DOLCharacters_ID,AccountName,ActiveWeaponSlot FROM DOLCharacters WHERE Name='Codexdruid'").fetchone();assert char
        saved['char']=(char['DOLCharacters_ID'],char['ActiveWeaponSlot']);saved['account']=(char['AccountName'],tuple(db.execute('SELECT PrivLevel,Realm FROM Account WHERE Name=?',(char['AccountName'],)).fetchone()))
        update(db,'Account','Name',char['AccountName'],{'PrivLevel':1,'Realm':3})
        update(db,'DOLCharacters','DOLCharacters_ID',char['DOLCharacters_ID'],{'ActiveWeaponSlot':0})
        saved['items']=[]
        for slot,model,color,emblem,effect in [(10,445,2,0,30),(11,59,1,0,0)]:
            item=db.execute('SELECT Inventory_ID,UTemplate_Id,Color,Emblem FROM Inventory WHERE OwnerID=? AND SlotPosition=?',(char['DOLCharacters_ID'],slot)).fetchone();assert item and item['UTemplate_Id']
            unique=db.execute('SELECT Id_nb,Model,Effect,Emblem FROM ItemUnique WHERE Id_nb=?',(item['UTemplate_Id'],)).fetchone();assert unique
            saved['items'].append((dict(item),dict(unique)))
            update(db,'ItemUnique','Id_nb',item['UTemplate_Id'],{'Model':model,'Effect':effect,'Emblem':emblem})
            update(db,'Inventory','Inventory_ID',item['Inventory_ID'],{'Color':color,'Emblem':emblem})
        fields=['Name','Model','EquipmentTemplateID','VisibleWeaponSlots','Brain','ClassType','Realm','AggroLevel','Speed']
        mob=db.execute('SELECT Mob_ID,'+','.join(fields)+" FROM Mob WHERE Name='Codex Pet Training Dummy'").fetchone();assert mob
        saved['mob']=dict(mob)
        update(db,'Mob','Mob_ID',mob['Mob_ID'],{'Name':'Codex Appearance NPC','Model':1984,'EquipmentTemplateID':template,'VisibleWeaponSlots':16,'Brain':'','ClassType':'DOL.GS.GameNPC','Realm':3,'AggroLevel':0,'Speed':0})
        db.execute('DELETE FROM NPCEquipment WHERE TemplateID=?',(template,))
        for slot,model,color,emblem,effect in [(10,445,2,0,30),(11,59,1,529,0)]:
            db.execute('INSERT INTO NPCEquipment (TemplateID,Slot,Model,Color,Effect,Extension,Emblem,NPCEquipment_ID) VALUES (?,?,?,?,?,0,?,?)',(template,slot,model,color,effect,emblem,template+'-'+str(slot)))
    # Use current production bridge scripts; only the isolated listener port changes.
    for p in (ROOT/'Godot').glob('*.gd'):shutil.copy2(p,RUN/'Godot'/p.name)
    p=RUN/'Godot/visual_bridge.gd';p.write_text(p.read_text().replace('port: int = 19727','port: int = 19737'),encoding='utf-8')
    log=(D/'appearance_real_server.log').open('w',encoding='utf-8');handles.append(log)
    server=subprocess.Popen([str(dotnet),str(SERVER/'CoreServer.dll'),'--start'],cwd=SERVER,env=env,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
    deadline=time.monotonic()+30
    while time.monotonic()<deadline:
        try:
            with socket.create_connection(('127.0.0.1',10351),timeout=.2):break
        except OSError:time.sleep(.2)
    else:raise RuntimeError('Isolated server unavailable')
    time.sleep(2)
    game=Path(str(INSTALL / 'new-client'));sdk=Path(str(ENGINE / 'Binaries/ThirdParty/DotNet/10.0/win-x64'))
    account='codexqa'+hashlib.sha256(RUN.name.encode()).hexdigest()[:10];password=hashlib.sha256(('disposable-local-protocol-qa:'+RUN.name).encode()).hexdigest()[:24]
    client_env=dict(env,DOTNET_ROOT=str(sdk),DOTNET_ROOT_X64=str(sdk),PATH=str(sdk)+os.pathsep+env['PATH'],APPDATA=str(RUN/'appdata'))
    (RUN/'Reports/live/logout.request').unlink(missing_ok=True)
    log=(D/'appearance_real_client.log').open('w',encoding='utf-8');handles.append(log)
    client=subprocess.Popen([str(game/'tools/godot_net/Godot_v4.7.2-stable_mono_win64.exe'),'--headless','--path',str(game/'godot'),'--script',str(RUN/'Godot/gateway_main.gd'),'--','--server=127.0.0.1','--server-port=10351','--account='+account,'--password='+password,'--no-world','--bridge-character=Codexdruid'],cwd=RUN,env=client_env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    deadline=time.monotonic()+60
    while time.monotonic()<deadline:
        if peer is None:
            try:peer=Peer()
            except OSError:time.sleep(.2);continue
        peer.pump();s=peer.snapshot
        local={i['slot']:i for i in s.get('inventory',{}).get('items',[])}
        npc=next((e for e in s.get('entities',[]) if e.get('name')=='Codex Appearance NPC'),{})
        remote={i['slot']:i for i in npc.get('equipment',{}).get('items',[])}
        if all(slot in local and slot in remote for slot in [10,11]):break
    else:
        result['diagnostic']={'local_slots':list(local),'remote_slots':list(remote),'npc_found':bool(npc),'npc_model':npc.get('model_id'),'npc_equipment':npc.get('equipment'),'entities':len(s.get('entities',[])),'inventory_ready':s.get('inventory',{}).get('ready'),'weapon_set':s.get('inventory',{}).get('weapon_set')}
        (D/'appearance_failed_snapshot.json').write_text(json.dumps(s),encoding='utf-8')
        raise RuntimeError('Original server equipment did not reach the bridge')
    (D/'appearance_failed_snapshot.json').write_text(json.dumps(s),encoding='utf-8')
    for name,items in [('local',local),('npc',remote)]:
        for slot,expected in [(10,{'model':445,'color':2,'effect':30}),(11,{'model':59,'color':0 if name=='npc' else 1,'emblem':529 if name=='npc' else 0})]:
            for key,value in expected.items():assert items[slot].get(key,0)==value,(name,slot,key,items[slot].get(key,0),value)
    assert s['inventory']['weapon_set']=='standard',s['inventory']['weapon_set']
    (D/'appearance_real_snapshot.json').write_text(json.dumps(s),encoding='utf-8')
    result.update(passed=True,local_equipment={str(slot):{k:local[slot].get(k,0) for k in ['model','color','effect','emblem']} for slot in [10,11]},npc_equipment={str(slot):{k:remote[slot].get(k,0) for k in ['model','color','effect','emblem']} for slot in [10,11]},snapshot_saved=True)
except Exception:result['errors'].append(traceback.format_exc())
finally:
    if peer and peer.session:
        try:peer.logout()
        except OSError:pass
    if client and client.poll() is None:
        (RUN/'Reports/live/logout.request').write_text('logout',encoding='utf-8')
        try:client.wait(timeout=80)
        except subprocess.TimeoutExpired:client.kill();client.wait();result['errors'].append('Isolated Godot needed forced stop')
    if peer:peer.sock.close()
    if server and server.poll() is None:
        server.stdin.write('exit\n');server.stdin.flush()
        try:server.wait(timeout=40)
        except subprocess.TimeoutExpired:server.kill();server.wait();result['errors'].append('Isolated server needed forced stop')
    if not server or server.poll() is not None:
        with checked() as db:
            if 'char'in saved:update(db,'DOLCharacters','DOLCharacters_ID',saved['char'][0],{'ActiveWeaponSlot':saved['char'][1]})
            if 'account'in saved:update(db,'Account','Name',saved['account'][0],dict(zip(['PrivLevel','Realm'],saved['account'][1])))
            for item,unique in saved.get('items',[]):
                update(db,'ItemUnique','Id_nb',unique['Id_nb'],{k:unique[k] for k in ['Model','Effect','Emblem']})
                update(db,'Inventory','Inventory_ID',item['Inventory_ID'],{k:item[k] for k in ['Color','Emblem']})
            if 'mob'in saved:update(db,'Mob','Mob_ID',saved['mob']['Mob_ID'],{k:v for k,v in saved['mob'].items() if k!='Mob_ID'})
            db.execute('DELETE FROM NPCEquipment WHERE TemplateID=?',(template,))
        result['private_fixture_restored']=True
    for handle in handles:handle.close()
    result['normal_shutdown']=bool(client and server and client.returncode==0 and server.returncode==0)
    result['passed']=result['passed'] and result['normal_shutdown'] and not result['errors']
    (D/'appearance_real.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result),flush=True)
if not result['passed']:raise SystemExit(1)
