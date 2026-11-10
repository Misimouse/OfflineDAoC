"""Ordinary melee XP/level refresh against a disposable NPC; restore private DB and libraries."""
from qa_runtime import *
import subprocess,socket,time,hashlib,traceback,sqlite3,shutil
import sys
source_qa=Path(os.environ.get("DAOC_BRIDGE_SOURCE_QA",str(ROOT.parent/"DAoC-Enhanced-Godot/source/ue5-bridge/ProtocolQA"))).resolve();assert (source_qa/"central_activation_receipts.py").is_file();sys.path.insert(0,str(source_qa))
from central_activation_receipts import verify_files
from prepare_combined_expansion_data import digest
source_mode=os.environ.get('DAOC_PROGRESSION_GODOT','installed');assert source_mode in ['installed','candidate']
SOURCE=source_qa.parent/'Godot' if source_mode=='candidate' else ROOT/'Godot'
training_case=os.environ.get('DAOC_PROGRESSION_TRAINING','off');assert training_case in ['off','on','cast','return','switch']
inventory_probe=os.environ.get('DAOC_CROSS_CHARACTER_INVENTORY','0')=='1'
assert not inventory_probe or training_case=='switch'
sight_harness_probe=os.environ.get('DAOC_NATIVE_SIGHT_HARNESS','0')=='1'
assert not sight_harness_probe or (training_case=='cast' and source_mode=='installed')
cast_movement_probe=os.environ.get('DAOC_CAST_MOVEMENT_PROBE','0')=='1'
assert not cast_movement_probe or sight_harness_probe
assert source_mode!='candidate' or training_case in ['on','switch']
budget_receipt=ROOT/'TrainerAffordabilityLab/installed.json';budget_probe=source_mode=='candidate' or (budget_receipt.exists() and json.loads(budget_receipt.read_text()).get('installed',False))
case_lab={'off':'ProgressionLab','on':'ProgressionTrainingLab','cast':'ProgressionCastingLab','return':'ProgressionReentryLab','switch':'CrossClassSwitchLab'}[training_case]
output_stage='RealProtocol'
if training_case=='on' and budget_probe:
 case_lab='TrainerAffordabilityLab';output_stage='InstalledRealProtocol' if source_mode=='installed' else 'RealProtocol'
elif training_case=='switch':
 page_receipt=ROOT/'CrossClassSwitchLab/installed.json'
 output_stage='CandidateRealProtocol' if source_mode=='candidate' else 'InstalledRealProtocol' if page_receipt.exists() and json.loads(page_receipt.read_text()).get('installed',False) else 'RealProtocol'
