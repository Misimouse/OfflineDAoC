"""Compare received starting spells and server-derived UI lists in the marked disposable database only."""
import argparse
from qa_runtime import *
import sqlite3,subprocess,socket,time,hashlib,shutil,traceback

parser=argparse.ArgumentParser();parser.add_argument('--class-id',type=int,choices=[51,52,53,54,57,47,39,58,62],required=True)
parser.add_argument('--bainshee-proposal',type=Path);parser.add_argument('--level',type=int,choices=[1,5,6,50])
parser.add_argument('--expansion-proposal',type=Path)
parser.add_argument('--career-proposal',type=Path)
parser.add_argument('--expansion-power',action='store_true')
parser.add_argument('--vampiir-bolt',action='store_true')
parser.add_argument('--bainshee-form-cycle',action='store_true')
parser.add_argument('--native-form-probe',action='store_true')
parser.add_argument('--central-installed-native',action='store_true')
parser.add_argument('--bainshee-race',type=int,choices=[9,11,12],default=9)
parser.add_argument('--bainshee-promotion',action='store_true')
parser.add_argument('--vampiir-promotion',action='store_true')
parser.add_argument('--vampiir-race',type=int,choices=[9,12,18],default=9)
parser.add_argument('--vampiir-female',action='store_true')
parser.add_argument('--candidate-build',type=Path)
parser.add_argument('--combined-expansions',action='store_true')
parser.add_argument('--combined-data',type=Path)
parser.add_argument('--server-source',type=Path)
parser.add_argument('--bainshee-effect',choices=['ward','barrier'])
parser.add_argument('--bainshee-training',action='store_true')
parser.add_argument('--expansion-training',action='store_true')
parser.add_argument('--expansion-self-buff',action='store_true')
parser.add_argument('--bainshee-combat',action='store_true')
parser.add_argument('--druid-promotion',action='store_true')
args=parser.parse_args();class_id=args.class_id
promotion_mode=args.bainshee_promotion or args.vampiir_promotion
training_mode=args.bainshee_training or args.expansion_training
native_combat_mode=args.bainshee_combat or args.vampiir_bolt
joint_vampiir_behavior=(class_id==58 and args.level==50 and bool(args.combined_data)
                       and bool(args.career_proposal) and (args.expansion_power or args.vampiir_bolt
                       or (args.expansion_training and args.expansion_self_buff)))
joint_bainshee_behavior=(class_id==39 and args.level==50 and bool(args.combined_data)
                        and (args.bainshee_training or args.bainshee_combat or bool(args.bainshee_effect)))
