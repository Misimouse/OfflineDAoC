"""Create and reenter ten original race/sex figures in a marked disposable database only."""
from qa_runtime import *
import hashlib,shutil,socket,sqlite3,subprocess,time,traceback
import argparse,ast,importlib.util,re,sys

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--bainshee-candidate',action='store_true')
parser.add_argument('--shar-candidate',action='store_true')
parser.add_argument('--starter-equipment-repair',action='store_true')
parser.add_argument('--shar-promotion',action='store_true')
parser.add_argument('--shar-gm-transfer',action='store_true')
parser.add_argument('--server-source',type=Path)
parser.add_argument('--candidate-build',type=Path)
parser.add_argument('--classic-class-batch',type=int,choices=[0,1])
parser.add_argument('--eligibility-only',action='store_true')
args=parser.parse_args()
candidate_mode=args.bainshee_candidate or args.shar_candidate
assert not (args.bainshee_candidate and args.shar_candidate)
assert candidate_mode==bool(args.server_source),'Candidate creation requires the explicit server source'
assert args.classic_class_batch is None or not candidate_mode
assert not args.eligibility_only or args.classic_class_batch==0
assert not args.starter_equipment_repair or args.shar_candidate
assert not args.shar_promotion or (args.shar_candidate and args.starter_equipment_repair)
assert not args.shar_gm_transfer or (args.shar_candidate and args.starter_equipment_repair and not args.shar_promotion)
assert not args.candidate_build or candidate_mode
assert not args.shar_gm_transfer or args.candidate_build, 'GM transfer requires a sealed build with the canonical bridge overlay'

D=ROOT/'Reports'/('classic_creation_eligibility' if args.eligibility_only else ('classic_class_creation_'+str(args.classic_class_batch) if args.classic_class_batch is not None else ('bainshee_creation' if args.bainshee_candidate else 'character_creation_matrix')));D.mkdir(exist_ok=True)
if args.shar_candidate:D=ROOT/'Reports/shar_creation';D.mkdir(exist_ok=True)
if args.starter_equipment_repair:D=ROOT/'Reports/shar_starter_creation';D.mkdir(exist_ok=True)
if args.shar_promotion:D=ROOT/'Reports/shar_promotion';D.mkdir(exist_ok=True)
if args.shar_gm_transfer:D=ROOT/'Reports/shar_gm_transfer';D.mkdir(exist_ok=True)
SOURCE=Path(os.environ.get('DAOC_BRIDGE_QA_GODOT',str(ROOT/'Godot')))
report={'passed':False,'disposable_only':True,'real_protocol':True,'cases':[],'errors':[]}
backup=ROOT/'Backups'/('CharacterCreationMatrix_'+time.strftime('%Y%m%d-%H%M%S'));backup.mkdir()
server=client=sock=None;logs=[];session='';buffer=b'';snapshot={};serial=0;backed=False
store=RUN/'appdata/Godot/app_userdata/MMOEngine/server_looks.json'
assert store.resolve().is_relative_to(RUN.resolve())
store_before=store.read_bytes() if store.exists() else None
restored_files=[]
config=RUN/'bridge_config.json';config_before=config.read_bytes()

def replace_private(src,dst):
    assert dst.resolve().is_relative_to(RUN.resolve())
    saved=backup/('file_'+str(len(restored_files))+'_'+dst.name) if dst.exists() else None
    if saved:shutil.copy2(dst,saved)
    restored_files.append((dst,saved));dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)

def checked():
    db=sqlite3.connect(DB);db.row_factory=sqlite3.Row
    assert DB.is_relative_to(RUN) and db.execute('SELECT RunId FROM CodexQaIsolationMarker').fetchone()[0]==RUN.name
    return db

def pump():
    global buffer,snapshot,session
    try:data=sock.recv(1048576)
    except socket.timeout:return
    if not data:raise RuntimeError('Disposable bridge closed')
    buffer+=data
    while b'\n' in buffer:
        line,buffer=buffer.split(b'\n',1);row=json.loads(line)
        if row.get('type')=='hello':session=row['session']
        if row.get('type')=='snapshot':snapshot=row

def wait(predicate,label,seconds=45):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        pump()
        if predicate():return
    (D/'timeout_snapshot.json').write_text(json.dumps(snapshot,indent=2),encoding='utf-8')
    raise RuntimeError(label+'; lobby feedback='+str(snapshot.get('character_lobby',{}).get('feedback')))

def lobby():return snapshot.get('character_lobby',{})

def settle(seconds):
    end=time.monotonic()+seconds
    while time.monotonic()<end:pump()

