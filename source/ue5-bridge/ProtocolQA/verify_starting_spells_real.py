"""Compare received starting spells and server-derived UI lists in the marked disposable database only."""
import argparse
from qa_runtime import *
import sqlite3,subprocess,socket,time,hashlib,shutil,traceback

parser=argparse.ArgumentParser();parser.add_argument('--class-id',type=int,choices=[51,52,53,54,57,47,39,58,62],required=True)
parser.add_argument('--bainshee-proposal',type=Path);parser.add_argument('--level',type=int,choices=[1,5,50])
parser.add_argument('--expansion-proposal',type=Path)
parser.add_argument('--bainshee-form-cycle',action='store_true')
parser.add_argument('--bainshee-race',type=int,choices=[9,11,12],default=9)
parser.add_argument('--bainshee-promotion',action='store_true')
parser.add_argument('--server-source',type=Path)
parser.add_argument('--bainshee-effect',choices=['ward','barrier'])
parser.add_argument('--bainshee-training',action='store_true')
parser.add_argument('--expansion-training',action='store_true')
parser.add_argument('--bainshee-combat',action='store_true')
args=parser.parse_args();class_id=args.class_id
training_mode=args.bainshee_training or args.expansion_training
training_lines={39:['Spectral Guard','Phantasmal Wail','Ethereal Shriek'],58:['Dementia','Shadow Mastery','Vampiiric Embrace'],62:['Aura Manipulation','Magnetism','Power Strikes']}
trainer_types={39:'BainsheeTrainer',58:'VampiirTrainer',62:'HiberniaMaulerTrainer'}
training_level=5 if class_id==62 else 4
assert not(args.bainshee_proposal and args.expansion_proposal)
proposal_path=args.bainshee_proposal or args.expansion_proposal
assert (class_id in [39,58,62])==bool(proposal_path),'Expansion classes require an explicit isolated data proposal'
assert not args.bainshee_proposal or class_id==39
assert not args.expansion_proposal or class_id in [58,62]
assert args.level is None or class_id in [39,58,62],'Advanced-level data probes are limited to scoped expansion fixtures'
level=args.level or (3 if class_id==52 else 1)
assert not args.bainshee_form_cycle or (class_id==39 and level==5),'Form cycle requires the scoped level-five Bainshee probe'
assert not args.bainshee_promotion or (class_id==39 and level==5 and args.server_source),'Promotion requires the explicit level-five candidate server'
assert args.server_source is None or args.bainshee_promotion
assert not args.bainshee_effect or (class_id==39 and level==50 and not args.bainshee_promotion and not args.bainshee_form_cycle)
assert args.bainshee_race==9 or args.bainshee_form_cycle or args.bainshee_promotion
assert not args.bainshee_training or (class_id==39 and level==50 and not args.bainshee_promotion and not args.bainshee_effect and not args.bainshee_form_cycle)
assert not args.expansion_training or (class_id in [58,62] and level==50 and not args.bainshee_training and not args.bainshee_combat)
assert not args.bainshee_combat or (class_id==39 and level==50 and not args.bainshee_promotion and not args.bainshee_effect and not args.bainshee_form_cycle and not args.bainshee_training)
D=ROOT/'Reports/starting_spells'/('class_'+str(class_id)+(('_level_'+str(level)) if class_id in [39,58,62] else '')+('_promotion' if args.bainshee_promotion else '')+('_form_cycle' if args.bainshee_form_cycle else '')+('_race_'+str(args.bainshee_race) if args.bainshee_race!=9 else '')+('_effect_'+args.bainshee_effect if args.bainshee_effect else '')+('_training' if training_mode else '')+('_combat' if args.bainshee_combat else ''));D.mkdir(parents=True,exist_ok=True)
SOURCE=Path(os.environ.get('DAOC_BRIDGE_QA_GODOT',str(ROOT/'Godot')))
result={'passed':False,'real_protocol':True,'disposable_only':True,'checks':{},'errors':[]}
server=client=sock=None;logs=[];session='';snapshot={};buffer=b'';serial=0;backed=False
backup=ROOT/'Backups'/('StartingSkillsQA_'+time.strftime('%Y%m%d-%H%M%S'));backup.mkdir()
config=RUN/'bridge_config.json';config_bytes=config.read_bytes()
native_catalog=RUN/'models.json'
native_catalog_before=native_catalog.read_bytes() if args.bainshee_form_cycle and native_catalog.exists() else None
candidate_files=[]
effect_trace=[]
relay=None
combat_motion_speed=0
combat_move_at=0
combat_finished=False
def checked():
 db=sqlite3.connect(DB);db.row_factory=sqlite3.Row;assert db.execute('SELECT RunId FROM CodexQaIsolationMarker').fetchone()[0]==RUN.name;return db
