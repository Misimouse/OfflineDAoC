"""Verify original positive absolute health at zero rounded percentage using only a marked disposable DOL database."""
from qa_runtime import *
import sqlite3,subprocess,socket,time,hashlib,shutil,traceback

case=os.environ.get('DAOC_VITALS_CASE','before');assert case in ['before','after']
D=ROOT/'PlayerVitalsLab'/('BeforeProtocol' if case=='before' else 'RealProtocol')/time.strftime('%Y%m%d-%H%M%S');D.mkdir(parents=True)
SOURCE=Path(os.environ.get('DAOC_BRIDGE_QA_SOURCE',str(ROOT/'Godot')))
assert (SOURCE/'inventory_state.gd').exists()
result={'passed':False,'real_protocol':True,'disposable_only':True,'checks':{},'errors':[],'case':case,'source_inputs':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCE.glob('*.gd')}}
server=client=sock=None;logs=[];session='';snapshot={};buffer=b'';serial=0;backed=False
normal_targets=[Path(r['target']) for r in json.loads((ROOT/'ExpansionRaceLab/CentralDelivery/MinotaurActivation/installed.json').read_text())['files'] if Path(r['target']).name in ['GameServer.dll','CoreBase.dll','CoreDatabase.dll','live_gateway.gd']] + [ROOT/'Godot/visual_bridge.gd',ROOT/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll']
normal_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in normal_targets}
candidate_files=[]
backup=ROOT/'Backups'/('PlayerVitalsProtocolQA_'+time.strftime('%Y%m%d-%H%M%S'));backup.mkdir()
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
  update(db,'DOLCharacters','DOLCharacters_ID',char['DOLCharacters_ID'],{'Level':20,'Health':1,'HCFlag':0})
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
 wait(lambda:snapshot.get('player_status',{}).get('ready') and snapshot['player_status'].get('vitals',{}).get('absolute_health_known') and snapshot['player_status']['vitals'].get('health',0)>0 and snapshot['player_status']['vitals'].get('health_pct')==0,'Original DOL positive HP and zero rounded percent')
 initial=json.loads(json.dumps(snapshot));v=initial['player_status']['vitals'];local=next(e for e in initial['entities'] if e['id']=='player:local')
 (D/'initial_snapshot.json').write_text(json.dumps(initial),encoding='utf-8')
 result['checks']['original_status_has_positive_absolute_hp']=v['health']>0 and v['max_health']>v['health']
 result['checks']['original_status_percentage_rounds_to_zero']=v['health_pct']==0 and v['health']*100//v['max_health']==0
 result['initial_vitals']=v;result['initial_local_state']={k:local.get(k) for k in ['id','health','state']};result['initial_max_speed_mps']=initial['max_speed_mps']
 if case=='before':
  result['checks']['existing_bridge_bug_reproduced']=local['state']=='dead' and initial['max_speed_mps']==0
  result['bug_reproduced']=result['checks']['existing_bridge_bug_reproduced']
 else:
  result['checks']['positive_absolute_hp_keeps_local_actor_alive']=local['state']!='dead' and local['health']>0
  result['checks']['positive_absolute_hp_keeps_real_move_speed']=initial['max_speed_mps']>0
  before_release=snapshot['player_status']['release'].get('requests',0);send('player_release',player_generation=snapshot['player_status']['generation']);settle(.3)
  result['checks']['living_zero_percent_player_cannot_release']=snapshot['player_status']['release'].get('requests',0)==before_release and 'only release after dying' in snapshot['player_status']['release'].get('feedback','').lower()
  send('player_sit',on=True,player_generation=snapshot['player_status']['generation']);wait(lambda:snapshot['player_status']['vitals'].get('sitting'),'Original server accepts sitting while alive')
  result['checks']['original_server_confirms_sitting']=True
  send('player_sit',on=False,player_generation=snapshot['player_status']['generation']);wait(lambda:not snapshot['player_status']['vitals'].get('sitting'),'Original server confirms standing')
  send('combat_attack',on=True,player_generation=snapshot['player_status']['generation'],entity_id='');wait(lambda:snapshot['player_status'].get('attack_on'),'Original server confirms weapon draw')
  result['checks']['original_server_confirms_attack_mode']=True
  send('combat_attack',on=False);wait(lambda:not snapshot['player_status'].get('attack_on'),'Original server confirms stop')
  wait(lambda:any(e['id']=='srv:40' for e in snapshot.get('classic_ui',{}).get('entries',[])),'Original potion entry ready')
  e=next(e for e in snapshot['classic_ui']['entries'] if e['id']=='srv:40');before_hp=snapshot['player_status']['vitals'].get('health',0)
  send('ui_use',entry_id=e['id'],entry_token=e['token']);wait(lambda:snapshot['player_status']['vitals'].get('health',0)>before_hp,'Original potion heals after low-health entry',seconds=20)
  e=next(e for e in snapshot['classic_ui']['entries'] if e['id']=='srv:40');send('ui_detail',entry_id=e['id'],entry_token=e['token'])
  wait(lambda:snapshot['classic_ui'].get('detail',{}).get('status')=='ready' and '- 1 Charges' in snapshot['classic_ui']['detail'].get('lines',[]),'Original remaining potion charge detail')
  result['checks']['original_potion_consumes_one_charge']=True
  result['checks']['original_server_heals_without_client_damage_simulation']=snapshot['player_status']['vitals'].get('health',0)>before_hp
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
  result['checks']['saved_original_charge_count']=any(r['SlotPosition']==40 and r['Charges']==(2 if case=='before' else 1) and r['Count']==1 for r in saved)

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
