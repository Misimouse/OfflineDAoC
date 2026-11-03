from qa_runtime import *
import sqlite3,subprocess,socket,time,hashlib,shutil,traceback

D=ROOT/'Reports/armour_rules';D.mkdir(exist_ok=True)
SOURCE=Path(os.environ.get('DAOC_BRIDGE_QA_GODOT',str(ROOT/'Godot')))
result={'passed':False,'real_protocol':True,'disposable_only':True,'checks':{},'errors':[]}
server=client=sock=None;logs=[];session='';snapshot={};buffer=b'';serial=0;backed=False
backup=ROOT/'Backups'/('ArmourRulesProtocolQA_'+time.strftime('%Y%m%d-%H%M%S'));backup.mkdir()
config=RUN/'bridge_config.json';config_bytes=config.read_bytes()
def checked():
 db=sqlite3.connect(DB);db.row_factory=sqlite3.Row;assert db.execute('SELECT RunId FROM CodexQaIsolationMarker').fetchone()[0]==RUN.name;return db
def update(db,table,keyfield,key,values):db.execute('UPDATE '+table+' SET '+','.join('"'+k+'"=?' for k in values)+' WHERE "'+keyfield+'"=?',list(values.values())+[key])
def send(action,**values):
 global serial
 serial+=1;sock.sendall((json.dumps(dict(type='command',session=session,id='cloak:'+str(serial),action=action,**values))+'\n').encode())
def pump():
 global session,snapshot,buffer
 try:data=sock.recv(1048576)
 except socket.timeout:return
 if not data:raise RuntimeError('Private cloak bridge closed')
 buffer+=data
 while b'\n' in buffer:
  line,buffer=buffer.split(b'\n',1);v=json.loads(line)
  if v.get('type')=='hello':session=v['session']
  if v.get('type')=='snapshot':snapshot=v
def wait(test,label,seconds=30):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  pump()
  if test():return
 raise RuntimeError(label+'; inventory='+str(inv().get('feedback'))+'; flags='+str(gear()))
def settle(seconds=.8):
 end=time.monotonic()+seconds
 while time.monotonic()<end:pump()