if inventory_probe:case_lab='CharacterInventorySwitchLab';output_stage='CandidateRealProtocol' if source_mode=='candidate' else 'InstalledRealProtocol' if (ROOT/'CharacterInventorySwitchLab/installed.json').exists() else 'RealProtocol'
if sight_harness_probe:case_lab='NativeSightHarnessLab';output_stage='RealProtocol'
if cast_movement_probe:case_lab='SpellMovementRoundtripLab'
D=ROOT/case_lab/output_stage/time.strftime('%Y%m%d-%H%M%S');D.mkdir(parents=True)
BACKUP=ROOT/'Backups'/('Progression_'+time.strftime('%Y%m%d-%H%M%S'));BACKUP.mkdir()
config_backups=[];candidate_files=[];backed=False;relay=None
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
  if sight_harness_probe:
   import struct,math
   spawn_config=ROOT/'bridge_config.json';result['source_inputs'][str(spawn_config)]=digest(spawn_config)
   spawn=json.loads(spawn_config.read_text())['initial_spawn_m'];leader['Xpos']=round(float(spawn[0])*40)+35*8192;leader['Ypos']=round(float(spawn[2])*40)+51*8192
   heights=INSTALL/'new-client/godot/content/zones/zone207/heights.f32';result['source_inputs'][str(heights)]=digest(heights)
   grid=struct.unpack('<'+str(257*257)+'f',heights.read_bytes());gx=(leader['Xpos']-35*8192)/256.;gz=(leader['Ypos']-51*8192)/256.;i=math.floor(gx);j=math.floor(gz);assert 0<=i<256 and 0<=j<256
   u=gx-i;w=gz-j;h0,h1,h2,h3=[grid[k] for k in [j*257+i,j*257+i+1,(j+1)*257+i,(j+1)*257+i+1]]
   height=h0+u*(h1-h0)+w*(h2-h0) if u+w<=1 else h3+(1-u)*(h2-h3)+(1-w)*(h1-h3)
   result['private_spawn_ground_m']=height;result['private_spawn_previous_m']=leader['Zpos']*.025;leader['Zpos']=round((height+.10)*40)
   for c in rows:db.execute('UPDATE DOLCharacters SET Xpos=?,Ypos=?,Zpos=? WHERE DOLCharacters_ID=?',(leader['Xpos'],leader['Ypos'],leader['Zpos'],c['DOLCharacters_ID']))
  witness=dict(db.execute("SELECT * FROM Mob WHERE Name='Codex Pet Training Dummy'").fetchone())
  witness.update(Mob_ID='codex-private-progression-witness',Name='Codex Progression Witness',ClassType='DOL.GS.GameNPC',Brain='DOL.AI.Brain.BlankBrain',Guild='',Level=1,Realm=0,Model=123,Flags=0,AggroLevel=0,AggroRange=0,Strength=1,Constitution=1,Dexterity=1,Quickness=1,Speed=0,RoamingRange=0,NPCTemplateID=0,RespawnInterval=3600,X=leader['Xpos']+80,Y=leader['Ypos'],Z=leader['Zpos'])
  keys=list(witness)
  db.execute('INSERT INTO Mob ('+','.join('"'+k+'"' for k in keys)+') VALUES ('+','.join('?' for _ in keys)+')',[witness[k] for k in keys])
  if training_case!='off':
   tutor=dict(witness);tutor.update(Mob_ID='codex-private-earned-points-trainer',Name='Codex Naturalist Trainer',ClassType='DOL.GS.Trainer.NaturalistTrainer',Brain='',Guild='Naturalist Trainer',Level=50,Realm=3,Model=342,X=leader['Xpos']-80)
   keys=list(tutor);db.execute('INSERT INTO Mob ('+','.join('"'+k+'"' for k in keys)+') VALUES ('+','.join('?' for _ in keys)+')',[tutor[k] for k in keys])
  for c in rows:
   db.execute('UPDATE Account SET PrivLevel=1,Realm=3 WHERE Name=?',(c['AccountName'],))
   db.execute("UPDATE DOLCharacters SET Class=53,Level=1,Experience=49,LastFreeLeveled=CURRENT_TIMESTAMP,LastFreeLevel=1,SerializedSpecs='',Health=200,Mana=100,Endurance=100,DeathTime=0,HasGravestone=0,DisabledSpells='',DisabledAbilities='',HCFlag=0 WHERE DOLCharacters_ID=?",(c['DOLCharacters_ID'],))
  if training_case=='cast':
   # Injured ordinary healing witness only; never change health while logged in.
   db.execute("UPDATE DOLCharacters SET Class=47,Level=20,Experience=25899950,Health=1,Xpos=?,Ypos=?,Zpos=?,Region=200 WHERE Name='Codexfriend'",(leader['Xpos']+20,leader['Ypos']+20,leader['Zpos']))
  if training_case=='switch':
   import uuid
   uid=uuid.uuid4().hex;swap_name='Codexswap'+''.join(chr(97+int(ch,16)) for ch in uid[:6])
   slots={r[0] for r in db.execute('SELECT AccountSlot FROM DOLCharacters WHERE AccountName=?',(leader['AccountName'],))}
   swap=dict(leader);swap.update(DOLCharacters_ID=uid,Name=swap_name,AccountSlot=next(slot for slot in range(300,310) if slot not in slots),Class=51,Level=1,Experience=0,SerializedSpecs='',SerializedAbilities='',SerializedRealmAbilities='',DisabledSpells='',DisabledAbilities='',Health=100,Mana=100,DeathTime=0,HasGravestone=0,HCFlag=0)
   if inventory_probe:
    for denomination in ['Copper','Silver','Gold','Platinum','Mithril']:swap[denomination]=0
   keys=list(swap);db.execute('INSERT INTO DOLCharacters ('+','.join('"'+k+'"' for k in keys)+') VALUES ('+','.join('?' for _ in keys)+')',[swap[k] for k in keys])
   result['swap_character']=swap_name
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
 if training_case!='off':
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
 result['checks']['no_level_change_for_idle_peer']=b.snapshot['classic_ui']['info']['level']==(20 if training_case=='cast' else 1) and b.snapshot['classic_ui']['points']['xp']==(25899950 if training_case=='cast' else 49)
 result['catalogue_before']=initial_entries;result['catalogue_after']=final_entries
 result['checks']['defeated_npc_no_longer_alive']=not any(e['id']==target['id'] and e.get('health',1)>0 and e.get('state')!='dead' for e in a.snapshot.get('entities',[]))
 if training_case!='off':
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
  if budget_probe:
   unavailable=dict(next(e for e in trainer()['specs'] if e['name']=='Nurture'))
   result['checks']['zero_budget_marks_lower_rank_unavailable']=unavailable['level']==1 and unavailable['cost']==2 and not unavailable['can_train']
   a.send('trainer_train',training_kind='spec',training_index=unavailable['index'],training_token=unavailable['token']);settle(.5)
   result['checks']['current_unaffordable_training_request_refused']=not trainer()['pending'] and trainer()['spec_points']==0 and 'requirements' in trainer().get('feedback','').lower() and any(e['name']=='Nurture' and e['level']==1 for e in trainer()['specs'])
  a.send('trainer_train',training_kind='spec',training_index=row['index'],training_token=row['token']);settle(.5)
  result['checks']['old_training_token_cannot_spend_again']=trainer()['spec_points']==0 and any(e['name']=='Regrowth' and e['level']==2 for e in trainer()['specs']) and 'changed' in trainer().get('feedback','').lower()
  slot=ui()['bars'][2][0][9]
  current=next((e for e in ui()['entries'] if e['id']==slot.get('id') and e['token']==slot.get('token')),None)
  result['checks']['saved_heal_still_matches_current_spell']=bool(current and current['name']==original_heal['name'] and current['kind']=='spell')
  if training_case in ['on','return','switch']:
   a.send('target_self');settle(.3)
   a.send('ui_use',entry_id=current['id'],entry_token=current['token'])
   wait(lambda:ui().get('feedback')=='Request sent to server.','Retained heal can request original spell after training')
   result['checks']['retained_spell_request_accepted_after_training']=True
  else:
   import importlib.util
   helper=source_qa.parent/'magic_sight_relay.py';result['source_inputs'][str(helper)]=digest(helper)
   spec=importlib.util.spec_from_file_location('progression_native_sight',helper);native_sight=importlib.util.module_from_spec(spec);spec.loader.exec_module(native_sight)
   target_config=ROOT/'playable_project.json';target_cfg=json.loads(target_config.read_text());result['source_inputs'][str(target_config)]=digest(target_config)
   project=(ROOT/target_cfg['project']).resolve();assert project.is_file()
   result['native_world']=dict(project=str(project),map=target_cfg['map'],read_only=True,offscreen=True,headless_geometry=sight_harness_probe)
   relay=native_sight.NativeSightRelay(a.sock,ROOT,a.session,a.snapshot,project=project,world=target_cfg['map'],report_dir=D/'NativeSight',offscreen=True,enabled_plugins=target_cfg.get('enable_plugins',[]),navigation_probe=sight_harness_probe,headless_geometry=sight_harness_probe);a.sock=relay
   wait(lambda:relay.read_report().get('local_animation'),'Current native map read-only sight client ready',80)
   def cast():return ui().get('casting',{})
   def avitals():return state().get('vitals',{})
   def bvitals():return b.snapshot.get('player_status',{}).get('vitals',{})
   wait(lambda:any(e.get('name')=='Codexfriend' for e in a.snapshot['entities']) and bvitals().get('ready',True) and bvitals().get('health',0)>0,'Injured healing witness visible')
   friend=next(e for e in a.snapshot['entities'] if e.get('name')=='Codexfriend')
   assert bvitals()['health']<bvitals()['max_health']
   result['checks']['ordinary_peer_still_injured_before_heal']=True
   a.send('ui_bank',bar=2,bank=0);wait(lambda:ui()['banks'][2]==0,'Select page holding original saved heal')
   a.send('target',entity_id=friend['id'])
   wait(lambda:a.snapshot['interaction']['target']['id']==friend['id'],'Select ordinary healing recipient')
   me=next(e for e in a.snapshot['entities'] if e['id']=='player:local')
   import math
   delta=[friend['position_m'][0]-me['position_m'][0],friend['position_m'][2]-me['position_m'][2]];length=math.hypot(*delta)
   a.send('move',position_m=me['position_m'],forward_xz=[v/length for v in delta],speed_mps=0,target_entity_id=friend['id'],target_in_view=True);settle(.3)
   if cast_movement_probe:
    facing=[v/length for v in delta]
    def point():return list(next(e['position_m'] for e in a.snapshot['entities'] if e['id']=='player:local'))
    def moving():
     p=point();p[0]+=.02;a.send('move',position_m=p,forward_xz=facing,speed_mps=1,target_entity_id=friend['id'],target_in_view=True)
    before_mana=avitals()['mana'];before_seq=cast().get('seq',0);moving();a.send('ui_use_slot',bar=2,slot=9);last_move=[time.monotonic()]
    def refused_while_moving():
     if time.monotonic()-last_move[0]>.10:moving();last_move[0]=time.monotonic()
     return any(('move' in m.lower() or 'moving' in m.lower() or 'stand still' in m.lower()) and ('cast' in m.lower() or 'spell' in m.lower()) for m in a.snapshot.get('messages',[]))
    wait(refused_while_moving,'Original server refuses an ordinary heal started while moving',6)
    a.send('move',position_m=point(),forward_xz=facing,speed_mps=0,target_entity_id=friend['id'],target_in_view=True);settle(.4)
    result['checks']['moving_heal_refused_or_interrupted_without_power_cost']=cast().get('phase','') in ['', 'interrupted'] and avitals()['mana']==before_mana
    settle(1);seq=cast().get('seq',0);a.send('ui_use_slot',bar=2,slot=9)
    wait(lambda:cast().get('seq',0)>seq and cast().get('phase')=='casting','Stationary heal starts before movement interruption')
    before_mana=avitals()['mana'];moving()
    wait(lambda:cast().get('phase')=='interrupted','Original movement interrupts pending heal')
    result['checks']['moving_interrupts_prepared_heal_without_power_cost']=avitals()['mana']==before_mana
    a.send('move',position_m=point(),forward_xz=facing,speed_mps=0,target_entity_id=friend['id'],target_in_view=True);settle(1)
   seq=cast().get('seq',0);before_hp=bvitals()['health'];before_mana=avitals()['mana']
   a.send('ui_use_slot',bar=2,slot=9)
   wait(lambda:cast().get('seq',0)>seq and cast().get('phase')=='casting','Actual server confirms retained quickbar heal preparation')
   result['checks']['trained_quickbar_heal_gets_server_cast']=True
   wait(lambda:cast().get('phase')=='released','Actual server releases retained quickbar heal')
   wait(lambda:bvitals()['health']>before_hp and avitals()['mana']<before_mana,'Server healing and power consumption')
   wait(lambda:any('heal Codexfriend for' in m for m in a.snapshot.get('messages',[])),'Original heal result identifies recipient')
   result['healing']={'hp_before':before_hp,'hp_after':bvitals()['health'],'mana_before':before_mana,'mana_after':avitals()['mana'],'cast':dict(cast())}
   result['checks']['server_heal_result_names_actual_recipient']=True
   result['checks']['actual_heal_increases_peer_health']=True
   result['checks']['actual_heal_consumes_power']=True
   wait(lambda:ui().get('reuse_ms',{}).get(current['id'],0)==0,'Original baseline spell has no remaining reuse timer')
   settle(2);seq=cast().get('seq',0);before_mana=avitals()['mana']
   a.send('ui_use_slot',bar=2,slot=9)
   wait(lambda:cast().get('seq',0)>seq and cast().get('phase')=='casting','Retained quickbar can prepare another actual heal')
   wait(lambda:cast().get('phase')=='released' and avitals()['mana']<before_mana,'Original repeat heal completes and consumes power')
   result['checks']['retained_spell_can_cast_again_after_recovery']=True
   buff=next(e for e in ui()['entries'] if e.get('kind')=='spell' and e.get('name')=='Minor Bark Skin')
   a.send('ui_assign',bar=2,bank=0,slot=8,entry_id=buff['id'],entry_token=buff['token'])
   wait(lambda:ui()['bars'][2][0][8].get('token')==buff['token'],'Place newly received level spell')
   a.send('target_self');settle(2);seq=cast().get('seq',0)
   a.send('ui_use_slot',bar=2,slot=8)
   wait(lambda:cast().get('seq',0)>seq and cast().get('phase')=='casting','New level spell begins actual server cast')
   wait(lambda:any(e.get('name')=='Minor Bark Skin' for e in ui().get('effects',[])),'Original server applies newly received buff effect')
   result['checks']['new_level_spell_usable_from_quickbar']=True
   result['checks']['new_level_buff_confirmed_in_server_effects']=True
   result['buff_effects']=ui()['effects']
   result['native_sight_answers']=relay.answers;result['checks']['actual_native_geometry_answered_server_sight']=bool(relay.answers) and all(e.get('question') for e in relay.answers)
   if sight_harness_probe:
    settle(2);native=relay.read_report();result['native_active_scene']={k:native.get(k) for k in ['map','navigation_ready','navigation_probe','character_grounded','position_m','pawn_position_m','camera_position_m','terrain_colliders','structure_colliders','tree_collider_instances']}
    result['checks']['native_character_stays_on_terrain']=bool(native.get('character_grounded')) and abs(native['position_m'][1]-result['private_spawn_ground_m'])<.5
  result['trained_specialization']='Regrowth';result['trained_rank']=2;result['final_spec_points']=0
 if training_case in ['return','switch']:
  a.send('ui_bank',bar=2,bank=0);wait(lambda:ui()['banks'][2]==0,'Select saved quickbar page before exit')
  old_session=a.session;old_generation=state()['generation']
  a.send('chat',text='/quit')
  wait(lambda:not a.snapshot.get('in_game') and a.snapshot.get('character_lobby',{}).get('ready'),'Normal saved return to character selection',100)
  result['checks']['saved_quit_preserves_bridge_connection']=a.session==old_session
  result['checks']['selection_clears_old_world']=not a.snapshot.get('entities')
  result['checks']['selection_clears_old_target']=not a.snapshot.get('interaction',{}).get('target',{}).get('id')
  result['checks']['selection_clears_old_cast']=not ui().get('casting')
  lobby=a.snapshot['character_lobby'];roster=next(e for e in lobby['characters'] if e['name']=='Codexdruid')
  result['checks']['selection_roster_reflects_earned_level']=roster['level']==2
  a.send('character_enter',name='Codexdruid',lobby_revision=lobby['revision'])
  wait(lambda:a.snapshot.get('in_game') and state().get('ready') and state()['generation']>old_generation and ui().get('skills_ready'),'Same-connection character reentry receives fresh generation',40)
  result['checks']['reentry_restores_server_progression']=ui()['info']['level']==2 and ui()['points']['xp']==64 and ui()['points']['spec_points']==0 and any(e['name']=='Regrowth' and e['level']==2 for e in ui()['specs'])
  slot=ui()['bars'][2][0][9];fresh=next((e for e in ui()['entries'] if e['id']==slot.get('id') and e['token']==slot.get('token') and e['name']==original_heal['name']),None)
  result['checks']['reentry_restores_valid_saved_shortcut_and_page']=bool(fresh) and ui()['banks'][2]==0
  a.send('target_self');settle(.3);a.send('ui_use_slot',bar=2,slot=9)
  wait(lambda:ui().get('feedback')=='Request sent to server.','Saved shortcut resolves after reentry')
  result['checks']['saved_shortcut_request_accepted_after_reentry']=True
 if training_case=='switch':
  if inventory_probe:
   wait(lambda:a.snapshot.get('inventory',{}).get('ready'),'Original inventory ready')
   old_inventory=json.loads(json.dumps(a.snapshot['inventory']))
   old_shield=next(e for e in old_inventory['items'] if e['slot']==11)
   assert any(old_inventory['money'].values()) and old_inventory['items']
  # Use a non-default old-character page to expose accidental page inheritance.
  a.send('ui_assign',bar=2,bank=4,slot=9,entry_id=fresh['id'],entry_token=fresh['token']);a.send('ui_bank',bar=2,bank=4)
  wait(lambda:ui()['banks'][2]==4 and ui()['bars'][2][4][9].get('token')==fresh['token'],'Save distinct original-character quickbar page')
  a.send('chat',text='/quit');wait(lambda:not a.snapshot.get('in_game') and a.snapshot.get('character_lobby',{}).get('ready'),'Return before class switch',100)
  lobby=a.snapshot['character_lobby'];assert any(e['name']==swap_name for e in lobby['characters'])
  if inventory_probe:
   closed=a.snapshot
   result['checks']['selection_clears_inventory_and_operations']=not closed['inventory']['items'] and not closed['inventory']['pending']
   result['checks']['selection_clears_trainer_and_dialogs']=not closed['classic_ui']['trainer']['ready'] and not closed['interaction']['dialogs'] and not closed['interaction']['talk'] and not closed['interaction']['merchant']
  generation=state()['generation'];a.send('character_enter',name=swap_name,lobby_revision=lobby['revision'])
  wait(lambda:a.snapshot.get('in_game') and state().get('ready') and state()['generation']>generation and ui().get('skills_ready') and ui().get('character')==swap_name,'Fresh Magician entered in same account',40)
  result['checks']['same_account_new_class_receives_own_skills']=ui()['info']['class_name']=='Magician' and any(e.get('kind')=='spell' for e in ui()['entries']) and not any(e.get('kind')=='spell' and e.get('line') in ['Regrowth','Nurture'] for e in ui()['entries'])
  result['checks']['new_character_has_fresh_shortcut_pages']=ui()['banks']==[0,0,0]
  result['checks']['new_character_does_not_inherit_heal_bar']=all(not slot for bar in ui()['bars'] for bank in bar for slot in bank)
  if inventory_probe:
   wait(lambda:a.snapshot['inventory']['ready'],'Fresh empty inventory received')
   inv=a.snapshot['inventory']
   result['new_character_inventory']={k:inv[k] for k in ['ready','items','money','pending']}
   with checked() as db:
    balance=db.execute('SELECT * FROM AccountXMoney WHERE AccountId=? AND Realm=3',(leader['AccountName'],)).fetchone();assert balance
    expected_money={key.lower():int(balance[key]) for key in ['Copper','Silver','Gold','Platinum','Mithril']}
   result['checks']['new_character_has_own_empty_inventory']=not inv['items'] and inv['money']==expected_money and not inv['pending']
   result['checks']['new_character_has_no_previous_target_or_trainer']=not a.snapshot['interaction']['target'] and not ui()['trainer']['ready'] and not ui()['trainer']['specs']
   a.send('inventory_unequip',slot=11,item_token=old_shield['token'],inventory_revision=old_inventory['state_revision']);settle(.4)
   result['checks']['previous_character_item_request_refused']=bool(a.snapshot['inventory']['feedback']) and not a.snapshot['inventory']['pending'] and not a.snapshot['inventory']['items']
  a.send('ui_use',entry_id=fresh['id'],entry_token=fresh['token']);settle(.3)
  result['checks']['previous_class_skill_token_refused']='changed' in ui().get('feedback','').lower()
  mage_spell=next(e for e in ui()['entries'] if e.get('kind')=='spell')
  a.send('ui_assign',bar=2,bank=0,slot=9,entry_id=mage_spell['id'],entry_token=mage_spell['token'])
  wait(lambda:ui()['bars'][2][0][9].get('token')==mage_spell['token'],'New class stores its own shortcut')
  a.send('chat',text='/quit');wait(lambda:not a.snapshot.get('in_game') and a.snapshot.get('character_lobby',{}).get('ready'),'Return after separate class shortcut save',100)
  lobby=a.snapshot['character_lobby'];generation=state()['generation'];a.send('character_enter',name='Codexdruid',lobby_revision=lobby['revision'])
  wait(lambda:a.snapshot.get('in_game') and state().get('ready') and state()['generation']>generation and ui().get('skills_ready') and ui().get('character')=='Codexdruid','Original trained character returns after class switch',40)
  result['checks']['original_character_progression_survives_class_switch']=ui()['info']['level']==2 and ui()['points']['xp']==64 and any(e['name']=='Regrowth' and e['level']==2 for e in ui()['specs'])
  slot=ui()['bars'][2][4][9]
  result['checks']['original_character_restores_distinct_saved_page']=ui()['banks'][2]==4 and slot.get('name')==original_heal['name'] and any(e['id']==slot.get('id') and e['token']==slot.get('token') for e in ui()['entries'])
  result['checks']['new_class_shortcut_does_not_replace_original_heal']=ui()['bars'][2][0][9].get('name')==original_heal['name'] and mage_spell['name'] not in [e['name'] for e in ui()['entries'] if e.get('kind')=='spell']
  if inventory_probe:
   wait(lambda:a.snapshot['inventory']['ready'] and any(e['slot']==11 for e in a.snapshot['inventory']['items']),'Original equipment restored')
   inv=a.snapshot['inventory'];identity=lambda rows:sorted((e['slot'],e['name'],e['model'],e['count']) for e in rows)
   result['checks']['original_equipment_and_coins_restored']=identity(inv['items'])==identity(old_inventory['items']) and inv['money']==old_inventory['money']
   shield=next(e for e in inv['items'] if e['slot']==11)
   a.send('inventory_unequip',slot=11,item_token=shield['token'],inventory_revision=inv['state_revision'])
   wait(lambda:not a.snapshot['inventory']['pending'] and not any(e['slot']==11 for e in a.snapshot['inventory']['items']) and any(e['slot']>=40 and e['name']==shield['name'] for e in a.snapshot['inventory']['items']),'Server confirms unequip after character return')
   inv=a.snapshot['inventory'];backpack=next(e for e in inv['items'] if e['slot']>=40 and e['name']==shield['name'])
   a.send('inventory_equip',slot=backpack['slot'],item_token=backpack['token'],inventory_revision=inv['state_revision'])
   wait(lambda:not a.snapshot['inventory']['pending'] and any(e['slot']==11 and e['name']==shield['name'] for e in a.snapshot['inventory']['items']),'Server confirms reequipment after character return')
   result['checks']['equipment_operations_work_after_return']=identity(a.snapshot['inventory']['items'])==identity(old_inventory['items'])
 result['passed']=all(result['checks'].values())
