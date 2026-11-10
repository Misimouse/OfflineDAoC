"""Verify original consumable use, refusals, charges and persistence using only a marked disposable DOL database."""
from qa_runtime import *
import sqlite3,subprocess,socket,time,hashlib,shutil,traceback

case=os.environ.get('DAOC_CONSUMABLE_CASE','charges');assert case in ['charges','last_charge']
qa_lab=os.environ.get('DAOC_CONSUMABLE_QA_LAB','ConsumableUseLab');assert qa_lab in ['ConsumableUseLab','ItemShortcutsLab']
D=ROOT/qa_lab/('RealConsumableProtocol' if qa_lab=='ItemShortcutsLab' else 'RealProtocol')/time.strftime('%Y%m%d-%H%M%S');D.mkdir(parents=True)
SOURCE=Path(os.environ.get('DAOC_BRIDGE_QA_SOURCE',str(ROOT/'Godot')))
assert (SOURCE/'inventory_state.gd').exists()
result={'passed':False,'real_protocol':True,'disposable_only':True,'checks':{},'errors':[],'case':case,'source_inputs':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCE.glob('*.gd')}}
server=client=sock=None;logs=[];session='';snapshot={};buffer=b'';serial=0;backed=False
normal_targets=[Path(r['target']) for r in json.loads((ROOT/'ExpansionRaceLab/CentralDelivery/MinotaurActivation/installed.json').read_text())['files'] if Path(r['target']).name in ['GameServer.dll','CoreBase.dll','CoreDatabase.dll','live_gateway.gd']] + [ROOT/'Godot/visual_bridge.gd',ROOT/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll']
normal_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in normal_targets}
candidate_files=[]
backup=ROOT/'Backups'/('ConsumableUseProtocolQA_'+time.strftime('%Y%m%d-%H%M%S'));backup.mkdir()
config=RUN/'bridge_config.json';config_bytes=config.read_bytes()
def checked():
 db=sqlite3.connect(DB);db.row_factory=sqlite3.Row;assert db.execute('SELECT RunId FROM CodexQaIsolationMarker').fetchone()[0]==RUN.name;return db
def update(db,table,keyfield,key,values):db.execute('UPDATE '+table+' SET '+','.join('"'+k+'"=?' for k in values)+' WHERE "'+keyfield+'"=?',list(values.values())+[key])
def send(action,**values):
 global serial
 serial+=1;sock.sendall((json.dumps(dict(type='command',session=session,id='consumable:'+str(serial),action=action,**values))+'\n').encode())
def pump():
 global session,snapshot,buffer
 try:data=sock.recv(1048576)
 except socket.timeout:return
 if not data:raise RuntimeError('Private item handover bridge closed')
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
 raise RuntimeError(label+'; vault='+repr(inv().get('vault',{})))
def settle(seconds=.8):
 end=time.monotonic()+seconds
 while time.monotonic()<end:pump()
