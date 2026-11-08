"""Verify original personal/account vault transactions and persistence using only a marked disposable DOL database."""
from qa_runtime import *
import sqlite3,subprocess,socket,time,hashlib,shutil,traceback

D=ROOT/'VaultPersistenceLab/RealProtocol'/time.strftime('%Y%m%d-%H%M%S');D.mkdir(parents=True)
SOURCE=Path(os.environ.get('DAOC_BRIDGE_QA_SOURCE',str(ROOT/'Godot')))
assert (SOURCE/'inventory_state.gd').exists()
result={'passed':False,'real_protocol':True,'disposable_only':True,'checks':{},'errors':[],'source_inputs':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCE.glob('*.gd')}}
server=client=sock=None;logs=[];session='';snapshot={};buffer=b'';serial=0;backed=False
normal_targets=[Path(r['target']) for r in json.loads((ROOT/'ExpansionRaceLab/CentralDelivery/MinotaurActivation/installed.json').read_text())['files'] if Path(r['target']).name in ['GameServer.dll','CoreBase.dll','CoreDatabase.dll','live_gateway.gd']] + [ROOT/'Godot/visual_bridge.gd',ROOT/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll']
normal_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in normal_targets}
candidate_files=[]
backup=ROOT/'Backups'/('VaultPersistenceProtocolQA_'+time.strftime('%Y%m%d-%H%M%S'));backup.mkdir()
config=RUN/'bridge_config.json';config_bytes=config.read_bytes()
def checked():
 db=sqlite3.connect(DB);db.row_factory=sqlite3.Row;assert db.execute('SELECT RunId FROM CodexQaIsolationMarker').fetchone()[0]==RUN.name;return db