def send(action,**values):
    global serial
    serial+=1;sock.sendall((json.dumps(dict(type='command',session=session,id='matrix:'+str(serial),action=action,**values))+'\n').encode())

def save_report():
    (D/'real_protocol.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

def verify_starter(base,figure):
    armour={51:{21:826,22:381,23:382,25:378,27:379,28:380},
            52:{21:835,22:386,23:387,25:383,27:384,28:385},
            54:{21:438,22:396,23:397,25:393,27:394,28:395}}[base]
    weapons={51:{12:19},52:{10:445,11:59},54:{10:454}}[base]
    expected={**armour,**weapons}
    def complete():
        items={int(row['slot']):row for row in snapshot.get('inventory',{}).get('items',[])}
        return snapshot.get('inventory',{}).get('ready') and all(slot in items and int(items[slot]['model'])==model for slot,model in expected.items())
    wait(complete,'Original complete starter equipment '+figure)
    items={int(row['slot']):row for row in snapshot['inventory']['items']}
    assert all(int(items[slot]['object_type'])=={51:32,52:37,54:33}[base] for slot in armour)
    fields=['slot','model','name','object_type','item_type','color','emblem','effect','extension','hand','weapon_stance']
    loadout={'items':[{key:items[slot][key] for key in fields if key in items[slot]} for slot in sorted(expected)],
             'weapon_set':snapshot['inventory']['weapon_set'],'gear':snapshot['inventory']['gear']}
    report.setdefault('original_starter_loadouts',{})[str(base)+':'+figure]=loadout
    return loadout

def verify_original_bind(name,base):
    original=next(value for value in proposal['original_rows'] if value['ClassID']==base)
    with checked() as db:
        row=db.execute('SELECT BindXpos,BindYpos,BindZpos,BindRegion,BindHeading FROM DOLCharacters WHERE Name=? AND AccountName=?',(name,account_name)).fetchone()
        assert row and all(row[key]==original[source] for key,source in [('BindXpos','XPos'),('BindYpos','YPos'),('BindZpos','ZPos'),('BindRegion','Region'),('BindHeading','Heading')]), 'GM test transfer changed original bind'

try:
    for port in [10351,19737]:
        try:
            with socket.create_connection(('127.0.0.1',port),timeout=.2):raise RuntimeError('Private QA port occupied')
        except (ConnectionRefusedError,socket.timeout):pass
    with checked() as db:
        dest=sqlite3.connect(backup/'before.sqlite3.db');db.backup(dest);dest.close();backed=True
        account_row=db.execute("SELECT a.Name FROM Account a JOIN DOLCharacters c ON c.AccountName=a.Name WHERE c.Name='Codexdruid'").fetchone();assert account_row
        account_name=account_row['Name']
        # All ten creation slots are needed; this account/database is explicitly
        # disposable and the entire database is restored in finally.
        db.execute('DELETE FROM DOLCharacters WHERE AccountName=?',(account_name,))
        db.execute('UPDATE Account SET PrivLevel=?,Realm=3 WHERE Name=?',(3 if args.shar_gm_transfer else 1,account_name))
        if args.starter_equipment_repair:
            sys.path.insert(0,str(Path(__file__).resolve().parent))
            from prepare_hibernia_starter_repair import prepare as prepare_starter_repair
            repair=prepare_starter_repair(ROOT/'References/DOLPublic_b5b29c2ada76/ItemTemplate.json',DB)
            assert repair['passed'] and not repair['database_modified'] and len(repair['insert_rows'])==6
            for row in repair['insert_rows']:
                keys=list(row)
                db.execute('INSERT INTO ItemTemplate ('+','.join('"'+key+'"' for key in keys)+') VALUES ('+','.join('?' for key in keys)+')',[row[key] for key in keys])
            report['starter_repair_reference']=repair['reference'];report['starter_repair_inserted_templates']=[row['Id_nb'] for row in repair['insert_rows']]
        if args.shar_promotion:
            template=db.execute("SELECT * FROM Mob WHERE Name IN ('Codex Magic Target','Codex Pet Training Dummy') LIMIT 1").fetchone();assert template
            trainer_classes={42:'Mentalist',43:'Blademaster',44:'Hero',45:'Champion',50:'Ranger'}
            for advanced,title in trainer_classes.items():
                base={42:51,43:52,44:52,45:52,50:54}[advanced]
                starts=db.execute('SELECT * FROM StartupLocation WHERE RaceID=9 AND ClassID=? AND Region=200 AND RealmID=3 AND ClientRegionID=0 AND MinVersion=0',(base,)).fetchall();assert len(starts)==1
                start=starts[0];trainer=dict(template)
                trainer.update(Mob_ID='codex-qa-shar-trainer-'+str(advanced),Name='Codex Shar '+title+' Trainer',ClassType='DOL.GS.Trainer.'+title+'Trainer',Guild=title+' Trainer',Model=342,Level=50,Realm=3,Flags=0,AggroLevel=0,Speed=0,Region=200,X=start['XPos']+80,Y=start['YPos']+40,Z=start['ZPos'])
                assert not db.execute('SELECT 1 FROM Mob WHERE Mob_ID=?',(trainer['Mob_ID'],)).fetchone()
                db.execute('INSERT INTO Mob ('+','.join('"'+key+'"' for key in trainer)+') VALUES ('+','.join('?' for key in trainer)+')',list(trainer.values()))
        if candidate_mode:
            prop=db.execute("SELECT Value FROM ServerProperty WHERE Key='disabled_classes'").fetchone();assert prop
            pipeline=args.server_source.resolve().parent/'new-client/pipeline/build_server_classes.py';assert pipeline.exists()
            spec=importlib.util.spec_from_file_location('candidate_class_rules',pipeline)
            rules=importlib.util.module_from_spec(spec);spec.loader.exec_module(rules)
            if args.bainshee_candidate:
                disabled=rules.id_set(prop['Value']);report['qa_bainshee_previously_disabled']=39 in disabled;disabled.discard(39)
                db.execute("UPDATE ServerProperty SET Value=? WHERE Key='disabled_classes'",(';'.join(str(n) for n in sorted(disabled)),))
            else:
                prop=db.execute("SELECT Value FROM ServerProperty WHERE Key='disabled_races'").fetchone();assert prop
                disabled=rules.id_set(prop['Value']);report['qa_shar_previously_disabled']=18 in disabled;disabled.discard(18)
                db.execute("UPDATE ServerProperty SET Value=? WHERE Key='disabled_races'",(';'.join(str(n) for n in sorted(disabled)),))
                sys.path.insert(0,str(Path(__file__).resolve().parent))
                from prepare_shar_startup_proposal import prepare as prepare_shar_starts
                proposal=prepare_shar_starts(ROOT/'References/DOLPublic_b5b29c2ada76/StartupLocation.source.json',DB)
                assert proposal['passed'] and not proposal['database_modified']
                columns={row[1] for row in db.execute('PRAGMA table_info(StartupLocation)')}
                for row in proposal['insert_rows']:
                    assert set(row)<=columns and row['RaceID']==18 and row['Region']==200 and row['ClassID'] in [51,52,54]
                    keys=list(row)
                    db.execute('INSERT INTO StartupLocation ('+','.join('"'+key+'"' for key in keys)+') VALUES ('+','.join('?' for key in keys)+')',[row[key] for key in keys])
                report['shar_startup_reference']=proposal['reference']
                report['shar_startup_insert_rows']=proposal['insert_rows']
    if args.classic_class_batch is not None or args.shar_candidate:
        config_data=json.loads(config_before);config_data['custom_class']=False
        config.write_text(json.dumps(config_data),encoding='utf-8')
    if candidate_mode:
        server_source=args.server_source.resolve();assert (server_source/'GameServer/playerclasses/hibernia/ClassBainshee.cs').exists()
        build=server_source/'Release'
        if args.candidate_build:
            candidate_root=args.candidate_build.resolve();assert candidate_root.is_relative_to(ROOT.resolve())
            receipt=json.loads((candidate_root/'build_receipt.json').read_text(encoding='utf-8-sig'))
            assert receipt['passed'] and not receipt['installed'] and receipt['compiled_bridge_overlay_verified']
            assert Path(receipt['source_root']).resolve()==server_source
            build=Path(receipt['libraries']).resolve();assert build.is_relative_to(candidate_root)
            for name,digest in receipt['binaries_sha256'].items():assert hashlib.sha256((build/name).read_bytes()).hexdigest()==digest
            report['candidate_build_receipt_sha256']=hashlib.sha256((candidate_root/'build_receipt.json').read_bytes()).hexdigest()
            report['candidate_overlay_verified']=True
        assert (build/'GameServer.dll').exists()
        for name in ['GameServer.dll','CoreBase.dll','CoreDatabase.dll']:
            for folder in [SERVER,SERVER/'lib',SERVER/'win-x64']:
                if folder==SERVER or (folder/name).exists():replace_private(build/name,folder/name)
        rules.GS=server_source/'GameServer';rules.DB=DB;rules.OUT=RUN/('shar_server_classes.json' if args.shar_candidate else 'bainshee_server_classes.json');rules.main()
        candidate=json.loads(rules.OUT.read_text())
        if args.bainshee_candidate:assert candidate['classes']['39']['gender']=='female' and candidate['classes']['39']['races']==[9,11,12]
        else:assert {int(k) for k,v in candidate['classes'].items() if 18 in v['races']}=={42,43,44,45,50}
        original_net=RUN/'LobbyProject/game/net/server.gd';saved_net=backup/'original_server.gd';shutil.copy2(original_net,saved_net)
        text=original_net.read_text(encoding='utf-8-sig');anchor='res://content/rules/server_classes.json';assert anchor in text
        restored_files.append((original_net,saved_net));original_net.write_text(text.replace(anchor,rules.OUT.as_posix()),encoding='utf-8')
        if args.shar_candidate:
            text=original_net.read_text(encoding='utf-8-sig')
            for old,new in [
                ('15: ["Sylvan", "syl", 700, 708]}','15: ["Sylvan", "syl", 700, 708], 18: ["Shar", "sha", 1075, 1087]}'),
                ('"Valkyn": 14, "Sylvan": 15}','"Valkyn": 14, "Sylvan": 15, "Shar": 18}'),
                ('15: [70, 55, 60, 45, 70, 60, 60, 60]}','15: [70, 55, 60, 45, 70, 60, 60, 60], 18: [60, 50, 80, 50, 60, 60, 60, 60]}')]:
                if new not in text:
                    assert text.count(old)==1,('Private Shar transport anchor',old)
                    text=text.replace(old,new,1)
            original_net.write_text(text,encoding='utf-8')
            canonical_net=(Path(__file__).resolve().parents[2]/'new-client/godot/game/net/server.gd').read_text(encoding='utf-8-sig')
            for table in ['RACES','RACE_BY_NAME','RACE_STATS']:
                pattern=r'const '+table+r'\s*:=\s*(\{.*?\})'
                private_table=re.search(pattern,text,re.S);source_table=re.search(pattern,canonical_net,re.S)
                assert private_table and source_table, ('Missing transport table',table)
                assert ast.literal_eval(private_table[1])==ast.literal_eval(source_table[1]), ('QA transport differs from canonical source',table)
            report['canonical_transport_metadata_verified']=True
            report['private_transport_sha256']=hashlib.sha256(original_net.read_bytes()).hexdigest()
        report['candidate_only']=True;report['server_build_sha256']=hashlib.sha256((build/'GameServer.dll').read_bytes()).hexdigest()
    for p in SOURCE.glob('*.gd'):shutil.copy2(p,RUN/'Godot'/p.name)
    if args.shar_candidate:
        p=RUN/'Godot/character_lobby.gd';text=p.read_text(encoding='utf-8-sig')
        assert '["Celt","Firbolg","Elf","Lurikeen","Sylvan","Shar"]' in text
        assert '"Sylvan":"syl","Shar":"sha"}' in text
        p=RUN/'Godot/character_appearance.gd';text=p.read_text(encoding='utf-8-sig')
        assert '"syl_m","syl_f","sha_m","sha_f"]' in text
        report['canonical_gateway_shar_support']=True
    p=RUN/'Godot/visual_bridge.gd';p.write_text(p.read_text(encoding='utf-8-sig').replace('port: int = 19727','port: int = 19737'),encoding='utf-8')
    # Observe the original parsed skill lists without changing their contents.
    p=RUN/'Godot/live_gateway.gd';text=p.read_text();anchor='var states:Array=[]';assert anchor in text
    p.write_text(text.replace(anchor,'transport.snapshot_metadata["qa_skill_audit"]={"skills":server.skills,"spell_lines":server.spell_lines}\n        '+anchor),encoding='utf-8')
    p=RUN/'Godot/visual_bridge.gd';text=p.read_text();assert '["character",' in text;p.write_text(text.replace('["character",','["qa_skill_audit","character",'),encoding='utf-8')
    (RUN/'SourceModels').mkdir(exist_ok=True);shutil.copy2(ROOT/'SourceModels/tasks.json',RUN/'SourceModels/tasks.json')
    tasks=json.loads((ROOT/'SourceModels/tasks.json').read_text())
    if args.shar_candidate:
        expansion_tasks=json.loads((ROOT/'ExpansionRaceLab/OriginalTasks/tasks.json').read_text(encoding='utf-8-sig'))
        shar_tasks=[t for t in expansion_tasks if str(t['id']) in ['1075','1087']];assert len(shar_tasks)==2
        assert {t['info']['race'] for t in shar_tasks}=={'sha_m','sha_f'}
        tasks+=shar_tasks
        target=RUN/'SourceModels/tasks.json';saved=backup/'original_tasks.json';shutil.copy2(target,saved);restored_files.append((target,saved))
        target.write_text(json.dumps(tasks),encoding='utf-8')
        target=RUN/'models.json';saved=backup/'original_models.json';shutil.copy2(target,saved);restored_files.append((target,saved))
        native=json.loads(target.read_text(encoding='utf-8-sig'))
        extra=json.loads((ROOT/'ExpansionRaceLab/models_outfits_candidate.json').read_text(encoding='utf-8-sig'))
        native.update({ident:extra[ident] for ident in ['1075','1087']})
        target.write_text(json.dumps(native),encoding='utf-8')
    models={t.get('info',{}).get('race'):int(t['id']) for t in tasks if t.get('info',{}).get('race')}
    (RUN/'Reports/live/logout.request').unlink(missing_ok=True)
    log=(D/'server.log').open('w');logs.append(log)
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
    log=(D/'client.log').open('w');logs.append(log)
    client_command=[str(game/'tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'),'--headless','--path',str(RUN/'LobbyProject'),'--script',str(RUN/'Godot/gateway_main.gd'),'--','--server=127.0.0.1','--server-port=10351','--account='+account,'--password='+password,'--no-world','--bridge-character-menu']
    client=subprocess.Popen(client_command,cwd=RUN,env=ce,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    end=time.monotonic()+50
    while time.monotonic()<end:
        try:sock=socket.create_connection(('127.0.0.1',19737),timeout=.3);sock.settimeout(.1);break
        except OSError:time.sleep(.2)
    else:raise RuntimeError('Private bridge unavailable')
    wait(lambda:lobby().get('ready') and lobby().get('enabled'),'Initial empty character menu')
    assert not lobby()['characters']
    if args.bainshee_candidate:
        choices=[c for c in lobby()['choices'] if c['class_id']==39]
        assert len(choices)==3 and all(c['female'] for c in choices)
        assert {c['race'] for c in choices}=={'Celt','Elf','Lurikeen'}
        report['female_only_choices']=True
    if args.shar_candidate:
        choices=[c for c in lobby()['choices'] if c['race']=='Shar']
        assert len(choices)==10 and {c['class_id'] for c in choices}=={42,43,44,45,50}
        assert all(sum(c['class_id']==cid and c['female']==female for c in choices)==1 for cid in [42,43,44,45,50] for female in [False,True])
        report['shar_choices_complete']=True
    suffix=''.join(chr(97+int(x,16)) for x in hashlib.sha256(str(time.time_ns()).encode()).hexdigest()[:5])
    cases=[('Celt','cel',39,51),('Elf','elf',39,51),('Lurikeen','lur',39,51)] if args.bainshee_candidate else [('Celt','cel',47,53),('Firbolg','fir',47,53),('Elf','elf',41,51),('Lurikeen','lur',41,51),('Sylvan','syl',55,57)]
    if args.shar_candidate:cases=[('Shar','sha',42,51),('Shar','sha',43,52),('Shar','sha',44,52),('Shar','sha',45,52),('Shar','sha',50,54)]
    if args.classic_class_batch is not None:
        repo=Path(__file__).resolve().parents[3]
        pipeline=repo/'source/new-client/pipeline/build_server_classes.py'
        spec=importlib.util.spec_from_file_location('classic_matrix_rules',pipeline)
        rules=importlib.util.module_from_spec(spec);spec.loader.exec_module(rules)
        rules.GS=repo/'source/server/GameServer'
        enums=rules.enum_values(rules.GS/'Enums/eCharacterClass.cs','eCharacterClass')
        definitions={enums[c['enum']]:c for c in rules.parse_classes().values()}
        classic_ids=list(range(40,51))+[55,56]
        assert {c['class_id'] for c in lobby()['choices']}==set(classic_ids),('Classic fixture must not silently omit or enable a class',sorted({c['class_id'] for c in lobby()['choices']}))
        race_ids={'Celt':9,'Firbolg':10,'Elf':11,'Lurikeen':12,'Sylvan':15}
        genders=rules.class_gender_constraints()
        expected_pairs={(rid,female,cid) for rid in race_ids.values() for female in [False,True] for cid in classic_ids
                        if rid in definitions[cid]['races'] and (definitions[cid]['enum'] not in genders or female==(genders[definitions[cid]['enum']]=='female'))}
        actual_pairs={(race_ids[c['race']],bool(c['female']),int(c['class_id'])) for c in lobby()['choices']}
        assert actual_pairs==expected_pairs,('Race/class eligibility mismatch',sorted(expected_pairs-actual_pairs),sorted(actual_pairs-expected_pairs))
        report['eligibility']={'source':'original server EligibleRaces and gender constraints','total_combinations':len(race_ids)*2*len(classic_ids),'valid_choices':len(expected_pairs),'invalid_choices_absent':len(race_ids)*2*len(classic_ids)-len(expected_pairs),'complete':True}
        cases=[]
        prefixes={'Celt':'cel','Firbolg':'fir','Elf':'elf','Lurikeen':'lur','Sylvan':'syl'}
        for cid in classic_ids[args.classic_class_batch*7:(args.classic_class_batch+1)*7]:
            choice=next(c for c in lobby()['choices'] if c['class_id']==cid and not c['female'])
            base=enums[definitions[cid]['base']]
            cases.append((choice['race'],prefixes[choice['race']],cid,base))
        # Rejected creation must leave the menu usable for the valid cases below.
        revision=lobby()['revision']
        send('character_create',lobby_revision=revision,choice_id='invalid-race-class',name='Codexinvalid',look={})
        wait(lambda:lobby()['revision']>revision and not lobby().get('pending'),'Invalid choice rejected without leaving creation')
        assert lobby()['enabled'] and lobby()['ready'] and not lobby()['characters']
        assert lobby()['feedback']=='Choose a valid race and class.'
        report['invalid_choice_recoverable']=True
        if args.eligibility_only:cases=[]
    for race,prefix,advanced,base in cases:
        for female in ([False] if args.classic_class_batch is not None else ([True] if args.bainshee_candidate else [False,True])):
            figure=prefix+('_f' if female else '_m');choice=next(c for c in lobby()['choices'] if c['race']==race and c['female']==female and c['class_id']==advanced)
            meta=json.loads((game/'godot/content/characters/races'/figure/'figure.json').read_text())
            look={'size':2,'face':0,'eyes':0,'skin':0,'hair':0,'hair_color':0,'tattoo':0,'sliders':[2 if i%2 else 6 for i in range(len(meta.get('sliders',[])))]}
            name='Codex'+prefix+('f' if female else 'm')+chr(97+advanced//26)+chr(97+advanced%26)+suffix
            send('character_create',lobby_revision=lobby()['revision'],choice_id=choice['id'],name=name,look=look)
            wait(lambda:any(c['name']==name for c in lobby().get('characters',[])) and not lobby().get('pending'),'Server confirms '+figure,55)
            selected=next(c for c in lobby()['characters'] if c['name']==name)
            assert selected['prefix']==figure and selected['look']==look,(figure,selected)
            with checked() as db:
                row=db.execute('SELECT Class,Level,Gender,Xpos,Ypos,Zpos,Region,Direction FROM DOLCharacters WHERE Name=? AND AccountName=?',(name,account_name)).fetchone()
                assert row and row['Class']==base and row['Level']==1 and bool(row['Gender'])==female
                if args.shar_candidate:
                    original=next(value for value in proposal['original_rows'] if value['ClassID']==base)
                    assert all(row[key]==original[source] for key,source in [('Xpos','XPos'),('Ypos','YPos'),('Zpos','ZPos'),('Region','Region'),('Direction','Heading')]),('Original DOL Shar start not applied',dict(row),original)
                    # The native bridge currently publishes only Connacht zone207.
                    # First verify the real DOL start above, then move this disposable
                    # fixture to an existing authoritative Connacht start for entry QA.
                    starts=db.execute('SELECT * FROM StartupLocation WHERE RaceID=9 AND ClassID=? AND Region=200 AND RealmID=3 AND ClientRegionID=0 AND MinVersion=0',(base,)).fetchall()
                    assert len(starts)==1
                    start=starts[0]
                    if not args.shar_gm_transfer:
                        db.execute('UPDATE DOLCharacters SET Xpos=?,Ypos=?,Zpos=?,Region=?,Direction=?,BindXpos=?,BindYpos=?,BindZpos=?,BindRegion=?,BindHeading=? WHERE Name=? AND AccountName=?',
                            (start['XPos'],start['YPos'],start['ZPos'],start['Region'],start['Heading'],start['XPos'],start['YPos'],start['ZPos'],start['Region'],start['Heading'],name,account_name))
                        report['qa_connacht_relocation']={'source_startup_id':start['StartupLoc_ID'],'original_dol_spawn_verified_first':True,'reason':'Native map currently supports zone207 only; fixture relocation is not a replacement startup rule.'}
                    else:
                        assert all(row[key]==original[source] for key,source in [('Xpos','XPos'),('Ypos','YPos'),('Zpos','ZPos')])
                        report['original_spawn_and_bind_preserved_before_entry']=True
                    if args.shar_promotion:
                        # Level advancement is an explicit disposable fixture, not a GM command
                        # or a direct class assignment. The original trainer performs promotion.
                        db.execute('UPDATE DOLCharacters SET Level=5,Health=200,Mana=100,DeathTime=0,HasGravestone=0,DisabledSpells=?,DisabledAbilities=? WHERE Name=? AND AccountName=?',('', '', name,account_name))
            if args.shar_candidate:
                # Account.Characters caches the just-created object. Reconnect
                # normally so the fixture relocation is read from the database;
                # never forge a world-entry packet or alter the server cache.
                send('logout');client.wait(timeout=90);assert client.returncode==0
                sock.close();sock=None;session='';buffer=b'';snapshot={}
                client=subprocess.Popen(client_command,cwd=RUN,env=ce,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                end=time.monotonic()+50
                while time.monotonic()<end:
                    try:sock=socket.create_connection(('127.0.0.1',19737),timeout=.3);sock.settimeout(.1);break
                    except OSError:time.sleep(.2)
                else:raise RuntimeError('Private bridge reconnect unavailable')
                wait(lambda:lobby().get('ready') and any(c['name']==name for c in lobby().get('characters',[])),'Fresh login after QA fixture relocation')
                selected=next(c for c in lobby()['characters'] if c['name']==name)
                assert selected['prefix']==figure and selected['look']==look
                report['qa_relocation_loaded_by_fresh_login']=True
            send('character_enter',lobby_revision=lobby()['revision'],name=name)
            wait(lambda:snapshot.get('in_game') and snapshot.get('character')==name and snapshot.get('classic_ui',{}).get('skills_ready') and snapshot.get('player_status',{}).get('ready'),'New character enters '+figure,45)
            wait(lambda:any(e.get('id')=='player:local' and e.get('look')==look and e.get('model_id')==models[figure] for e in snapshot.get('entities',[])),'Chosen figure and look reach world '+figure)
            if args.shar_gm_transfer:
                wait(lambda:snapshot.get('player_status',{}).get('gm_mode',{}).get('ready'),'Server confirms GM test transfer permission')
                assert not snapshot['player_status']['gm_mode']['combat_test']
                player=next(e for e in snapshot['entities'] if e['id']=='player:local')
                assert snapshot['zone_id']==207 and len(player['position_m'])==3
                report['server_authorized_gm_transfer']=True
                verify_original_bind(name,base)
            if args.shar_promotion:
                title=trainer_classes[advanced];trainer_name='Codex Shar '+title+' Trainer'
                player=next(e for e in snapshot['entities'] if e['id']=='player:local')
                send('move',position_m=player['position_m'],forward_xz=player['forward_xz'],speed_mps=0)
                wait(lambda:any(e.get('name')==trainer_name for e in snapshot['entities']),'Original Shar trainer visible '+title,20)
                npc=next(e for e in snapshot['entities'] if e.get('name')==trainer_name)
                send('interact',entity_id=npc['id'])
                wait(lambda:any(word.casefold()==title.casefold() for word in snapshot.get('interaction',{}).get('talk',{}).get('keywords',[])),'Original promotion keyword '+title,20)
                talk=snapshot['interaction']['talk'];word=next(word for word in talk['keywords'] if word.casefold()==title.casefold())
                send('keyword',reply_id=talk['id'],word=word)
                def promoted():
                    with checked() as db:
                        row=db.execute('SELECT Class,Level FROM DOLCharacters WHERE Name=? AND AccountName=?',(name,account_name)).fetchone()
                        return row and row['Class']==advanced and row['Level']==5
                wait(promoted,'Original trainer saves Shar advanced class '+title,25)
                settle(3)
            audit=snapshot.get('qa_skill_audit',{});assert audit
            expected={str(x['name']) for x in audit['skills'] if int(x['page']) in [3,4]}
            for line in audit['spell_lines']:expected.update(str(x['name']) for x in line['spells'])
            actual={str(x['name']) for x in snapshot['classic_ui']['entries'] if x.get('kind')=='spell'}
            assert actual==expected,(figure,expected,actual)
            if (args.classic_class_batch is not None or args.shar_candidate) and not args.shar_promotion:
                base_spells={51:{'Gleam Ray','Lesser Powerward'},52:set(),53:{'Minor Revigoration'},54:set(),57:{"Grove's Protection"}}
                assert actual==base_spells[base],('Unexpected original base-class spells',advanced,base,actual)
            if args.starter_equipment_repair and not args.shar_promotion:verify_starter(base,figure)
            send('chat',text='/quit')
            wait(lambda:not snapshot.get('in_game') and lobby().get('ready'),'Saved return '+figure,90)
            selected=next(c for c in lobby()['characters'] if c['name']==name);assert selected['look']==look and selected['prefix']==figure
            if args.shar_gm_transfer:verify_original_bind(name,base)
            if args.classic_class_batch is not None or args.shar_candidate:
                send('character_enter',lobby_revision=lobby()['revision'],name=name)
                wait(lambda:snapshot.get('in_game') and snapshot.get('character')==name and snapshot.get('classic_ui',{}).get('skills_ready') and snapshot.get('player_status',{}).get('ready'),'Existing character reenters '+name,45)
                wait(lambda:any(e.get('id')=='player:local' and e.get('look')==look and e.get('model_id')==models[figure] for e in snapshot.get('entities',[])),'Existing look restored '+name)
                retained={str(e['name']) for e in snapshot['classic_ui']['entries'] if e.get('kind')=='spell'}
                assert retained==expected,('Existing character spell loss',advanced,expected,retained)
                if args.starter_equipment_repair and not args.shar_promotion:verify_starter(base,figure)
                if args.shar_promotion:
                    with checked() as db:
                        saved=db.execute('SELECT Class,Level FROM DOLCharacters WHERE Name=? AND AccountName=?',(name,account_name)).fetchone()
                        assert saved['Class']==advanced and saved['Level']==5
                send('chat',text='/quit')
                wait(lambda:not snapshot.get('in_game') and lobby().get('ready'),'Second saved return '+name,90)
            report['cases'].append({'figure':figure,'selected_class':advanced,'created':True,'base_class':base,'level':1,'world_model':models[figure],'appearance_retained':True,'spell_list_complete':True,'spells':sorted(actual),'saved_return':True,'existing_character_reentry':args.classic_class_batch is not None or args.shar_candidate});save_report()
            if args.shar_promotion:
                report['cases'][-1].update(level=5,original_trainer_promotion=True,advanced_class_retained=True);save_report()
            if args.shar_gm_transfer:
                verify_original_bind(name,base)
                report['cases'][-1].update(original_bind_preserved=True,server_authorized_gm_transfer=True);save_report()
            print('CREATION_MATRIX_CASE '+figure+' passed',flush=True)
    expected_count=len(cases) if args.classic_class_batch is not None else (3 if args.bainshee_candidate else 10)
    assert len(report['cases'])==expected_count and len(lobby()['characters'])==expected_count
    report['passed']=True
except Exception:report['errors'].append(traceback.format_exc())
finally:
    if sock and session:
        try:send('logout')
        except OSError:pass
    if client and client.poll() is None:
        (RUN/'Reports/live/logout.request').write_text('logout',encoding='utf-8')
        try:client.wait(timeout=90)
        except subprocess.TimeoutExpired:client.kill();client.wait();report['errors'].append('Private client required forced stop')
    if sock:sock.close()
    if server and server.poll() is None:
        server.stdin.write('exit\n');server.stdin.flush()
        try:server.wait(timeout=45)
        except subprocess.TimeoutExpired:server.kill();server.wait();report['errors'].append('Private server required forced stop')
    for log in logs:log.close()
    if store_before is None:store.unlink(missing_ok=True)
    else:store.write_bytes(store_before)
    report['appearance_profile_restored']=True
    config.write_bytes(config_before);report['bridge_config_restored']=True
    if backed:
        with checked() as db:
            src=sqlite3.connect(backup/'before.sqlite3.db');src.backup(db);src.close()
        report['database_restored']=True
    for dst,saved in reversed(restored_files):
        assert dst.resolve().is_relative_to(RUN.resolve())
        if saved:shutil.copy2(saved,dst)
        elif dst.exists():dst.unlink()
    report['candidate_files_restored']=True
    report['normal_shutdown']=bool(client and server and client.returncode==0 and server.returncode==0)
    report['passed']=report['passed'] and report['normal_shutdown'] and not report['errors'];save_report()
    print(json.dumps({'passed':report['passed'],'cases':len(report['cases']),'errors':report['errors'],'database_restored':report.get('database_restored'),'appearance_profile_restored':report['appearance_profile_restored']}));assert report['passed']