def update(db,table,keyfield,key,values):db.execute('UPDATE '+table+' SET '+','.join('"'+k+'"=?' for k in values)+' WHERE "'+keyfield+'"=?',list(values.values())+[key])

def install_probe_data(db):
 import importlib.util
 spec=importlib.util.spec_from_file_location('bainshee_probe_data',Path(__file__).with_name('bainshee_probe_data.py'))
 helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
 result['isolated_bainshee_data' if class_id==39 else 'isolated_expansion_data']=helper.install(db,proposal_path,RUN.name,class_id)

def send(action,**values):
 global serial
 serial+=1;sock.sendall((json.dumps(dict(type='command',session=session,id='cloak:'+str(serial),action=action,**values))+'\n').encode())
def pump():
 global session,snapshot,buffer,combat_move_at
 # The headless observer suppresses native movement commands. Supply the
 # stationary/input heartbeat normally sent by the pawn, using its real probe.
 if args.bainshee_combat and not combat_finished and relay is not None and relay.probe_result is True and time.monotonic()-combat_move_at>.1:
  player=next((e for e in snapshot.get('entities',[]) if e['id']=='player:local'),None)
  if player:
   combat_move_at=time.monotonic();send('move',position_m=player['position_m'],forward_xz=[0,1],speed_mps=combat_motion_speed,target_in_view=True,target_entity_id=enemy_id)
 try:data=sock.recv(1048576)
 except socket.timeout:return
 if not data:raise RuntimeError('Private spell bridge closed')
 buffer+=data
 while b'\n' in buffer:
  line,buffer=buffer.split(b'\n',1);v=json.loads(line)
  if v.get('type')=='hello':session=v['session']
  if v.get('type')=='snapshot':
   snapshot=v
   if args.bainshee_effect:
    for event in v.get('spell_visuals',[]):
     if event.get('effect_id') in [13515,13516,3332,3334] and not any(old.get('seq')==event.get('seq') for old in effect_trace):effect_trace.append(event)
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
  if class_id in [39,58,62]:install_probe_data(db)
  update(db,'Account','Name',char['AccountName'],{'PrivLevel':1 if training_mode or args.bainshee_combat else 3,'Realm':3})
  values={'Class':class_id,'Level':level,'Experience':0,'SerializedSpecs':''}
  if class_id==39:
   creation_model={9:310,11:342,12:326}[args.bainshee_race]
   values.update(Gender=1,Race=args.bainshee_race,CreationModel=creation_model,CurrentModel=creation_model)
  if args.bainshee_promotion:
   values.update(Class=51,Health=200,DeathTime=0,HasGravestone=0,DisabledSpells='',DisabledAbilities='')
   disabled=db.execute("SELECT Value FROM ServerProperty WHERE Key='disabled_classes'").fetchone()[0]
   # Only the disposable candidate enables this promotion; preserve every other class restriction.
   import importlib.util
   pipeline=args.server_source.resolve().parent/'new-client/pipeline/build_server_classes.py';assert pipeline.exists()
   spec=importlib.util.spec_from_file_location('candidate_class_rules',pipeline)
   rules=importlib.util.module_from_spec(spec);spec.loader.exec_module(rules)
   disabled_ids=rules.id_set(disabled);disabled_ids.discard(39)
   db.execute("UPDATE ServerProperty SET Value=? WHERE Key='disabled_classes'",(';'.join(map(str,sorted(disabled_ids))),))
   npc=db.execute("SELECT Mob_ID FROM Mob WHERE Name IN ('Codex Magic Target','Codex Pet Training Dummy')").fetchone();assert npc
   update(db,'Mob','Mob_ID',npc['Mob_ID'],{'Name':'Codex Bainshee Trainer','ClassType':'DOL.GS.Trainer.BainsheeTrainer','Guild':'Bainshee Trainer','Model':342,'Level':50,'Realm':3,'Flags':0,'AggroLevel':0,'Speed':0,'X':char['Xpos']+80,'Y':char['Ypos']+40,'Z':char['Zpos']})
   result['promotion_gift_template_present']=bool(db.execute("SELECT 1 FROM ItemTemplate WHERE Id_nb='bainshee_item'").fetchone())
  if training_mode:
   values.update(Health=200,DeathTime=0,HasGravestone=0,DisabledSpells='',DisabledAbilities='')
   npc=db.execute("SELECT Mob_ID FROM Mob WHERE Name IN ('Codex Magic Target','Codex Pet Training Dummy')").fetchone();assert npc
   update(db,'Mob','Mob_ID',npc['Mob_ID'],{'Name':'Codex Expansion Trainer','ClassType':'DOL.GS.Trainer.'+trainer_types[class_id],'Guild':'Trainer','Model':342,'Level':50,'Realm':3,'Flags':0,'AggroLevel':0,'Speed':0,'X':char['Xpos']+80,'Y':char['Ypos']+40,'Z':char['Zpos']})
  if args.bainshee_combat:
   values.update(Health=200,DeathTime=0,HasGravestone=0,DisabledSpells='',DisabledAbilities='')
   npc=db.execute("SELECT Mob_ID FROM Mob WHERE Name IN ('Codex Magic Target','Codex Pet Training Dummy')").fetchone();assert npc
   update(db,'Mob','Mob_ID',npc['Mob_ID'],{'Name':'Codex Bainshee Target','ClassType':'DOL.GS.GameNPC','Guild':'','Model':118,'Level':50,'Realm':0,'Flags':0,'AggroLevel':0,'Speed':0,'X':char['Xpos'],'Y':char['Ypos']+400,'Z':char['Zpos']})
  update(db,'DOLCharacters','DOLCharacters_ID',char['DOLCharacters_ID'],values)
 cfg=json.loads(config_bytes);cfg['custom_class']=False;cfg['initial_spawn_m']=[(char['Xpos']-35*8192)*.025,char['Zpos']*.025,(char['Ypos']-51*8192)*.025];config.write_text(json.dumps(cfg),encoding='utf-8')
 if args.bainshee_promotion:
  build=args.server_source.resolve()/'Release';assert (build/'GameServer.dll').exists()
  for name in ['GameServer.dll','CoreBase.dll','CoreDatabase.dll']:
   for folder in [SERVER,SERVER/'lib',SERVER/'win-x64']:
    dst=folder/name
    if folder!=SERVER and not dst.exists():continue
    assert dst.resolve().is_relative_to(RUN.resolve())
    saved=backup/('candidate_'+str(len(candidate_files))+'_'+name) if dst.exists() else None
    if saved:shutil.copy2(dst,saved)
    candidate_files.append((dst,saved));shutil.copy2(build/name,dst)
  result['candidate_server_sha256']=hashlib.sha256((build/'GameServer.dll').read_bytes()).hexdigest()
 if args.bainshee_form_cycle:
  assert native_catalog.resolve().is_relative_to(RUN.resolve())
  models=json.loads((ROOT/'models.json').read_text())
  assert all(models.get(str(model),{}).get('type')=='skeletal' for model in (1883,1884,1885))
  native_catalog.write_text(json.dumps(models),encoding='utf-8')
 for p in SOURCE.glob('*.gd'):shutil.copy2(p,RUN/'Godot'/p.name)
 p=RUN/'Godot/live_gateway.gd';p.write_text(p.read_text().replace('var states:Array=[]','transport.snapshot_metadata[\"qa_skill_audit\"]={\"skills\":server.skills,\"spell_lines\":server.spell_lines}\n        var states:Array=[]'))
 p=RUN/'Godot/visual_bridge.gd';p.write_text(p.read_text(encoding='utf-8-sig').replace('port: int = 19727','port: int = 19737').replace('["character",','["qa_skill_audit","character",'),encoding='utf-8')
 log=(D/'starting_spells_server.log').open('w',encoding='utf-8');logs.append(log)
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
 log=(D/'starting_spells_client.log').open('w',encoding='utf-8');logs.append(log)
 client=subprocess.Popen([str(game/'tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'),'--headless','--path',str(RUN/'LobbyProject'),'--script',str(RUN/'Godot/gateway_main.gd'),'--','--server=127.0.0.1','--server-port=10351','--account='+account,'--password='+password,'--no-world','--bridge-character=Codexdruid'],cwd=RUN,env=ce,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 end=time.monotonic()+50
 while time.monotonic()<end:
  try:sock=socket.create_connection(('127.0.0.1',19737),timeout=.3);sock.settimeout(.1);break
  except OSError:time.sleep(.2)
 else:raise RuntimeError('Private spell bridge unavailable')
 wait(lambda:snapshot.get('classic_ui',{}).get('skills_ready'),'Starting spell lists');settle(5)
 if args.bainshee_promotion:
  player=next(e for e in snapshot.get('entities',[]) if e.get('id')=='player:local')
  send('move',position_m=player['position_m'],forward_xz=player['forward_xz'],speed_mps=0);settle(2)
  wait(lambda:any(e.get('name')=='Codex Bainshee Trainer' for e in snapshot.get('entities',[])),'Original candidate trainer visible',20)
  npc=next(e for e in snapshot['entities'] if e.get('name')=='Codex Bainshee Trainer')
  send('interact',entity_id=npc['id'])
  wait(lambda:'Bainshee' in snapshot.get('interaction',{}).get('talk',{}).get('keywords',[]),'Original trainer offers promotion keyword',20)
  talk=snapshot['interaction']['talk'];send('keyword',reply_id=talk['id'],word='Bainshee')
  wait(lambda:any(e.get('name')=="Bawler's Bruise" for e in snapshot.get('classic_ui',{}).get('entries',[])),'Original trainer promotion updates Bainshee spell list',20)
  with checked() as db:assert db.execute("SELECT Class FROM DOLCharacters WHERE Name='Codexdruid'").fetchone()[0]==39
  result['checks']['original_trainer_promotes_magician']=True;settle(1)
 if class_id in [39,58,62]:
  candidate=json.loads(proposal_path.read_text())
  startup=(D/'starting_spells_server.log').read_text(encoding='utf-8-sig',errors='replace')
  registered={kind:any('Found spell handler DOL.GS.Spells.'+row['class'] in startup for row in rows) for kind,rows in candidate['concrete_handler_source_coverage'].items()}
  assert all(registered.values()),registered
  result['runtime_registered_handler_types']=registered
 (D/'druid_level1_snapshot.json').write_text(json.dumps(snapshot),encoding='utf-8')
 result['checks']['starting_list']=True
 result['entries']=[{'name':e.get('name'),'group':e.get('group'),'id':e.get('id')} for e in snapshot.get('classic_ui',{}).get('entries',[]) if e.get('kind')=='spell']
 audit=snapshot['qa_skill_audit'];expected={str(x['name']) for x in audit['skills'] if int(x['page']) in [3,4]}
 for line in audit['spell_lines']:expected.update(str(x['name']) for x in line['spells'])
 actual={str(x['name']) for x in snapshot['classic_ui']['entries'] if x.get('kind')=='spell'}
 result['class_id']=class_id;result['level']=level;result['expected_spells']=sorted(expected);result['visible_spells']=sorted(actual);result['complete']=expected==actual
 if class_id in [39,58,62]:assert expected,'Candidate expansion class must receive actual spells, not merely an empty matching list'
 assert result['complete'],(expected,actual)
 if args.bainshee_promotion:
  assert len(expected)==7 and 'Gleam Ray' not in expected,'Promotion must replace the base-class list, not append stale entries'
  result['checks']['promotion_replaces_base_spell_list']=True
 if training_mode:
  player=next(e for e in snapshot['entities'] if e['id']=='player:local')
  send('move',position_m=player['position_m'],forward_xz=player['forward_xz'],speed_mps=0)
  wait(lambda:any(e.get('name')=='Codex Expansion Trainer' for e in snapshot.get('entities',[])),'Original trainer visible')
  npc=next(e for e in snapshot['entities'] if e.get('name')=='Codex Expansion Trainer');send('interact',entity_id=npc['id']);send('trainer_refresh')
  trainer=lambda:snapshot.get('classic_ui',{}).get('trainer',{})
  wait(lambda:trainer().get('ready') and not trainer().get('pending'),'Original trainer list ready')
  points_before=trainer()['spec_points'];trained=[]
  for line in training_lines[class_id]:
   for target_level in range(2,training_level+1):
    row=next(e for e in trainer()['specs'] if e['name']==line);assert row['level']==target_level-1 and row['can_train']
    points=trainer()['spec_points'];cost=row['cost'];assert cost==target_level
    send('trainer_train',training_kind='spec',training_index=row['index'],training_token=row['token'])
    wait(lambda:any(e['name']==line and e['level']==target_level for e in trainer().get('specs',[])) and not trainer().get('pending'),'Server confirms trained '+line+' level '+str(target_level))
    wait(lambda:trainer()['spec_points']==points-cost,'Original specialization point cost')
   trained.append({'line':line,'level':training_level})
  proposed_names={int(e['SpellID']):str(e['Name']) for e in candidate['spells']}
  unlocked={proposed_names[int(e['SpellID'])] for e in candidate['line_spells'] if e['LineName'] in training_lines[class_id] and 1<int(e['Level'])<=training_level}-expected
  top_rank={proposed_names[int(e['SpellID'])] for e in candidate['line_spells'] if e['LineName'] in training_lines[class_id] and int(e['Level'])==training_level}
  wait(lambda:top_rank<={e.get('name') for e in snapshot['classic_ui']['entries'] if e.get('kind')=='spell'},'New highest-rank spells reach actual usable list')
  trained_audit=snapshot['qa_skill_audit'];received_trained={str(e['name']) for e in trained_audit['skills'] if int(e['page']) in [3,4]}
  for line in trained_audit['spell_lines']:received_trained.update(str(e['name']) for e in line['spells'])
  actual_trained={str(e['name']) for e in snapshot['classic_ui']['entries'] if e.get('kind')=='spell'}
  assert received_trained==actual_trained,'Trained received/UI spell lists differ'
  learned=actual_trained-expected
  assert learned and learned<=unlocked,'Training must unlock original source spells'
  assert trainer()['spec_points']==points_before-len(training_lines[class_id])*sum(range(2,training_level+1))
  result['training']={'normal_player_privileges':True,'lines':trained,'points_before':points_before,'points_after':trainer()['spec_points'],'learned_spells':sorted(learned)}
  result['checks']['original_training_points_and_spells']=True
 if args.bainshee_combat:
  import importlib.util
  spec=importlib.util.spec_from_file_location('bainshee_native_observer',Path(__file__).resolve().parents[1]/'pet_sight_relay.py');observer=importlib.util.module_from_spec(spec);spec.loader.exec_module(observer)
  player=next(e for e in snapshot['entities'] if e['id']=='player:local')
  send('move',position_m=player['position_m'],forward_xz=[0,1],speed_mps=0)
  wait(lambda:any(e.get('name')=='Codex Bainshee Target' for e in snapshot.get('entities',[])),'Real combat target visible')
  enemy=next(e for e in snapshot['entities'] if e.get('name')=='Codex Bainshee Target');enemy_id=enemy['id']
  relay=observer.NativeSightRelay(sock,ROOT,session,snapshot,output=D,duration=95,entity_ids=['player:local',enemy_id],render=False);sock=relay
  wait(lambda:bool(relay.read_report().get('local_animation')),'Native observer loads original character',80)
  send('target',entity_id=enemy_id);settle(.5)
  def stationary():
   player=next(e for e in snapshot['entities'] if e['id']=='player:local')
   send('move',position_m=player['position_m'],forward_xz=[0,1],speed_mps=0,target_in_view=True,target_entity_id=enemy_id)
  stationary();relay.start_probe(enemy_id);wait(lambda:relay.probe_result is not None,'Native geometry answers target probe');assert relay.probe_result
  def use_spell():
   entry=next(e for e in snapshot['classic_ui']['entries'] if e.get('kind')=='spell' and e.get('name')=='Wailing Pain')
   send('ui_use',entry_id=entry['id'],entry_token=entry['token'])
  cast=lambda:snapshot.get('classic_ui',{}).get('casting',{})
  vitals=lambda:snapshot.get('player_status',{}).get('vitals',{})
  before=cast().get('seq',0);use_spell()
  wait(lambda:cast().get('seq',0)>before and cast().get('phase')=='casting','Actual hostile Bainshee cast starts')
  player=next(e for e in snapshot['entities'] if e['id']=='player:local');position=list(player['position_m']);position[0]+=.1
  combat_motion_speed=1
  send('move',position_m=position,forward_xz=[0,1],speed_mps=1,target_in_view=True,target_entity_id=enemy_id)
  wait(lambda:cast().get('phase')=='interrupted','Actual movement interrupts Bainshee cast');result['checks']['normal_movement_interrupts']=True
  combat_motion_speed=0
  stationary();settle(1);attempts=[]
  for attempt in range(6):
   health_before=next(e for e in snapshot['entities'] if e['id']==enemy_id).get('health',1);mana_before=vitals()['mana'];before=cast().get('seq',0);use_spell()
   wait(lambda:cast().get('seq',0)>before and cast().get('phase')=='casting','Stationary hostile spell starts')
   wait(lambda:cast().get('phase')=='released','Server resolves Bainshee damage spell')
   resisted=bool(cast().get('resisted'));attempts.append({'resisted':resisted,'mana_before':mana_before,'mana_after':vitals()['mana']})
   if not resisted:break
   assert next(e for e in snapshot['entities'] if e['id']==enemy_id).get('health',1)==health_before
   settle(1.5)
  assert not resisted,'All bounded attempts were resisted; no damage result was manufactured'
  wait(lambda:any(e['id']==enemy_id and e.get('health',1)<health_before for e in snapshot['entities']),'Actual target health decreases')
  wait(lambda:vitals()['mana']<mana_before,'Original spell consumes mana')
  enemy=next(e for e in snapshot['entities'] if e['id']==enemy_id)
  result['combat']={'normal_player_privileges':True,'native_geometry_without_rendering':True,'spell':'Wailing Pain','attempts':attempts,'health_before':health_before,'health_after':enemy['health'],'mana_before':mana_before,'mana_after':vitals()['mana'],'native_los_answers':relay.answers,'native_probes':relay.probes}
  assert relay.answers and all(row['visible'] for row in relay.answers)
  result['checks']['normal_player_hostile_damage_and_mana']=True;result['checks']['native_geometry_answers_server_los']=True
  # Combat verification is complete. Keep the actual backend socket while
  # the normal player waits out the server's sixty-second seated logout.
  combat_finished=True;sock=relay.backend;sock.settimeout(.1)
 if args.bainshee_effect:
  candidate=json.loads(args.bainshee_proposal.read_text())
  assert len(candidate.get('client_effect_adaptations',[]))==2 and not candidate['missing_effect_definitions'] and not candidate['missing_fx_resources']
  wait(lambda:snapshot.get('player_status',{}).get('ready'),'Effect probe vitals ready')
  player=next(e for e in snapshot['entities'] if e.get('id')=='player:local')
  send('move',position_m=player['position_m'],forward_xz=player['forward_xz'],speed_mps=0);send('target_self');settle(2)
  name,effect_id=('Ward of Power',13515) if args.bainshee_effect=='ward' else ('Barrier of Power',13516)
  entry=next(e for e in snapshot['classic_ui']['entries'] if e.get('kind')=='spell' and e.get('name')==name)
  send('ui_use',entry_id=entry['id'],entry_token=entry['token'])
  wait(lambda:any(e.get('kind')=='release' and e.get('effect_id')==effect_id and not e.get('resisted') for e in effect_trace),'Real self buff releases the matching original client effect',20)
  assert not any(e.get('effect_id') in [3332,3334] for e in effect_trace)
  assert not next(e for e in snapshot['entities'] if e.get('id')=='player:local').get('morphed')
  result['checks']['original_absorption_effect_released']=True
  result['effect_probe']={'spell':name,'effect_id':effect_id,'events':effect_trace,'native_visual_acceptance':'separate probe'}
 if args.bainshee_form_cycle:
  def local_player():return next((e for e in snapshot.get('entities',[]) if e.get('id')=='player:local'),{})
  wait(lambda:snapshot.get('player_status',{}).get('ready') and bool(local_player()),'Bainshee world and vitals ready')
  original=dict(local_player());assert not original.get('morphed')
  worn=[(x['slot'],x.get('model')) for x in inv().get('items',[])]
  send('move',position_m=original['position_m'],forward_xz=original['forward_xz'],speed_mps=0);settle(2)
  if snapshot['player_status']['vitals'].get('sitting'):
   send('player_sit',on=False,player_generation=snapshot['player_status']['generation']);wait(lambda:not snapshot['player_status']['vitals'].get('sitting'),'Stand before casting')
  def use(name):
   entry=next(e for e in snapshot['classic_ui']['entries'] if e.get('kind')=='spell' and e.get('name')==name)
   send('ui_use',entry_id=entry['id'],entry_token=entry['token'])
  def server_said(text):return any(text in e.get('text','') for e in snapshot.get('chat',{}).get('entries',[]))
  use('Lesser Powerward')
  wait(lambda:server_said('You cast a Lesser Powerward spell!'),'Original positive self buff completes',20)
  assert not local_player().get('morphed');result['checks']['positive_buff_retains_original_form']=True
  # Original cone spells require no selected enemy; no synthetic LOS reply or damage result.
  settle(1);use("Bawler's Bruise")
  form_model={9:1883,11:1885,12:1884}[args.bainshee_race]
  wait(lambda:local_player().get('morphed') and local_player().get('model_id')==form_model,'Original offensive CastFinished transforms Bainshee',20)
  changed_at=time.monotonic()
  assert local_player().get('look',{})==original.get('look',{})
  result['checks']['original_offensive_cast_transforms']=True
  result['form_spell']="Bawler's Bruise";result['form_model']=form_model;result['race']=args.bainshee_race
  wait(lambda:not local_player().get('morphed') and local_player().get('model_id')==original['model_id'],'Original thirty-second Bainshee timer restores chosen figure',40)
  elapsed=time.monotonic()-changed_at;assert 25<=elapsed<=40,elapsed
  result['form_timer_seconds']=round(elapsed,2)
  assert local_player().get('look',{})==original.get('look',{})
  assert [(x['slot'],x.get('model')) for x in inv().get('items',[])]==worn
  result['checks']['original_timer_restores_appearance_and_inventory']=True
  result['combat_damage_tested']=False
 send('chat',text='/quit')
 wait(lambda:not snapshot.get('in_game') and snapshot.get('character_lobby',{}).get('ready'),'Return to current creation rules',100 if args.bainshee_combat or training_mode else 45)
 lobby=snapshot['character_lobby'];assert all(int(c['class_id'])!=63 for c in lobby['choices'])
 result['custom_disabled_choice_hidden']=True
 row=next(c for c in lobby['characters'] if c['name']=='Codexdruid')
 result['base_class_caption']=row['class_name'];assert class_id!=51 or row['class_name']=='Magician'
 if training_mode:
  with checked() as db:
   saved=db.execute("SELECT SerializedSpecs FROM DOLCharacters WHERE Name='Codexdruid'").fetchone()[0]
   assert all(line in saved for line in training_lines[class_id])
  send('character_enter',name='Codexdruid',lobby_revision=lobby['revision'])
  wait(lambda:snapshot.get('classic_ui',{}).get('skills_ready') and learned<={e.get('name') for e in snapshot.get('classic_ui',{}).get('entries',[]) if e.get('kind')=='spell'},'Trained spells survive saved reentry',40)
  result['checks']['trained_spells_survive_saved_reentry']=True
 result['passed']=True

except Exception:
 if relay is not None:result['native_observer_diagnostics']={'answers':relay.answers,'probes':relay.probes,'questions':relay.questions}
 result['errors'].append(traceback.format_exc());(D/'starting_spells_failed.json').write_text(json.dumps(snapshot),encoding='utf-8')
finally:
 if sock and session:
  try:send('logout')
  except OSError:pass
 if client and client.poll() is None:
  (RUN/'Reports/live/logout.request').write_text('logout',encoding='utf-8')
  try:client.wait(timeout=90)
  except subprocess.TimeoutExpired:client.kill();client.wait();result['errors'].append('Private starting-spell client forced stop')
 if sock:sock.close()
 if server and server.poll() is None:
  server.stdin.write('exit\n');server.stdin.flush()
  try:server.wait(timeout=45)
  except subprocess.TimeoutExpired:server.kill();server.wait();result['errors'].append('Private server forced stop')
 if relay is not None:
  try:result['native_observer_exit']=relay.finish()
  except Exception:result['errors'].append(traceback.format_exc())
 for log in logs:log.close()
 for dst,saved in reversed(candidate_files):
  assert dst.resolve().is_relative_to(RUN.resolve())
  if saved:shutil.copy2(saved,dst)
  elif dst.exists():dst.unlink()
 if candidate_files:result['candidate_server_restored']=True
 if args.bainshee_form_cycle:
  assert native_catalog.resolve().is_relative_to(RUN.resolve())
  if native_catalog_before is None:native_catalog.unlink(missing_ok=True)
  else:native_catalog.write_bytes(native_catalog_before)
  result['qa_native_catalogue_restored']=True
 if backed:
  assert DB.is_relative_to(RUN) and RUN.is_relative_to(ROOT/'ProtocolQA')
  with checked() as dst:
   src=sqlite3.connect(backup/'before.sqlite3.db');src.backup(dst);src.close()
  config.write_bytes(config_bytes);result['database_restored']=True
 result['normal_shutdown']=bool(client and server and client.returncode==0 and server.returncode==0)
 result['passed']=result['passed'] and result['normal_shutdown'] and not result['errors']
 (D/'real_protocol.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result));assert result['passed']