except Exception:result['errors'].append(traceback.format_exc())
finally:
 for peer in peers:
  if peer.session and peer.snapshot.get('in_game'):
   try:
    me=next(e for e in peer.snapshot.get('entities',[]) if e['id']=='player:local')
    peer.send('move',position_m=me['position_m'],forward_xz=me.get('forward_xz',[0,1]),speed_mps=0,target_entity_id='',target_in_view=False)
   except (OSError,StopIteration):pass
 if peers:
  try:settle(.4)
  except OSError:pass
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
 if relay is not None:
  result['native_sight_answers']=relay.answers
  native=relay.read_report();result['native_scene_at_cleanup']={k:native.get(k) for k in ['map','navigation_ready','navigation_probe','character_grounded','position_m','terrain_colliders']}
  try:result['native_normal_exit']=relay.finish()==0
  except Exception:result['errors'].append('Native cleanup: '+traceback.format_exc())
 for handle in handles:handle.close()
 for target,saved in reversed(candidate_files):assert target.resolve().is_relative_to(RUN);shutil.copy2(saved,target)
 for config,raw in config_backups:config.write_bytes(raw)
 if backed and result['passed']:
  with checked() as db:
   saved=db.execute("SELECT Level,Experience FROM DOLCharacters WHERE Name='Codexdruid'").fetchone()
   result['checks']['normal_logout_saves_level_and_experience']=saved['Level']==result['final_level'] and saved['Experience']==result['final_points']['xp']
   result['passed']=result['passed'] and result['checks']['normal_logout_saves_level_and_experience']
   if training_case!='off':
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
 (D/'verified.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k not in ['source_inputs','catalogue_before','catalogue_after']}));assert result['passed']