def guild():return snapshot.get('guild',{})
def picker():return snapshot.get('emblem_picker',{})
def money():
 v=inv().get('money',{})
 return sum(int(v.get(k,0))*n for k,n in [('copper',1),('silver',100),('gold',10000),('platinum',10000000),('mithril',10000000000)])
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
  update(db,'DOLCharacters','DOLCharacters_ID',char['DOLCharacters_ID'],{'Level':20,'Health':60,'HCFlag':0})
  def insert(table,row):db.execute('INSERT INTO '+table+' ('+','.join('"'+k+'"' for k in row)+') VALUES ('+','.join('?' for k in row)+')',list(row.values()))
  original=dict(db.execute('SELECT * FROM Inventory WHERE OwnerID=? LIMIT 1',(char['DOLCharacters_ID'],)).fetchone())
  db.execute('DELETE FROM Inventory WHERE OwnerID=? AND SlotPosition BETWEEN 40 AND 79',(char['DOLCharacters_ID'],))
  for slot,template_id,charges in [(40,'Elixir_of_Healing',1 if case=='last_charge' else 2),(41,'Elixir_of_Instant_Healing',3),(42,'Elixir_of_Healing',0)]:
   template=db.execute('SELECT * FROM ItemTemplate WHERE Id_nb=?',(template_id,)).fetchone();assert template
   row=dict(original);row.update(Inventory_ID='codex-private-consumable-'+str(slot),OwnerID=char['DOLCharacters_ID'],SlotPosition=slot,ITemplate_Id=template_id,UTemplate_Id='',Count=1,Charges=charges,Emblem=0,Color=0,IsCrafted=0,IsROG=0,Condition=template['MaxCondition'],Durability=template['MaxCondition'])
   insert('Inventory',row)
 cfg=json.loads(config_bytes);cfg['initial_spawn_m']=[(char['Xpos']-35*8192)*.025,char['Zpos']*.025,(char['Ypos']-51*8192)*.025];config.write_text(json.dumps(cfg),encoding='utf-8')
 for p in SOURCE.glob('*.gd'):shutil.copy2(p,RUN/'Godot'/p.name)
 p=RUN/'Godot/visual_bridge.gd';p.write_text(p.read_text(encoding='utf-8-sig').replace('port: int = 19727','port: int = 19737'),encoding='utf-8')
 candidate_root=ROOT/'GuildWindowLab/ServerCandidate';candidate=json.loads((candidate_root/'build_receipt.json').read_text());assert candidate['passed'] and 'guild_roster_cache' in candidate['candidate_features']
 for folder in [SERVER,SERVER/'lib',SERVER/'win-x64']:
  for name,expected in candidate['binaries_sha256'].items():
   target=folder/name
   if not target.exists():continue
   assert target.resolve().is_relative_to(RUN)
   origin=Path(candidate['libraries'])/name;assert hashlib.sha256(origin.read_bytes()).hexdigest()==expected
   saved=backup/('server_'+str(len(candidate_files))+'_'+name);shutil.copy2(target,saved);candidate_files.append((target,saved));shutil.copy2(origin,target)
 result['candidate_server_build_sha256']=hashlib.sha256((candidate_root/'build_receipt.json').read_bytes()).hexdigest()
 log=(D/'server.log').open('w',encoding='utf-8');logs.append(log)
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
 log=(D/'client.log').open('w',encoding='utf-8');logs.append(log)
 client=subprocess.Popen([str(game/'tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'),'--headless','--path',str(RUN/'LobbyProject'),'--script',str(RUN/'Godot/gateway_main.gd'),'--','--server=127.0.0.1','--server-port=10351','--account='+account,'--password='+password,'--no-world','--bridge-character=Codexdruid'],cwd=RUN,env=ce,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 end=time.monotonic()+50
 while time.monotonic()<end:
  try:sock=socket.create_connection(('127.0.0.1',19737),timeout=.3);sock.settimeout(.1);break
  except OSError:time.sleep(.2)
 else:raise RuntimeError('Private item handover bridge unavailable')
 wait(lambda:snapshot.get('classic_ui',{}).get('skills_ready') and inv().get('ready') and item(40) is not None and item(42) is not None and snapshot.get('player_status',{}).get('ready'),'Original consumable character ready')
 def ui():return snapshot.get('classic_ui',{})
 def vitals():return snapshot.get('player_status',{}).get('vitals',{})
 def messages():return snapshot.get('chat',{}).get('entries',[])
 def after(mark,text):return any(int(r.get('id',0))>mark and text.lower() in r.get('text','').lower() for r in messages())
 def mark():return max((int(r.get('id',0)) for r in messages()),default=0)
 def entry(slot):return next(e for e in ui().get('entries',[]) if e['id']=='srv:'+str(slot))
 def use(slot):
  e=entry(slot);send('ui_use',entry_id=e['id'],entry_token=e['token'])
 def posture(on):
  send('player_sit',on=on,player_generation=snapshot['player_status']['generation']);wait(lambda:bool(vitals().get('sitting'))==on,'Original posture confirmation')
 wait(lambda:any(e['id']=='srv:40' for e in ui().get('entries',[])),'Carried original potion entry')
 before=money();initial=dict(item(40));posture(True);message=mark();use(40)
 wait(lambda:after(message,"can't use an item while sitting"),'Original sitting refusal')
 result['checks']['sitting_refuses_use']=item(40)==initial
 posture(False);message=mark();use(41)
 wait(lambda:after(message,'not powerful enough'),'Original higher-level potion refusal')
 result['checks']['level_requirement_preserved']=item(41) is not None
 message=mark();use(42);wait(lambda:after(message,'out of charges'),'Original empty potion refusal')
 result['checks']['empty_charge_refusal']=item(42) is not None
 e=entry(40);send('ui_hover',entry_id=e['id'],entry_token=e['token'])
 wait(lambda:ui().get('hover',{}).get('status')=='ready' and ui()['hover'].get('entry_id')==e['id'],'Original potion detail')
 result['initial_hover_lines']=ui()['hover']['lines']
 send('ui_assign',bar=2,bank=ui()['banks'][2],slot=9,entry_id=e['id'],entry_token=e['token'])
 wait(lambda:ui()['bars'][2][ui()['banks'][2]][9].get('id')==e['id'],'Potion assigned to existing quickbar')
 hp=vitals()['health'];message=mark();send('ui_use_slot',bar=2,slot=9)
 wait(lambda:after(message,'has been used'),'Original potion used through quickbar')
 wait(lambda:vitals()['health']>hp,'Original potion heals character')
 result['checks']['quickbar_uses_original_potion']=True
 result['checks']['original_heal_increases_health']=vitals()['health']>hp
 if case=='charges':
  message=mark();send('ui_use_slot',bar=2,slot=9)
  wait(lambda:after(message,'must wait'),'Original potion shared cooldown')
  result['checks']['shared_reuse_refuses_duplicate']=item(40) is not None
  e=entry(40);send('ui_detail',entry_id=e['id'],entry_token=e['token'])
  wait(lambda:ui().get('detail',{}).get('status')=='ready','Fresh authoritative charge count')
  result['fresh_detail_lines']=ui()['detail']['lines'];result['hover_after_use']=ui().get('hover',{})
  wait(lambda:ui().get('hover',{}).get('status')=='ready' and '- 1 Charges' in ui()['hover'].get('lines',[]),'Hover refreshes to authoritative remaining charge')
  result['checks']['hover_charge_count_is_current']='- 1 Charges' in ui()['hover']['lines'] and '- 2 Charges' not in ui()['hover']['lines']
  result['checks']['inspection_charge_count_is_current']='- 1 Charges' in ui()['detail']['lines']
 else:
  wait(lambda:item(40) is None,'Last potion charge removes consumed item')
  wait(lambda:not ui().get('hover'),'Consumed item description closes')
  result['checks']['last_charge_removes_item']=True
  result['checks']['last_charge_removes_hover']=True
  stale=e;send('ui_use',entry_id=stale['id'],entry_token=stale['token']);settle(.3)
  result['checks']['consumed_entry_cannot_reuse']=item(40) is None and 'changed' in ui().get('feedback','').lower()
 result['checks']['consumables_do_not_charge_money']=money()==before
 (D/'snapshot.json').write_text(json.dumps(snapshot),encoding='utf-8')
 result['passed']=all(result['checks'].values())
except Exception:
 result['errors'].append(traceback.format_exc());(D/'failed_snapshot.json').write_text(json.dumps(snapshot),encoding='utf-8')
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
 if client and server and client.returncode==0 and server.returncode==0 and backed:
  with checked() as db:
   saved=[dict(r) for r in db.execute("SELECT Inventory_ID,SlotPosition,ITemplate_Id,Charges,Count FROM Inventory WHERE Inventory_ID LIKE 'codex-private-consumable-%'")]
  (D/'saved_items.json').write_text(json.dumps(saved,indent=2),encoding='utf-8')
  result['checks']['saved_original_charge_consumption']=any(r['SlotPosition']==40 and r['Charges']==1 and r['Count']==1 for r in saved) if case=='charges' else not any(r['SlotPosition']==40 for r in saved)
  result['checks']['saved_refused_items_unchanged']=all(any(r['SlotPosition']==slot and r['Charges']==charges and r['Count']==1 for r in saved) for slot,charges in [(41,3),(42,0)])
 for log in logs:log.close()
 for target,saved in reversed(candidate_files):
  assert target.resolve().is_relative_to(RUN);shutil.copy2(saved,target)
 if candidate_files:result["candidate_server_restored"]=True
 if backed:
  assert DB.is_relative_to(RUN) and RUN.is_relative_to(ROOT/'ProtocolQA')
  with checked() as dst:
   src=sqlite3.connect(backup/'before.sqlite3.db');src.backup(dst);src.close()
  config.write_bytes(config_bytes);result['database_restored']=True
 result['normal_runtime_unchanged']=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in normal_hashes.items())
 result['normal_shutdown']=bool(client and server and client.returncode==0 and server.returncode==0)
 result['passed']=result['passed'] and all(result['checks'].values()) and result['normal_shutdown'] and result['normal_runtime_unchanged'] and not result['errors'] and all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in result['source_inputs'].items())
 (D/'real_protocol.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='source_inputs'}));assert result['passed']