def inv():return snapshot.get('inventory',{})
def gear():return inv().get('gear',{})
def item(slot):return next((i for i in inv().get('items',[]) if i['slot']==slot),None)
try:
 for port in [10351,19737]:
  try:
   with socket.create_connection(('127.0.0.1',port),timeout=.2):raise RuntimeError('Private QA port already occupied')
  except (ConnectionRefusedError,socket.timeout):pass
 with checked() as db:
  dest=sqlite3.connect(backup/'before.sqlite3.db');db.backup(dest);dest.close();backed=True
  char=db.execute("SELECT * FROM DOLCharacters WHERE Name='Codexdruid'").fetchone();assert char
  update(db,'Account','Name',char['AccountName'],{'PrivLevel':1,'Realm':3})
  update(db,'DOLCharacters','DOLCharacters_ID',char['DOLCharacters_ID'],{'IsCloakHoodUp':0,'IsCloakInvisible':0,'IsHelmInvisible':0})
  update(db,'DOLCharacters','DOLCharacters_ID',char['DOLCharacters_ID'],{'Class':51,'Level':50})
  original=dict(db.execute('SELECT * FROM Inventory WHERE OwnerID=? LIMIT 1',(char['DOLCharacters_ID'],)).fetchone())
  db.execute('DELETE FROM Inventory WHERE OwnerID=? AND SlotPosition IN (25,70,71,72)',(char['DOLCharacters_ID'],))
  for slot,template in [(70,'Gossamer_Voided_Robe'),(71,'daringleatherjerkin_hib'),(72,'free_plate_vest')]:
   assert db.execute('SELECT Item_Type FROM ItemTemplate WHERE Id_nb=?',(template,)).fetchone()[0]==25
   row=dict(original,Inventory_ID='codex-armour-rules-'+str(slot),ITemplate_Id=template,UTemplate_Id=None,SlotPosition=slot,Count=1,Color=0,Emblem=0,SellPrice=0,OwnerLot=0,RealmExchangeListedUtc=None)
   db.execute('INSERT INTO Inventory ('+','.join('"'+k+'"' for k in row)+') VALUES ('+','.join('?' for k in row)+')',list(row.values()))
  mob=db.execute("SELECT Mob_ID FROM Mob WHERE Name='Codex Pet Training Dummy'").fetchone();assert mob
  update(db,'Mob','Mob_ID',mob[0],{'Name':'Codex Helmet NPC','Model':1984,'EquipmentTemplateID':'codex-helmet-qa-only','ClassType':'DOL.GS.GameNPC','Brain':'','Realm':3,'Speed':0,'AggroLevel':0,'X':char['Xpos']+80,'Y':char['Ypos'],'Z':char['Zpos'],'Region':char['Region']})
  db.execute("DELETE FROM NPCEquipment WHERE TemplateID='codex-helmet-qa-only'")
  db.execute("INSERT INTO NPCEquipment(TemplateID,Slot,Model,Color,Effect,Extension,Emblem,NPCEquipment_ID) VALUES ('codex-helmet-qa-only',21,438,2,0,0,0,'codex-helmet-qa-only-26')")
 cfg=json.loads(config_bytes);cfg['initial_spawn_m']=[(char['Xpos']-35*8192)*.025,char['Zpos']*.025,(char['Ypos']-51*8192)*.025];config.write_text(json.dumps(cfg),encoding='utf-8')
 for p in SOURCE.glob('*.gd'):shutil.copy2(p,RUN/'Godot'/p.name)
 p=RUN/'Godot/visual_bridge.gd';p.write_text(p.read_text(encoding='utf-8-sig').replace('port: int = 19727','port: int = 19737'),encoding='utf-8')
 log=(D/'real_armour_rules_server.log').open('w',encoding='utf-8');logs.append(log)
 server=subprocess.Popen([str(dotnet),str(SERVER/'CoreServer.dll'),'--start'],cwd=SERVER,env=env,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
 end=time.monotonic()+40
 while time.monotonic()<end:
  try:
   with socket.create_connection(('127.0.0.1',10351),timeout=.2):break
  except OSError:time.sleep(.2)
 else:raise RuntimeError('Private QA server unavailable')
 game=INSTALL/'new-client';sdk=ENGINE/'Binaries/ThirdParty/DotNet/10.0/win-x64'
 account='codexqa'+hashlib.sha256(RUN.name.encode()).hexdigest()[:10];password=hashlib.sha256(('disposable-local-protocol-qa:'+RUN.name).encode()).hexdigest()[:24]
 ce=dict(env,DOTNET_ROOT=str(sdk),DOTNET_ROOT_X64=str(sdk),PATH=str(sdk)+os.pathsep+env['PATH'])
 (RUN/'Reports/live/logout.request').unlink(missing_ok=True)
 log=(D/'real_armour_rules_client.log').open('w',encoding='utf-8');logs.append(log)
 client=subprocess.Popen([str(game/'tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'),'--headless','--path',str(RUN/'LobbyProject'),'--script',str(RUN/'Godot/gateway_main.gd'),'--','--server=127.0.0.1','--server-port=10351','--account='+account,'--password='+password,'--no-world','--bridge-character=Codexdruid'],cwd=RUN,env=ce,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 end=time.monotonic()+50
 while time.monotonic()<end:
  try:sock=socket.create_connection(('127.0.0.1',19737),timeout=.3);sock.settimeout(.1);break
  except OSError:time.sleep(.2)
 else:raise RuntimeError('Private cloak bridge unavailable')
 wait(lambda:inv().get('ready') and all(item(slot) for slot in [70,71,72]),'Normal magician inventory')
 settle(2);assert item(25) is None;result['checks']['ordinary_magician_fixture']=True
 cloth=item(70);assert cloth['object_type']==32
 send('inventory_equip',slot=70,item_token=cloth['token'],inventory_revision=inv()['state_revision'])
 wait(lambda:item(25) and item(25)['model']==cloth['model'] and not inv()['pending'],'Magician equips cloth')
 result['checks']['cloth_equipped']=True;settle()
 for slot,label,object_type in [(71,'leather',33),(72,'plate',36)]:
  armour=item(slot);assert armour and armour['object_type']==object_type
  previous_denials=json.dumps(snapshot).count('You have no skill in wearing this armor type!')
  send('inventory_equip',slot=slot,item_token=armour['token'],inventory_revision=inv()['state_revision'])
  wait(lambda:json.dumps(snapshot).count('You have no skill in wearing this armor type!')>previous_denials,'Original class restriction reply')
  result['checks'][label+'_original_server_refusal']=True
  if os.environ.get('DAOC_BRIDGE_QA_DENIAL_ACK')=='1':
   wait(lambda:not inv()['pending'] and inv()['feedback']=='You have no skill in wearing this armor type!','Class refusal immediately finishes the equipment request',3)
   result['checks'][label+'_immediate_original_feedback']=True
  assert item(slot) and item(slot)['model']==armour['model'] and item(25)['model']==cloth['model'],label+' was equipped by a normal magician'
  result['checks'][label+'_rejected']=True
  wait(lambda:not inv()['pending'],'Rejected armour leaves inventory usable',20);settle()
  assert item(slot)['model']==armour['model'] and item(25)['model']==cloth['model'];result['checks'][label+'_did_not_replace_cloth']=True
 (D/'normal_magician_snapshot.json').write_text(json.dumps(snapshot),encoding='utf-8')
 result['passed']=all(result['checks'].values())
except Exception:
 result['errors'].append(traceback.format_exc());(D/'real_armour_rules_failed.json').write_text(json.dumps(snapshot),encoding='utf-8')
finally:
 if sock and session:
  try:send('logout')
  except OSError:pass
 if client and client.poll() is None:
  (RUN/'Reports/live/logout.request').write_text('logout',encoding='utf-8')
  try:client.wait(timeout=90)
  except subprocess.TimeoutExpired:client.kill();client.wait();result['errors'].append('Private client forced stop')
 if sock:sock.close()
 if server and server.poll() is None:
  server.stdin.write('exit\n');server.stdin.flush()
  try:server.wait(timeout=45)
  except subprocess.TimeoutExpired:server.kill();server.wait();result['errors'].append('Private server forced stop')
 for log in logs:log.close()
 if backed:
  assert DB.is_relative_to(RUN) and RUN.is_relative_to(ROOT/'ProtocolQA')
  with checked() as dst:
   src=sqlite3.connect(backup/'before.sqlite3.db');src.backup(dst);src.close()
  config.write_bytes(config_bytes);result['database_restored']=True
 result['normal_shutdown']=bool(client and server and client.returncode==0 and server.returncode==0)
 result['passed']=result['passed'] and result['normal_shutdown'] and not result['errors']
 (D/'real_protocol.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result));assert result['passed']