training_lines={39:['Spectral Guard','Phantasmal Wail','Ethereal Shriek'],58:['Dementia','Shadow Mastery','Vampiiric Embrace'],62:['Aura Manipulation','Magnetism','Power Strikes']}
trainer_types={39:'BainsheeTrainer',58:'VampiirTrainer',62:'HiberniaMaulerTrainer'}
training_level=5 if class_id==62 else 4
assert not args.vampiir_bolt or (class_id==58 and args.level==50 and args.career_proposal and not args.expansion_power and not training_mode),'Bolt requires a separate level-fifty Vampiir career fixture'
assert not args.expansion_power or (args.career_proposal and not training_mode and not args.expansion_self_buff),'Power fixture requires career data and a separate run'
assert not args.career_proposal or class_id in [58,62]
assert not(args.bainshee_proposal and args.expansion_proposal)
proposal_path=args.bainshee_proposal or args.expansion_proposal
assert (class_id in [39,58,62])==bool(proposal_path),'Expansion classes require an explicit isolated data proposal'
assert not args.bainshee_proposal or class_id==39
assert not args.expansion_proposal or class_id in [58,62]
assert args.level is None or class_id in [39,58,62] or args.druid_promotion,'Advanced-level data probes require a scoped fixture'
assert not args.druid_promotion or (class_id==47 and args.level==5 and not proposal_path and not training_mode and not native_combat_mode),'Druid promotion uses the original level-five Naturalist and trainer'
level=args.level or (3 if class_id==52 else 1)
assert level!=6 or class_id==58, 'The level-six boundary fixture is specific to original Vampiir career abilities'
assert not args.combined_data or args.combined_expansions
assert not args.native_form_probe or (args.bainshee_form_cycle and args.combined_expansions)
assert not args.central_installed_native or args.native_form_probe
assert not args.bainshee_form_cycle or (class_id==39 and level==5),'Form cycle requires the scoped level-five Bainshee probe'
assert not args.bainshee_promotion or (class_id==39 and level==5 and args.server_source),'Promotion requires the explicit level-five candidate server'
assert not args.vampiir_promotion or (class_id==58 and level==5 and args.server_source and args.candidate_build and args.career_proposal and not training_mode and not native_combat_mode and not args.expansion_power),'Vampiir promotion requires the sealed level-five candidate and original career data'
assert args.server_source is None or promotion_mode or args.combined_expansions
assert not args.candidate_build or args.vampiir_promotion or (args.combined_expansions and (args.bainshee_promotion or args.bainshee_form_cycle or joint_vampiir_behavior or joint_bainshee_behavior))
assert not args.combined_expansions or ((promotion_mode or args.bainshee_form_cycle or joint_vampiir_behavior or joint_bainshee_behavior) and args.candidate_build and args.server_source)
assert not args.vampiir_female or args.vampiir_promotion
assert args.vampiir_race==9 or args.vampiir_promotion
assert not args.bainshee_effect or (class_id==39 and level==50 and not args.bainshee_promotion and not args.bainshee_form_cycle)
assert args.bainshee_race==9 or args.bainshee_form_cycle or args.bainshee_promotion
assert not args.bainshee_training or (class_id==39 and level==50 and not args.bainshee_promotion and not args.bainshee_effect and not args.bainshee_form_cycle)
assert not args.expansion_self_buff or args.expansion_training,'Self buff requires the original training fixture'
assert not args.expansion_training or (class_id in [58,62] and level==50 and not args.bainshee_training and not args.bainshee_combat)
assert not args.bainshee_combat or (class_id==39 and level==50 and not args.bainshee_promotion and not args.bainshee_effect and not args.bainshee_form_cycle and not args.bainshee_training)
D=ROOT/'Reports/starting_spells'/('class_'+str(class_id)+(('_level_'+str(level)) if class_id in [39,58,62] or args.druid_promotion else '')+('_promotion' if args.bainshee_promotion or args.druid_promotion else '')+('_form_cycle' if args.bainshee_form_cycle else '')+('_race_'+str(args.bainshee_race) if args.bainshee_race!=9 else '')+('_effect_'+args.bainshee_effect if args.bainshee_effect else '')+('_training' if training_mode else '')+('_combat' if args.bainshee_combat else '')+('_self_buff' if args.expansion_self_buff else '')+('_career' if args.career_proposal else '')+('_power' if args.expansion_power else '')+('_bolt' if args.vampiir_bolt else ''));D.mkdir(parents=True,exist_ok=True)
if args.vampiir_promotion:D=ROOT/'Reports/starting_spells'/('class_58_level_5_promotion_race_'+str(args.vampiir_race)+('_female' if args.vampiir_female else '_male'));D.mkdir(parents=True,exist_ok=True)
if args.combined_expansions:D=ROOT/'Reports/combined_expansions/starting_spells'/D.name;D.mkdir(parents=True,exist_ok=True)
if args.native_form_probe:D=D.parent/(D.name+'_native');D.mkdir(parents=True,exist_ok=True)
if args.combined_data:D=D.parent/(D.name+'_preloaded');D.mkdir(parents=True,exist_ok=True)
if args.central_installed_native:D=ROOT/'Reports/central_bainshee_forms'/('race_'+str(args.bainshee_race));D.mkdir(parents=True,exist_ok=True)
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
combat_visibility_override=None
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
 if native_combat_mode and not combat_finished and relay is not None and relay.probe_result is True and time.monotonic()-combat_move_at>.1:
  player=next((e for e in snapshot.get('entities',[]) if e['id']=='player:local'),None)
  if player:
   combat_move_at=time.monotonic();send('move',position_m=player['position_m'],forward_xz=[0,1],speed_mps=combat_motion_speed,target_in_view=relay.probe_result if combat_visibility_override is None else combat_visibility_override,target_entity_id=enemy_id)
 try:data=sock.recv(1048576)
 except socket.timeout:return
 if not data:raise RuntimeError('Private spell bridge closed')
 buffer+=data
 while b'\n' in buffer:
  line,buffer=buffer.split(b'\n',1);v=json.loads(line)
  if v.get('type')=='hello':session=v['session']
  if v.get('type')=='snapshot':
   snapshot=v
   if args.bainshee_effect or args.expansion_self_buff or args.vampiir_bolt:
    for event in v.get('spell_visuals',[]):
     if (args.expansion_self_buff or args.vampiir_bolt or event.get('effect_id') in [13515,13516,3332,3334]) and not any(old.get('seq')==event.get('seq') for old in effect_trace):effect_trace.append(event)
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
  if args.combined_data:
   import sys
   sys.path.insert(0,str(Path(__file__).resolve().parent))
   from prepare_combined_expansion_data import apply_marked
   result['preloaded_combined_data']=apply_marked(db,args.combined_data,RUN.name,ROOT)
  elif class_id in [39,58,62]:install_probe_data(db)
  if args.career_proposal and not args.combined_data:
   import importlib.util
   spec=importlib.util.spec_from_file_location('expansion_career_data',Path(__file__).with_name('expansion_career_data.py'));career=importlib.util.module_from_spec(spec);spec.loader.exec_module(career)
   result['isolated_career_data']=career.install(db,args.career_proposal,RUN.name,class_id)
  update(db,'Account','Name',char['AccountName'],{'PrivLevel':1 if training_mode or args.bainshee_combat or args.expansion_power or args.vampiir_bolt or args.druid_promotion else 3,'Realm':3})
  values={'Class':class_id,'Level':level,'Experience':0,'SerializedSpecs':''}
  if class_id==39:
   creation_model={9:310,11:342,12:326}[args.bainshee_race]
   values.update(Gender=1,Race=args.bainshee_race,CreationModel=creation_model,CurrentModel=creation_model)
  if args.druid_promotion:
   values.update(Class=53,Race=9,Gender=0,CreationModel=1984,CurrentModel=1984,Health=200,Mana=100,DeathTime=0,HasGravestone=0,DisabledSpells='',DisabledAbilities='')
   npc=db.execute("SELECT Mob_ID FROM Mob WHERE Name IN ('Codex Magic Target','Codex Pet Training Dummy')").fetchone();assert npc
   update(db,'Mob','Mob_ID',npc['Mob_ID'],{'Name':'Codex Druid Trainer','ClassType':'DOL.GS.Trainer.DruidTrainer','Guild':'Druid Trainer','Model':342,'Level':50,'Realm':3,'Flags':0,'AggroLevel':0,'Speed':0,'X':char['Xpos']+80,'Y':char['Ypos']+40,'Z':char['Zpos']})
   result['promotion_gift_template_present']=bool(db.execute("SELECT 1 FROM ItemTemplate WHERE Id_nb='druid_item'").fetchone())
  if promotion_mode:
   values.update(Class=54 if args.vampiir_promotion else 51,Health=200,DeathTime=0,HasGravestone=0,DisabledSpells='',DisabledAbilities='')
   if args.vampiir_promotion:
    model={9:(302,310),12:(318,326),18:(1075,1087)}[args.vampiir_race][int(args.vampiir_female)]
    values.update(Race=args.vampiir_race,Gender=int(args.vampiir_female),CreationModel=model,CurrentModel=model)
   disabled=db.execute("SELECT Value FROM ServerProperty WHERE Key='disabled_classes'").fetchone()[0]
   # Only the disposable candidate enables this promotion; preserve every other class restriction.
   import importlib.util
   pipeline=args.server_source.resolve().parent/'new-client/pipeline/build_server_classes.py';assert pipeline.exists()
   spec=importlib.util.spec_from_file_location('candidate_class_rules',pipeline)
   rules=importlib.util.module_from_spec(spec);spec.loader.exec_module(rules)
   disabled_ids=rules.id_set(disabled);disabled_ids.discard(class_id)
   db.execute("UPDATE ServerProperty SET Value=? WHERE Key='disabled_classes'",(';'.join(map(str,sorted(disabled_ids))),))
   npc=db.execute("SELECT Mob_ID FROM Mob WHERE Name IN ('Codex Magic Target','Codex Pet Training Dummy')").fetchone();assert npc
   promotion_title='Vampiir' if args.vampiir_promotion else 'Bainshee'
   update(db,'Mob','Mob_ID',npc['Mob_ID'],{'Name':'Codex '+promotion_title+' Trainer','ClassType':'DOL.GS.Trainer.'+promotion_title+'Trainer','Guild':promotion_title+' Trainer','Model':342,'Level':50,'Realm':3,'Flags':0,'AggroLevel':0,'Speed':0,'X':char['Xpos']+80,'Y':char['Ypos']+40,'Z':char['Zpos']})
   if args.bainshee_promotion:result['promotion_gift_template_present']=bool(db.execute("SELECT 1 FROM ItemTemplate WHERE Id_nb='bainshee_item'").fetchone())
   else:result['original_promotion_has_item_gift']=False
  if training_mode:
   values.update(Health=200,DeathTime=0,HasGravestone=0,DisabledSpells='',DisabledAbilities='')
   npc=db.execute("SELECT Mob_ID FROM Mob WHERE Name IN ('Codex Magic Target','Codex Pet Training Dummy')").fetchone();assert npc
   update(db,'Mob','Mob_ID',npc['Mob_ID'],{'Name':'Codex Expansion Trainer','ClassType':'DOL.GS.Trainer.'+trainer_types[class_id],'Guild':'Trainer','Model':342,'Level':50,'Realm':3,'Flags':0,'AggroLevel':0,'Speed':0,'X':char['Xpos']+80,'Y':char['Ypos']+40,'Z':char['Zpos']})
  if args.bainshee_combat:
   values.update(Health=200,DeathTime=0,HasGravestone=0,DisabledSpells='',DisabledAbilities='')
   npc=db.execute("SELECT Mob_ID FROM Mob WHERE Name IN ('Codex Magic Target','Codex Pet Training Dummy')").fetchone();assert npc
   update(db,'Mob','Mob_ID',npc['Mob_ID'],{'Name':'Codex Bainshee Target','ClassType':'DOL.GS.GameNPC','Guild':'','Model':118,'Level':50,'Realm':0,'Flags':0,'AggroLevel':0,'Speed':0,'X':char['Xpos'],'Y':char['Ypos']+400,'Z':char['Zpos']})
  if args.expansion_power:
   values.update(Health=10000,Mana=0,DeathTime=0,HasGravestone=0,DisabledSpells='',DisabledAbilities='')
   npc=db.execute("SELECT Mob_ID FROM Mob WHERE Name IN ('Codex Magic Target','Codex Pet Training Dummy')").fetchone();assert npc
   update(db,'Mob','Mob_ID',npc['Mob_ID'],{'Name':'Codex Power Target','ClassType':'DOL.GS.GameNPC','Guild':'','Model':118,'Level':45,'Realm':0,'Flags':0,'AggroLevel':0,'Speed':0,'X':char['Xpos'],'Y':char['Ypos']+60,'Z':char['Zpos']})
  if args.vampiir_bolt:
   values.update(Health=10000,Mana=0,DeathTime=0,HasGravestone=0,DisabledSpells='',DisabledAbilities='')
   npc=db.execute("SELECT Mob_ID FROM Mob WHERE Name IN ('Codex Magic Target','Codex Pet Training Dummy')").fetchone();assert npc
   update(db,'Mob','Mob_ID',npc['Mob_ID'],{'Name':'Codex Vampiir Target','ClassType':'DOL.GS.GameNPC','Guild':'','Model':118,'Level':45,'Realm':0,'Flags':0,'AggroLevel':0,'Speed':0,'X':char['Xpos'],'Y':char['Ypos']+400,'Z':char['Zpos']})
  update(db,'DOLCharacters','DOLCharacters_ID',char['DOLCharacters_ID'],values)
 cfg=json.loads(config_bytes);cfg['custom_class']=False;cfg['initial_spawn_m']=[(char['Xpos']-35*8192)*.025,char['Zpos']*.025,(char['Ypos']-51*8192)*.025];config.write_text(json.dumps(cfg),encoding='utf-8')
 if promotion_mode or args.combined_expansions:
  build=args.server_source.resolve()/'Release';assert (build/'GameServer.dll').exists()
  if args.candidate_build:
   candidate=args.candidate_build.resolve();assert candidate.is_relative_to(ROOT.resolve())
   receipt=json.loads((candidate/'build_receipt.json').read_text(encoding='utf-8-sig'))
   assert receipt['passed'] and not receipt['installed'] and receipt['compiled_bridge_overlay_verified']
   if args.vampiir_promotion:assert 'vampiir_creation' in receipt['candidate_features']
   if args.combined_expansions:
    assert set(receipt['candidate_features'])=={'vampiir_creation','minotaur_creation'}
    result['combined_expansion_build']=True
    result['candidate_build_receipt_sha256']=hashlib.sha256((candidate/'build_receipt.json').read_bytes()).hexdigest()
   assert Path(receipt['source_root']).resolve()==args.server_source.resolve()
   build=Path(receipt['libraries']).resolve();assert build.is_relative_to(candidate)
   for name,expected in receipt['binaries_sha256'].items():assert hashlib.sha256((build/name).read_bytes()).hexdigest()==expected
  for name in ['GameServer.dll','CoreBase.dll','CoreDatabase.dll']:
   for folder in [SERVER,SERVER/'lib',SERVER/'win-x64']:
    dst=folder/name
    if folder!=SERVER and not dst.exists():continue
    assert dst.resolve().is_relative_to(RUN.resolve())
    saved=backup/('candidate_'+str(len(candidate_files))+'_'+name) if dst.exists() else None
    if saved:shutil.copy2(dst,saved)
    candidate_files.append((dst,saved));shutil.copy2(build/name,dst)
  result['candidate_server_sha256']=hashlib.sha256((build/'GameServer.dll').read_bytes()).hexdigest()
 if args.vampiir_promotion and args.vampiir_race==18:
  import sys
  sys.path.insert(0,str(Path(__file__).resolve().parent))
  from shar_transport_metadata import apply as apply_shar_transport
  target=RUN/'LobbyProject/game/net/server.gd';saved=backup/'original_shar_transport.gd';shutil.copy2(target,saved);candidate_files.append((target,saved))
  canonical=(Path(__file__).resolve().parents[2]/'new-client/godot/game/net/server.gd').read_text(encoding='utf-8-sig')
  target.write_text(apply_shar_transport(target.read_text(encoding='utf-8-sig'),canonical),encoding='utf-8')
  for target in [RUN/'SourceModels/tasks.json',RUN/'models.json']:
   saved=backup/('original_shar_'+target.name);shutil.copy2(target,saved);candidate_files.append((target,saved))
   current=json.loads(target.read_text(encoding='utf-8-sig'))
   if target.name=='tasks.json':
    extra=json.loads((ROOT/'ExpansionRaceLab/OriginalTasks/tasks.json').read_text(encoding='utf-8-sig'))
    current=[row for row in current if str(row['id']) not in ['1075','1087']]+[row for row in extra if str(row['id']) in ['1075','1087']]
   else:
    extra=json.loads((ROOT/'ExpansionRaceLab/models_outfits_candidate.json').read_text(encoding='utf-8-sig'));current.update({key:extra[key] for key in ['1075','1087']})
   target.write_text(json.dumps(current),encoding='utf-8')
  result['canonical_shar_transport_staged_privately']=True
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
 if args.druid_promotion:
  wait(lambda:snapshot.get('player_status',{}).get('ready'),'Naturalist vitals ready')
  if snapshot['player_status']['vitals'].get('sitting'):
   send('player_sit',on=False,player_generation=snapshot['player_status']['generation'])
   wait(lambda:not snapshot['player_status']['vitals'].get('sitting'),'Naturalist stands before training')
  before={e.get('name') for e in snapshot['classic_ui']['entries'] if e.get('kind')=='spell'}
  assert not any(str(name).startswith('Call ') for name in before),'Naturalist must not receive a Druid pet before promotion'
  player=next(e for e in snapshot['entities'] if e['id']=='player:local')
  send('move',position_m=player['position_m'],forward_xz=player['forward_xz'],speed_mps=0);settle(2)
  wait(lambda:any(e.get('name')=='Codex Druid Trainer' for e in snapshot['entities']),'Original Druid trainer visible',20)
  npc=next(e for e in snapshot['entities'] if e.get('name')=='Codex Druid Trainer')
  send('interact',entity_id=npc['id'])
  wait(lambda:'Druid' in snapshot.get('interaction',{}).get('talk',{}).get('keywords',[]),'Original trainer offers Druid promotion',20)
  talk=snapshot['interaction']['talk'];send('keyword',reply_id=talk['id'],word='Druid')
  wait(lambda:any(e.get('name')=='Call Minor Nature Spirit' for e in snapshot['classic_ui']['entries'] if e.get('kind')=='spell'),'Promotion grants original Druid pet spell',20)
  with checked() as db:assert db.execute("SELECT Class FROM DOLCharacters WHERE Name='Codexdruid'").fetchone()[0]==47
  result['checks']['original_naturalist_promoted_by_trainer']=True
  send('target_self');settle(.5)
  entry=next(e for e in snapshot['classic_ui']['entries'] if e.get('name')=='Call Minor Nature Spirit' and e.get('kind')=='spell')
  send('ui_use',entry_id=entry['id'],entry_token=entry['token'])
  wait(lambda:snapshot['classic_ui'].get('pet',{}).get('valid'),'Promoted Druid summons original owned pet',25)
  pet=dict(snapshot['classic_ui']['pet'])
  wait(lambda:any(e['id']=='npc:'+str(pet['oid']) for e in snapshot['entities']),'Server pet exists in entity stream')
  entity=next(e for e in snapshot['entities'] if e['id']=='npc:'+str(pet['oid']))
  result['druid_pet']={'oid':pet['oid'],'name':entity.get('name'),'model_id':entity.get('model_id'),'rendered_visual_acceptance':False}
  entry=next(e for e in snapshot['classic_ui']['entries'] if e['id']=='petcmd:release')
  send('ui_use',entry_id=entry['id'],entry_token=entry['token'])
  wait(lambda:not snapshot['classic_ui'].get('pet',{}).get('valid'),'Original release clears owned pet',15)
  result['checks']['promoted_pet_summoned_and_released']=True
 if promotion_mode:
  player=next(e for e in snapshot.get('entities',[]) if e.get('id')=='player:local')
  send('move',position_m=player['position_m'],forward_xz=player['forward_xz'],speed_mps=0);settle(2)
  wait(lambda:any(e.get('name')=='Codex '+promotion_title+' Trainer' for e in snapshot.get('entities',[])),'Original candidate trainer visible',20)
  npc=next(e for e in snapshot['entities'] if e.get('name')=='Codex '+promotion_title+' Trainer')
  send('interact',entity_id=npc['id'])
  wait(lambda:promotion_title in snapshot.get('interaction',{}).get('talk',{}).get('keywords',[]),'Original trainer offers promotion keyword',20)
  talk=snapshot['interaction']['talk'];send('keyword',reply_id=talk['id'],word=promotion_title)
  def promoted():
   with checked() as db:return db.execute("SELECT Class FROM DOLCharacters WHERE Name='Codexdruid'").fetchone()[0]==class_id
  wait(promoted,'Original trainer saves advanced class',20)
  if args.bainshee_promotion:wait(lambda:any(e.get('name')=="Bawler's Bruise" for e in snapshot.get('classic_ui',{}).get('entries',[])),'Original trainer promotion updates Bainshee spell list',20)
  result['checks']['original_trainer_promotes_stalker' if args.vampiir_promotion else 'original_trainer_promotes_magician']=True;settle(2)
 if class_id in [39,58,62]:
  candidate=json.loads(proposal_path.read_text())
  startup=(D/'starting_spells_server.log').read_text(encoding='utf-8-sig',errors='replace')
  registered={kind:any('Found spell handler DOL.GS.Spells.'+row['class'] in startup for row in rows) for kind,rows in candidate['concrete_handler_source_coverage'].items()}
  assert all(registered.values()),registered
  result['runtime_registered_handler_types']=registered
 (D/'druid_level1_snapshot.json').write_text(json.dumps(snapshot),encoding='utf-8')
 result['checks']['starting_list']=True
 result['entries']=[{'name':e.get('name'),'group':e.get('group'),'id':e.get('id')} for e in snapshot.get('classic_ui',{}).get('entries',[]) if e.get('kind')=='spell']
 if args.career_proposal:
  required={58:{152,153,154,155,341},62:{69,68,67}}[class_id]
  not_yet_granted=set()
  if args.vampiir_promotion:
   career=json.loads(args.career_proposal.read_text())
   ability_ids={row['KeyName']:int(row['InternalID']) for row in career['rows']['Ability']}
   # The four inherent stat abilities start at level six in the pinned DOL
   # career. A level-five promotion must not be judged by the level-fifty fixture.
   not_yet_granted={ability_ids[row['AbilityKey']] for row in career['rows']['SpecXAbility'] if row['AbilityKey'] in ability_ids and int(row['SpecLevel'])>level}
   required-=not_yet_granted
  received={int(e['id']) for e in snapshot['qa_skill_audit']['skills']}
  assert required<=received,('Missing original career ability IDs',required-received)
  assert not (not_yet_granted&received),('Career ability granted before its original level',not_yet_granted&received)
  result['career_abilities']=[e for e in snapshot['qa_skill_audit']['skills'] if int(e['id']) in required]
  result['checks']['original_career_abilities_received']=True
 audit=snapshot['qa_skill_audit'];expected={str(x['name']) for x in audit['skills'] if int(x['page']) in [3,4]}
 for line in audit['spell_lines']:expected.update(str(x['name']) for x in line['spells'])
 actual={str(x['name']) for x in snapshot['classic_ui']['entries'] if x.get('kind')=='spell'}
 result['class_id']=class_id;result['level']=level;result['expected_spells']=sorted(expected);result['visible_spells']=sorted(actual);result['complete']=expected==actual
 if class_id in [39,58,62]:assert expected,'Candidate expansion class must receive actual spells, not merely an empty matching list'
 assert result['complete'],(expected,actual)
 if args.bainshee_promotion:
  assert len(expected)==7 and 'Gleam Ray' not in expected,'Promotion must replace the base-class list, not append stale entries'
  result['checks']['promotion_replaces_base_spell_list']=True
 if args.vampiir_bolt:
  import importlib.util
  spec=importlib.util.spec_from_file_location('vampiir_native_observer',Path(__file__).resolve().parents[1]/'pet_sight_relay.py');observer=importlib.util.module_from_spec(spec);spec.loader.exec_module(observer)
  wait(lambda:snapshot.get('player_status',{}).get('ready') and any(e.get('name')=='Codex Vampiir Target' for e in snapshot.get('entities',[])),'Vampiir ability target ready')
  player=next(e for e in snapshot['entities'] if e['id']=='player:local');enemy=next(e for e in snapshot['entities'] if e.get('name')=='Codex Vampiir Target');enemy_id=enemy['id']
  send('move',position_m=player['position_m'],forward_xz=[0,1],speed_mps=0)
  relay=observer.NativeSightRelay(sock,ROOT,session,snapshot,output=D,duration=95,entity_ids=['player:local',enemy_id],render=False);sock=relay
  wait(lambda:bool(relay.read_report().get('local_animation')),'Native observer loads Vampiir',80)
  send('target',entity_id=enemy_id);relay.start_probe(enemy_id)
  wait(lambda:relay.probe_result is not None,'Actual native geometry answers Vampiir target');assert relay.probe_result
  settle(.5);entry=next(e for e in snapshot['classic_ui']['entries'] if e.get('kind')=='ability' and e.get('name')=='Vampiir Bolt')
  with checked() as db:original=dict(db.execute('SELECT * FROM Spell WHERE SpellID=?',(13200+7,)).fetchone())
  assert original['Type']=='VampiirBolt';mana_before=snapshot['player_status']['vitals']['mana'];health_before=enemy['health'];assert mana_before==0
  # Instant original abilities consume TargetInView from UseSkill; they need
  # not ask the asynchronous LOS responder. First verify the unseen flag is
  # rejected, then restore the actual native geometry result for the cast.
  combat_visibility_override=False;settle(.5)
  unseen_seq={e.get('seq') for e in effect_trace}
  send('ui_use',entry_id=entry['id'],entry_token=entry['token']);settle(3)
  assert snapshot['player_status']['vitals']['mana']==0,'Unseen target must not grant power'
  assert not any(e.get('seq') not in unseen_seq and e.get('kind')=='release' and e.get('effect_id')==original['ClientEffect'] for e in effect_trace),'Unseen bolt must not release'
  result['checks']['unseen_target_flag_blocks_instant_bolt']=True
  combat_visibility_override=None;settle(.5)
  send('ui_use',entry_id=entry['id'],entry_token=entry['token'])
  wait(lambda:any(e.get('kind')=='release' and e.get('effect_id')==original['ClientEffect'] and not e.get('resisted') for e in effect_trace),'Original Vampiir ability releases matching bolt',25)
  wait(lambda:snapshot['player_status']['vitals']['mana']>0,'Original bolt obtains actual power from NPC',20)
  assert relay.probe_result is True and relay.probes,'Visible cast requires the actual native geometry probe'
  assert all(row['visible'] for row in relay.answers)
  assert next(e for e in snapshot['entities'] if e['id']==enemy_id)['health']==health_before,'Power bolt must not invent health damage'
  result['vampiir_bolt']={'normal_player_privileges':True,'ability_level':7,'original_spell_id':original['SpellID'],'effect_id':original['ClientEffect'],'initial_mana':0,'mana_after':snapshot['player_status']['vitals']['mana'],'visibility_contract':'original instant ability uses TargetInView; unseen flag rejected, then native geometry result supplied','native_los_answers':relay.answers,'native_probes':relay.probes,'events':effect_trace,'rendered_visual_acceptance':False}
  result['checks']['original_ability_power_bolt_and_native_los']=True
  combat_finished=True;sock=relay.backend;sock.settimeout(.1)
 if args.expansion_power:
  wait(lambda:snapshot.get('player_status',{}).get('ready') and any(e.get('name')=='Codex Power Target' for e in snapshot.get('entities',[])),'Normal power fixture ready')
  target=next(e for e in snapshot['entities'] if e.get('name')=='Codex Power Target');power_target=target['id']
  def face_power_target():
   player=next(e for e in snapshot['entities'] if e['id']=='player:local')
   send('move',position_m=player['position_m'],forward_xz=[0,1],speed_mps=0,target_in_view=True,target_entity_id=power_target)
  send('target',entity_id=power_target);face_power_target();settle(2)
  vitals=lambda:snapshot['player_status']['vitals']
  assert vitals()['mana']==0,'Power must start empty; no grant during combat'
  initial_health=vitals()['health'];target_health=target['health'];power_samples=[]
  send('combat_attack',on=True,entity_id=power_target,player_generation=snapshot['player_status']['generation'])
  deadline=time.monotonic()+35;next_face=0
  while time.monotonic()<deadline:
   pump()
   if time.monotonic()>next_face:face_power_target();next_face=time.monotonic()+.2
   if not power_samples or vitals()!=power_samples[-1]:power_samples.append(dict(vitals()))
   if vitals()['mana']>0:break
   assert vitals()['health_pct']>=65,'Stop bounded fixture before unsafe health loss'
  send('combat_attack',on=False)
  wait(lambda:not snapshot['player_status'].get('attack_on') and not snapshot['player_status'].get('attack_pending'),'Original attack stops')
  assert any(row['mana']>0 for row in power_samples),'No actual combat power gain'
  if class_id==62:assert min(row['health'] for row in power_samples)<initial_health,'Mauler must actually receive damage'
  else:assert any(e['id']==power_target and e['health']<target_health for e in snapshot['entities']),'Vampiir must actually damage target'
  result['combat_power']={'normal_player_privileges':True,'initial_mana':0,'samples':power_samples,'player_initial_health':initial_health,'target_initial_health':target_health,'no_resource_grants':True,'native_collision_acceptance':False}
  result['checks']['original_combat_power_generation']=True
  # A stopped player attack does not pacify the ordinary NPC. Walk out of
  # reach before the normal seated logout, without a GM command or heal.
  departure=list(next(e for e in snapshot['entities'] if e['id']=='player:local')['position_m'])
  for step in range(1,41):
   point=list(departure);point[2]-=step*.6
   send('move',position_m=point,forward_xz=[0,-1],speed_mps=6,target_in_view=False,target_entity_id=power_target)
   settle(.1)
  send('move',position_m=point,forward_xz=[0,-1],speed_mps=0,target_in_view=False,target_entity_id=power_target)
  settle(15)
  assert vitals()['health']>0,'Power fixture must disengage alive'
  result['combat_power']['walked_out_of_melee_before_quit']=True
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
 if args.expansion_self_buff:
  name={58:'Minor Force',62:'Minor Discipline of Laresh'}[class_id]
  original=next(e for e in candidate['spells'] if e['Name']==name)
  assert original['Target']=='Self' and original['Power']>0 and original['Duration']>0
  player=next(e for e in snapshot['entities'] if e['id']=='player:local')
  send('move',position_m=player['position_m'],forward_xz=player['forward_xz'],speed_mps=0);send('target_self');settle(1)
  entry=next(e for e in snapshot['classic_ui']['entries'] if e.get('kind')=='spell' and e.get('name')==name)
  mana_before=snapshot['player_status']['vitals']['mana'];seq_before=max([e.get('seq',0) for e in effect_trace],default=0)
  send('ui_use',entry_id=entry['id'],entry_token=entry['token'])
  wait(lambda:any(e.get('seq',0)>seq_before and e.get('kind')=='release' and e.get('effect_id')==original['ClientEffect'] and not e.get('resisted') for e in effect_trace),'Original trained self buff releases effect',20)
  wait(lambda:snapshot['player_status']['vitals']['mana']<mana_before,'Trained self buff consumes power')
  assert not next(e for e in snapshot['entities'] if e['id']=='player:local').get('morphed')
  result['self_buff']={'spell':name,'original_type':original['Type'],'effect_id':original['ClientEffect'],'mana_before':mana_before,'mana_after':snapshot['player_status']['vitals']['mana'],'events':[e for e in effect_trace if e.get('seq',0)>seq_before],'rendered_visual_acceptance':False}
  result['checks']['trained_self_buff_power_and_effect']=True
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
  if args.native_form_probe:
   import importlib.util
   spec=importlib.util.spec_from_file_location('form_native_observer',Path(__file__).resolve().parents[1]/'pet_sight_relay.py');observer=importlib.util.module_from_spec(spec);spec.loader.exec_module(observer)
   native_inputs=[ROOT/'ExpansionRaceLab/FormLiveHost/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll']+[ROOT/'ExpansionRaceLab/MinotaurOwnerReview'/name for name in ['models.json','equipment_catalog.json','appearance_catalog.json']]
   if args.central_installed_native:
    native_inputs=[ROOT/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll',ROOT/'models.json',ROOT/'equipment_catalog_v01.json',ROOT/'Client/Plugins/DAoCVisualBridge/Content/ClassicUI/Pregame/appearance_catalog.json']
    result['native_uses_installed_central_assets']=True
   result['native_form_inputs']={str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in native_inputs}
   relay=observer.NativeSightRelay(sock,ROOT,session,snapshot,output=D,duration=100,entity_ids=['player:local'],render=True,native_profile='central_expansion_forms' if args.central_installed_native else 'expansion_forms');sock=relay
   wait(lambda:bool(relay.read_report().get('player_visual',{}).get('body_asset')) and bool(relay.read_report().get('player_visual',{}).get('portrait_asset')),'Native original body and inventory portrait actually rendered',90)
   native_before=relay.read_report()['player_visual']
   assert native_before['body_visible'] and native_before['body_asset']
   (D/'native_before.json').write_text(json.dumps(relay.read_report(),indent=2),encoding='utf-8')

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
  if args.native_form_probe:
   catalogue=json.loads((ROOT/'models.json' if args.central_installed_native else ROOT/'ExpansionRaceLab/MinotaurOwnerReview/models.json').read_text())
   expected_asset=catalogue[str(form_model)]['asset']
   wait(lambda:relay.read_report().get('player_visual',{}).get('body_asset')==expected_asset and relay.read_report().get('player_visual',{}).get('portrait_asset')==expected_asset,'Native body and portrait follow real server transformation',12)
   visual=relay.read_report()['player_visual']
   assert visual['body_visible'] and visual['weapon_components']==0
   assert visual.get('portrait_asset')==expected_asset
   (D/'native_transformed.json').write_text(json.dumps(relay.read_report(),indent=2),encoding='utf-8')
   result['checks']['live_native_body_and_portrait_transform']=True

  assert local_player().get('look',{})==original.get('look',{})
  result['checks']['original_offensive_cast_transforms']=True
  result['form_spell']="Bawler's Bruise";result['form_model']=form_model;result['race']=args.bainshee_race
  wait(lambda:not local_player().get('morphed') and local_player().get('model_id')==original['model_id'],'Original thirty-second Bainshee timer restores chosen figure',40)
  elapsed=time.monotonic()-changed_at;assert 25<=elapsed<=40,elapsed
  result['form_timer_seconds']=round(elapsed,2)
  assert local_player().get('look',{})==original.get('look',{})
  assert [(x['slot'],x.get('model')) for x in inv().get('items',[])]==worn
  result['checks']['original_timer_restores_appearance_and_inventory']=True
  if args.native_form_probe:
   wait(lambda:relay.read_report().get('player_visual',{}).get('body_asset')==native_before['body_asset'] and relay.read_report().get('player_visual',{}).get('portrait_asset')==native_before['portrait_asset'],'Native body and portrait restore actual original meshes',12)
   visual=relay.read_report()['player_visual']
   assert visual['body_visible'] and visual['weapon_components']==native_before['weapon_components']
   assert visual.get('portrait_asset')==native_before.get('portrait_asset')
   (D/'native_restored.json').write_text(json.dumps(relay.read_report(),indent=2),encoding='utf-8')
   result['checks']['live_native_original_body_and_equipment_restored']=True
   assert all(hashlib.sha256(Path(path).read_bytes()).hexdigest()==value for path,value in result['native_form_inputs'].items())
   result['checks']['native_form_inputs_unchanged']=True
   sock=relay.backend;sock.settimeout(.1)

  result['combat_damage_tested']=False
 send('chat',text='/quit')
 wait(lambda:not snapshot.get('in_game') and snapshot.get('character_lobby',{}).get('ready'),'Return to current creation rules',100 if native_combat_mode or training_mode or args.expansion_power or args.druid_promotion else 45)
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
 if args.druid_promotion:
  send('character_enter',name='Codexdruid',lobby_revision=lobby['revision'])
  wait(lambda:snapshot.get('in_game') and snapshot.get('classic_ui',{}).get('skills_ready') and {e.get('name') for e in snapshot.get('classic_ui',{}).get('entries',[]) if e.get('kind')=='spell'}==expected,'Druid promotion and spells survive saved reentry',45)
  with checked() as db:assert db.execute("SELECT Class FROM DOLCharacters WHERE Name='Codexdruid'").fetchone()[0]==47
  result['checks']['druid_class_and_spells_survive_saved_reentry']=True
 if args.bainshee_promotion or args.vampiir_promotion or (class_id==58 and level==6):
  send('character_enter',name='Codexdruid',lobby_revision=lobby['revision'])
  wait(lambda:snapshot.get('in_game') and snapshot.get('classic_ui',{}).get('skills_ready') and {e.get('name') for e in snapshot.get('classic_ui',{}).get('entries',[]) if e.get('kind')=='spell'}==expected,'Advanced class and spells survive saved reentry',45)
  with checked() as db:
   saved=db.execute("SELECT Class,Level,Race,Gender FROM DOLCharacters WHERE Name='Codexdruid'").fetchone()
   assert (saved['Class'],saved['Level'])==(class_id,level)
   if args.vampiir_promotion:assert (saved['Race'],saved['Gender'])==(args.vampiir_race,int(args.vampiir_female))
  if args.career_proposal:
   assert required<={int(entry['id']) for entry in snapshot['qa_skill_audit']['skills']}
  result['checks']['bainshee_class_and_spells_survive_saved_reentry' if args.bainshee_promotion else 'vampiir_class_and_spells_survive_saved_reentry']=True
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
