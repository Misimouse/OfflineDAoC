"""Ordinary melee XP/level refresh against a disposable NPC; restore private DB and libraries."""
from qa_runtime import *
import subprocess,socket,time,hashlib,traceback,sqlite3,shutil
import sys
source_qa=Path(os.environ.get("DAOC_BRIDGE_SOURCE_QA",str(ROOT.parent/"DAoC-Enhanced-Godot/source/ue5-bridge/ProtocolQA"))).resolve();assert (source_qa/"central_activation_receipts.py").is_file();sys.path.insert(0,str(source_qa))
from central_activation_receipts import verify_files
from prepare_combined_expansion_data import digest
SOURCE=ROOT/'Godot'
training_case=os.environ.get('DAOC_PROGRESSION_TRAINING','off');assert training_case in ['off','on']
D=ROOT/('ProgressionTrainingLab/RealProtocol' if training_case=='on' else 'ProgressionLab/RealProtocol')/time.strftime('%Y%m%d-%H%M%S');D.mkdir(parents=True)
BACKUP=ROOT/'Backups'/('Progression_'+time.strftime('%Y%m%d-%H%M%S'));BACKUP.mkdir()
config_backups=[];candidate_files=[];backed=False
normal=verify_files(ROOT)
normal_paths=[ROOT/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll',INSTALL/'runtime/server/GameServer.dll',INSTALL/'runtime/server/lib/GameServer.dll']
normal_hashes={str(p):digest(p) for p in normal_paths}
def checked():
 db=sqlite3.connect(DB);db.row_factory=sqlite3.Row;assert db.execute('SELECT RunId FROM CodexQaIsolationMarker').fetchone()[0]==RUN.name;return db
class Peer:
 def __init__(self,port):
  deadline=time.monotonic()+30
  while time.monotonic()<deadline:
   try:self.sock=socket.create_connection(('127.0.0.1',port),timeout=.2);break
   except OSError:time.sleep(.2)
  else:raise RuntimeError('QA bridge unavailable')
  self.sock.settimeout(.03);self.buffer=b'';self.snapshot={};self.session='';self.serial=0;self.trace=[]
 def send(self,action,**values):
  self.serial+=1;self.sock.sendall((json.dumps(dict(type='command',session=self.session,id='qa-group:'+str(self.serial),action=action,**values))+'\n').encode())
 def pump(self):
  try:chunk=self.sock.recv(1048576)
  except socket.timeout:return
  if not chunk:raise RuntimeError('QA bridge closed')
  self.buffer+=chunk
  while b'\n' in self.buffer:
   line,self.buffer=self.buffer.split(b'\n',1);value=json.loads(line)
   if value.get('type')=='hello':self.session=value['session']
   if value.get('type')=='snapshot':self.snapshot=value;self.trace.append(value)
 def party(self):return self.snapshot.get('classic_ui',{}).get('party',{})
peers=[];clients=[];handles=[];server=None
result={'passed':False,'real_protocol':True,'disposable_only':True,'checks':{},'errors':[],'source_inputs':{str(p):digest(p) for p in SOURCE.glob('*.gd')}}
def wait(test,label,seconds=20):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  for peer in peers:peer.pump()
  if test():return
 raise RuntimeError(label+'; '+repr([p.snapshot.get('messages',[]) for p in peers]))
def settle(seconds):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  for peer in peers:peer.pump()
try:
 for port in [10351,19737,19738]:
  try:
   with socket.create_connection(('127.0.0.1',port),timeout=.2):raise RuntimeError('Private QA port occupied')
  except (ConnectionRefusedError,socket.timeout):pass
 with checked() as db:
  dest=sqlite3.connect(BACKUP/'before.sqlite3.db');db.backup(dest);dest.close();backed=True
  rows=db.execute("SELECT * FROM DOLCharacters WHERE Name IN ('Codexdruid','Codexfriend')").fetchall();assert len(rows)==2
  leader=dict(next(c for c in rows if c['Name']=='Codexdruid'))
  witness=dict(db.execute("SELECT * FROM Mob WHERE Name='Codex Pet Training Dummy'").fetchone())
  witness.update(Mob_ID='codex-private-progression-witness',Name='Codex Progression Witness',ClassType='DOL.GS.GameNPC',Brain='DOL.AI.Brain.BlankBrain',Guild='',Level=1,Realm=0,Model=123,Flags=0,AggroLevel=0,AggroRange=0,Strength=1,Constitution=1,Dexterity=1,Quickness=1,Speed=0,RoamingRange=0,NPCTemplateID=0,RespawnInterval=3600,X=leader['Xpos']+80,Y=leader['Ypos'],Z=leader['Zpos'])
  keys=list(witness)
  db.execute('INSERT INTO Mob ('+','.join('"'+k+'"' for k in keys)+') VALUES ('+','.join('?' for _ in keys)+')',[witness[k] for k in keys])
  if training_case=='on':
   tutor=dict(witness);tutor.update(Mob_ID='codex-private-earned-points-trainer',Name='Codex Naturalist Trainer',ClassType='DOL.GS.Trainer.NaturalistTrainer',Brain='',Guild='Naturalist Trainer',Level=50,Realm=3,Model=342,X=leader['Xpos']-80)
   keys=list(tutor);db.execute('INSERT INTO Mob ('+','.join('"'+k+'"' for k in keys)+') VALUES ('+','.join('?' for _ in keys)+')',[tutor[k] for k in keys])
  for c in rows:
   db.execute('UPDATE Account SET PrivLevel=1,Realm=3 WHERE Name=?',(c['AccountName'],))
   db.execute("UPDATE DOLCharacters SET Class=53,Level=1,Experience=49,LastFreeLeveled=CURRENT_TIMESTAMP,LastFreeLevel=1,SerializedSpecs='',Health=200,Mana=100,Endurance=100,DeathTime=0,HasGravestone=0,DisabledSpells='',DisabledAbilities='',HCFlag=0 WHERE DOLCharacters_ID=?",(c['DOLCharacters_ID'],))
  result['checks']['ordinary_accounts_only']=all(db.execute('SELECT PrivLevel FROM Account WHERE Name=?',(c['AccountName'],)).fetchone()[0]==1 for c in rows)
 for n,root in enumerate([RUN,RUN/'friend-session']):
  assert root.resolve().is_relative_to(RUN)
  config=root/'bridge_config.json';config_backups.append((config,config.read_bytes()))
  cfg=json.loads(config.read_text());cfg['initial_spawn_m']=[(leader['Xpos']-35*8192)*.025,leader['Zpos']*.025,(leader['Ypos']-51*8192)*.025];config.write_text(json.dumps(cfg),encoding='utf-8')
  for q in SOURCE.glob('*.gd'):shutil.copy2(q,root/'Godot'/q.name)
  q=root/'Godot/visual_bridge.gd';q.write_text(q.read_text(encoding='utf-8-sig').replace('port: int = 19727','port: int = '+str(19737+n)),encoding='utf-8')
 candidate_root=ROOT/'GuildWindowLab/ServerCandidate';candidate=json.loads((candidate_root/'build_receipt.json').read_text());assert candidate['passed']
 for folder in [SERVER,SERVER/'lib',SERVER/'win-x64']:
  for name,expected in candidate['binaries_sha256'].items():
   target=folder/name
   if not target.exists():continue
   assert target.resolve().is_relative_to(RUN);origin=Path(candidate['libraries'])/name;assert digest(origin)==expected
   saved=BACKUP/('server_'+str(len(candidate_files))+'_'+name);shutil.copy2(target,saved);candidate_files.append((target,saved));shutil.copy2(origin,target)
 output=(D/'server.log').open('w',encoding='utf-8');handles.append(output)
 server=subprocess.Popen([str(dotnet),str(SERVER/'CoreServer.dll'),'--start'],cwd=SERVER,env=env,stdin=subprocess.PIPE,stdout=output,stderr=subprocess.STDOUT,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
 deadline=time.monotonic()+40
 while time.monotonic()<deadline:
  try:
   with socket.create_connection(('127.0.0.1',10351),timeout=.2):break
  except OSError:time.sleep(.2)
 else:raise RuntimeError('Isolated server unavailable')
 game=INSTALL/'new-client';sdk=ENGINE/'Binaries/ThirdParty/DotNet/10.0/win-x64'
 for character,suffix,root,port in [('Codexdruid','',RUN,19737),('Codexfriend',':friend',RUN/'friend-session',19738)]:
  account='codexqa'+hashlib.sha256((RUN.name+suffix).encode()).hexdigest()[:10];password=hashlib.sha256(('disposable-local-protocol-qa:'+RUN.name+suffix).encode()).hexdigest()[:24]
  ce=dict(env,DOTNET_ROOT=str(sdk),DOTNET_ROOT_X64=str(sdk),PATH=str(sdk)+os.pathsep+env['PATH'],APPDATA=str(root/'appdata'))
  log=(D/(character+'_client.log')).open('w',encoding='utf-8');handles.append(log);(root/'Reports/live/logout.request').unlink(missing_ok=True)
  client=subprocess.Popen([str(game/'tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'),'--headless','--path',str(RUN/'LobbyProject'),'--script',str(root/'Godot/gateway_main.gd'),'--','--server=127.0.0.1','--server-port=10351','--account='+account,'--password='+password,'--no-world','--bridge-character='+character],cwd=root,env=ce,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  clients.append((client,root));peers.append(Peer(port))
 wait(lambda:all(p.snapshot.get('classic_ui',{}).get('skills_ready') for p in peers),'Both ordinary players ready',40)
 a,b=peers
 def state():return a.snapshot.get('player_status',{})
 def ui():return a.snapshot.get('classic_ui',{})
 wait(lambda:state().get('ready') and ui().get('points',{}).get('xp')==49,'Initial XP and ready status')
 result['checks']['initial_level_and_experience']=ui()['info']['level']==1 and ui()['points']['xp']==49
 initial_entries={e['id']:dict(e) for e in ui().get('entries',[]) if e.get('kind')!='item'}
 result['initial_points']=dict(ui()['points'])
 result['initial_level']=ui()['info']['level']
 if training_case=='on':
  original_heal=next(e for e in ui()['entries'] if e.get('kind')=='spell' and e.get('line')=='Regrowth')
  a.send('ui_assign',bar=2,bank=0,slot=9,entry_id=original_heal['id'],entry_token=original_heal['token'])
  wait(lambda:ui()['bars'][2][0][9].get('token')==original_heal['token'],'Original heal assigned before gaining level')
 wait(lambda:any(e.get('name')==witness['Name'] for e in a.snapshot.get('entities',[])),'Disposable ordinary NPC arrives')
 target=next(e for e in a.snapshot['entities'] if e.get('name')==witness['Name'])
 a.send('target',entity_id=target['id'])
 wait(lambda:a.snapshot.get('interaction',{}).get('target',{}).get('id')==target['id'],'Actual target acknowledged')
 def face():
  me=next(e for e in a.snapshot['entities'] if e['id']=='player:local')
  npc=next((e for e in a.snapshot['entities'] if e['id']==target['id']),None)
  if npc:
   import math
   delta=[npc['position_m'][0]-me['position_m'][0],npc['position_m'][2]-me['position_m'][2]];length=math.hypot(*delta)
   a.send('move',position_m=me['position_m'],forward_xz=[v/length for v in delta] if length>.01 else [1,0],speed_mps=0,target_entity_id=target['id'],target_in_view=True)
 face();settle(.5)
 a.send('combat_attack',on=True,entity_id=target['id'],player_generation=state()['generation'])
 end=time.monotonic()+90
 while time.monotonic()<end and ui().get('info',{}).get('level',1)==1:
  settle(.2);face()
  if not state().get('vitals',{}).get('alive',True):raise RuntimeError('Disposable player died before level-up')
 wait(lambda:ui().get('info',{}).get('level',1)>1,'Original melee kill advances level',5)
 a.send('combat_attack',on=False);settle(3)
 result['final_points']=dict(ui()['points']);result['final_level']=ui()['info']['level']
 result['checks']['melee_kill_awards_experience']=ui()['points']['xp']>49
 result['checks']['level_refresh_without_reconnect']=ui()['info']['level']>1
 result['checks']['points_and_threshold_refresh']=ui()['points']['xp_next']>result['initial_points']['xp_next'] and 0<=ui()['points']['level_permill']<=1000
 result['checks']['specialization_points_received']=ui()['points']['spec_points']>result['initial_points']['spec_points']
 final_entries={e['id']:dict(e) for e in ui().get('entries',[]) if e.get('kind')!='item'}
 result['checks']['server_skill_catalogue_remains_available']=bool(initial_entries) and bool(final_entries) and ui()['skills_ready']
 result['checks']['no_level_change_for_idle_peer']=b.snapshot['classic_ui']['info']['level']==1 and b.snapshot['classic_ui']['points']['xp']==49
 result['catalogue_before']=initial_entries;result['catalogue_after']=final_entries
 result['checks']['defeated_npc_no_longer_alive']=not any(e['id']==target['id'] and e.get('health',1)>0 and e.get('state')!='dead' for e in a.snapshot.get('entities',[]))
 if training_case=='on':
  wait(lambda:any(e.get('name')==tutor['Name'] for e in a.snapshot['entities']),'Original Naturalist trainer visible')
  npc=next(e for e in a.snapshot['entities'] if e.get('name')==tutor['Name'])
  a.send('interact',entity_id=npc['id']);a.send('trainer_refresh')
  def trainer():return ui().get('trainer',{})
  wait(lambda:trainer().get('ready') and not trainer().get('pending'),'Original training list ready')
  row=dict(next(e for e in trainer()['specs'] if e['name']=='Regrowth'))
  assert row['level']==1 and row['cost']==2 and row['can_train'] and trainer()['spec_points']==2
  result['checks']['earned_points_available_at_original_trainer']=True
  a.send('trainer_train',training_kind='spec',training_index=row['index'],training_token=row['token'])
  wait(lambda:any(e['name']=='Regrowth' and e['level']==2 for e in trainer().get('specs',[])) and not trainer().get('pending') and trainer()['spec_points']==0,'Server confirms original training cost and rank')
  wait(lambda:any(e['name']=='Regrowth' and e['level']==2 for e in ui().get('specs',[])) and ui()['points']['spec_points']==0,'Character sheet receives trained rank and points')
  result['checks']['earned_points_spent_exactly_once']=True
  result['checks']['trained_rank_reaches_character_sheet']=True
  a.send('trainer_train',training_kind='spec',training_index=row['index'],training_token=row['token']);settle(.5)
  result['checks']['old_training_token_cannot_spend_again']=trainer()['spec_points']==0 and any(e['name']=='Regrowth' and e['level']==2 for e in trainer()['specs']) and 'changed' in trainer().get('feedback','').lower()
  slot=ui()['bars'][2][0][9]
  current=next((e for e in ui()['entries'] if e['id']==slot.get('id') and e['token']==slot.get('token')),None)
  result['checks']['saved_heal_still_matches_current_spell']=bool(current and current['name']==original_heal['name'] and current['kind']=='spell')
  a.send('target_self');settle(.3)
  a.send('ui_use',entry_id=current['id'],entry_token=current['token'])
  wait(lambda:ui().get('feedback')=='Request sent to server.','Retained heal can request original spell after training')
  result['checks']['retained_spell_request_accepted_after_training']=True
  result['trained_specialization']='Regrowth';result['trained_rank']=2;result['final_spec_points']=0
 result['passed']=all(result['checks'].values())
except Exception:result['errors'].append(traceback.format_exc())
finally:
 if peers and not peers[0].snapshot.get('player_status',{}).get('vitals',{}).get('alive',True):
  try:
   peers[0].send('chat',text='/release');wait(lambda:peers[0].snapshot.get('player_status',{}).get('vitals',{}).get('alive',False),'Release disposable player before logout',15)
  except Exception:result['errors'].append('Release cleanup: '+traceback.format_exc())
 for i,peer in enumerate(peers):
  (D/('snapshot_'+str(i)+'.json')).write_text(json.dumps(peer.snapshot),encoding='utf-8')
  if peer.session:
   try:peer.send('logout')
   except OSError:pass
 for client,root in clients:
  if client.poll() is None:
   (root/'Reports/live/logout.request').write_text('logout',encoding='utf-8')
   try:client.wait(timeout=100)
   except subprocess.TimeoutExpired:client.kill();client.wait();result['errors'].append('Private client forced stop')
 for peer in peers:peer.sock.close()
 if server and server.poll() is None:
  server.stdin.write('exit\n');server.stdin.flush()
  try:server.wait(timeout=45)
  except subprocess.TimeoutExpired:server.kill();server.wait();result['errors'].append('Private server forced stop')
 for handle in handles:handle.close()
 for target,saved in reversed(candidate_files):assert target.resolve().is_relative_to(RUN);shutil.copy2(saved,target)
 for config,raw in config_backups:config.write_bytes(raw)
 if backed and result['passed']:
  with checked() as db:
   saved=db.execute("SELECT Level,Experience FROM DOLCharacters WHERE Name='Codexdruid'").fetchone()
   result['checks']['normal_logout_saves_level_and_experience']=saved['Level']==result['final_level'] and saved['Experience']==result['final_points']['xp']
   result['passed']=result['passed'] and result['checks']['normal_logout_saves_level_and_experience']
   if training_case=='on':
    saved_specs=db.execute("SELECT SerializedSpecs FROM DOLCharacters WHERE Name='Codexdruid'").fetchone()[0]
    result['saved_specializations']=saved_specs
    result['checks']['trained_specialization_saved_on_logout']='Regrowth|2' in saved_specs
    result['passed']=result['passed'] and result['checks']['trained_specialization_saved_on_logout']
 if backed:
  with checked() as db:
   src=sqlite3.connect(BACKUP/'before.sqlite3.db');src.backup(db);src.close()
  result['database_restored']=True
 result['private_server_restored']=bool(candidate_files)
 result['normal_shutdown']=bool(clients) and all(c.returncode==0 for c,_ in clients) and server is not None and server.returncode==0
 result['normal_runtime_unchanged']=all(digest(Path(p))==h for p,h in normal_hashes.items())
 result['passed']=result['passed'] and result['normal_shutdown'] and result.get('database_restored',False) and result['normal_runtime_unchanged'] and not result['errors'] and all(digest(Path(p))==h for p,h in result['source_inputs'].items())
 (D/'verified.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='source_inputs'}));assert result['passed']