def update(db,table,keyfield,key,values):db.execute('UPDATE '+table+' SET '+','.join('"'+k+'"=?' for k in values)+' WHERE "'+keyfield+'"=?',list(values.values())+[key])
def send(action,**values):
 global serial
 serial+=1;sock.sendall((json.dumps(dict(type='command',session=session,id='vault:'+str(serial),action=action,**values))+'\n').encode())
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
  update(db,'DOLCharacters','DOLCharacters_ID',char['DOLCharacters_ID'],{'Level':20,'HCFlag':0})
  def insert(table,row):db.execute('INSERT INTO '+table+' ('+','.join('"'+k+'"' for k in row)+') VALUES ('+','.join('?' for k in row)+')',list(row.values()))
  mob=dict(db.execute("SELECT * FROM Mob WHERE Name='Codex Pet Training Dummy'").fetchone());assert mob
  for suffix,kind in [('Personal','DOL.GS.GameVaultKeeper'),('Account','DOL.GS.AccountVaultKeeper')]:
   # The server resolves guild scripts before explicit ClassType. Do not give
   # the account keeper the personal keeper's registered "Vault Keeper" guild.
   row=dict(mob);row.update(Mob_ID='codex-private-vault-'+suffix,Name='Codex '+suffix+' Keeper',Guild='Private '+suffix+' Vault',Model=1984,ClassType=kind,Brain='',Realm=3,Speed=0,AggroLevel=0,X=char['Xpos']+80,Y=char['Ypos'],Z=char['Zpos'],Region=char['Region'])
   insert('Mob',row)
  account_owner=char['AccountName']+'_Hibernia' # GetOwner interpolates the original eRealm enum name.
  original=dict(db.execute('SELECT * FROM Inventory WHERE OwnerID=? LIMIT 1',(char['DOLCharacters_ID'],)).fetchone())
  db.execute('DELETE FROM Inventory WHERE OwnerID=? AND (SlotPosition BETWEEN 40 AND 79 OR SlotPosition BETWEEN 110 AND 149)',(char['DOLCharacters_ID'],))
  db.execute('DELETE FROM Inventory WHERE OwnerID=? AND SlotPosition BETWEEN 2500 AND 2699',(account_owner,))
  for slot,template_id,count in [(40,'minor_lethal_poison',3),(41,'club',1),(42,'cloak',1)]:
   template=db.execute('SELECT * FROM ItemTemplate WHERE Id_nb=?',(template_id,)).fetchone();assert template
   row=dict(original);row.update(Inventory_ID='codex-private-vault-item-'+str(slot),OwnerID=char['DOLCharacters_ID'],SlotPosition=slot,ITemplate_Id=template_id,UTemplate_Id='',Count=count,Emblem=0,Color=0,IsCrafted=0,IsROG=0,Condition=template['MaxCondition'],Durability=template['MaxCondition'])
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
 wait(lambda:snapshot.get('classic_ui',{}).get('skills_ready') and inv().get('ready') and item(40) is not None and item(42) is not None,'Ordinary private character ready')
 wait(lambda:all(any(e.get('name')=='Codex '+kind+' Keeper' for e in snapshot.get('entities',[])) for kind in ['Personal','Account']),'Original private keeper services available')
 def vault():return inv().get('vault',{})
 def open_keeper(kind):
  keeper=next(e for e in snapshot['entities'] if e.get('name')=='Codex '+kind+' Keeper')
  send('target',entity_id=keeper['id']);wait(lambda:snapshot.get('interaction',{}).get('target',{}).get('id')==keeper['id'],'Select original keeper')
  send('interact',entity_id=keeper['id']);wait(lambda:vault().get('valid') and vault().get('keeper_id')==keeper['id'],'Original keeper opens container')
 def move(source,destination,token=None):
  row=item(source);assert row and not inv().get('pending')
  send('inventory_move',slot=source,to_slot=destination,item_token=row['token'],inventory_revision=inv()['state_revision'],vault_token=vault().get('token','') if token is None else token)
 def moved(source,destination,label):wait(lambda:item(source) is None and item(destination) is not None and not inv().get('pending'),label)
 def page(word):
  # Original GameLiving.WhisperReceive enforces 1500 ms for ordinary players,
  # in addition to WhisperCommandHandler's 500 ms command interval.
  settle(1.7)
  before=vault()['token'];talk=snapshot['interaction']['talk'];assert word in talk['keywords']
  send('keyword',word=word,reply_id=talk['id']);wait(lambda:vault().get('valid') and vault().get('token')!=before,'Original account page '+word)
 baseline=money();before=dict(item(40));move(40,110,'forged-closed-token');settle(.5)
 result['checks']['closed_vault_rejects_deposit']=item(40)==before and not inv().get('pending')
 open_keeper('Personal');result['checks']['personal_original_window']=vault()['first']==110 and vault()['count']==40
 move(40,110);moved(40,110,'Deposit stack into personal vault')
 result['checks']['personal_full_stack_preserved']=item(110)['count']==3
 move(110,149);moved(110,149,'Reorder at final personal vault slot')
 result['checks']['personal_final_slot']=item(149)['count']==3
 move(149,40);moved(149,40,'Withdraw original stack')
 result['checks']['personal_withdrawal']=item(40)['count']==3
 move(40,110);moved(40,110,'Leave personal deposit for save verification');personal_token=vault()['token']
 open_keeper('Account');result['checks']['account_original_window']=vault()['first']==150 and vault()['count']==100 and item(110) is None
 before=dict(item(41));move(41,150,personal_token);settle(.5)
 result['checks']['previous_keeper_token_rejected']=item(41)==before and item(150) is None and not inv().get('pending')
 move(41,150);moved(41,150,'Deposit first account page');first_token=vault()['token']
 result['checks']['account_first_deposit']=item(150)['name'].lower()=='club'
 page('second');result['checks']['account_pages_isolated']=item(150) is None
 before=dict(item(42));move(42,249,first_token);settle(.5)
 result['checks']['previous_page_token_rejected']=item(42)==before and item(249) is None and not inv().get('pending')
 move(42,249);moved(42,249,'Deposit last slot on second account page')
 result['checks']['account_second_final_slot']=item(249)['name'].lower()=='cloak'
 page('first');result['checks']['return_to_first_page']=item(150) is not None and item(249) is None
 move(150,41);moved(150,41,'Withdraw first account page item')
 result['checks']['account_withdrawal']=item(41)['name'].lower()=='club'
 move(41,150);moved(41,150,'Leave first account deposit for save verification')
 token=vault()['token'];send('vault_close',vault_token=token);wait(lambda:not vault().get('valid'),'Close current vault')
 result['checks']['closed_hides_cached_storage']=item(150) is None and item(249) is None
 result['checks']['vault_transactions_do_not_charge']=money()==baseline
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
   saved=[dict(r) for r in db.execute("SELECT Inventory_ID,OwnerID,SlotPosition,ITemplate_Id,Count FROM Inventory WHERE Inventory_ID LIKE 'codex-private-vault-item-%'")]
  (D/'saved_items.json').write_text(json.dumps(saved,indent=2),encoding='utf-8')
  result['checks']['personal_saved_owner_slot_count']=any(r['OwnerID']==char['DOLCharacters_ID'] and r['SlotPosition']==110 and r['Count']==3 and r['ITemplate_Id']=='minor_lethal_poison' for r in saved)
  result['checks']['account_first_saved_owner_slot']=any(r['OwnerID']==account_owner and r['SlotPosition']==2500 and r['ITemplate_Id']=='club' for r in saved)
  result['checks']['account_second_saved_last_slot']=any(r['OwnerID']==account_owner and r['SlotPosition']==2699 and r['ITemplate_Id']=='cloak' for r in saved)
  result['checks']['no_duplicate_items']=len(saved)==3
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
