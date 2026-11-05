"""Create and reenter ten original race/sex figures in a marked disposable database only."""
from qa_runtime import *
import hashlib,shutil,socket,sqlite3,subprocess,time,traceback
import argparse,importlib.util

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--bainshee-candidate',action='store_true')
parser.add_argument('--server-source',type=Path)
parser.add_argument('--classic-class-batch',type=int,choices=[0,1])
parser.add_argument('--eligibility-only',action='store_true')
args=parser.parse_args()
assert args.bainshee_candidate==bool(args.server_source),'Bainshee creation requires the explicit candidate server source'
assert args.classic_class_batch is None or not args.bainshee_candidate
assert not args.eligibility_only or args.classic_class_batch==0

D=ROOT/'Reports'/('classic_creation_eligibility' if args.eligibility_only else ('classic_class_creation_'+str(args.classic_class_batch) if args.classic_class_batch is not None else ('bainshee_creation' if args.bainshee_candidate else 'character_creation_matrix')));D.mkdir(exist_ok=True)
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
    raise RuntimeError(label+'; lobby feedback='+str(snapshot.get('character_lobby',{}).get('feedback')))

def lobby():return snapshot.get('character_lobby',{})

def send(action,**values):
    global serial
    serial+=1;sock.sendall((json.dumps(dict(type='command',session=session,id='matrix:'+str(serial),action=action,**values))+'\n').encode())

def save_report():
    (D/'real_protocol.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

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
        db.execute('UPDATE Account SET PrivLevel=1,Realm=3 WHERE Name=?',(account_name,))
        if args.bainshee_candidate:
            prop=db.execute("SELECT Value FROM ServerProperty WHERE Key='disabled_classes'").fetchone();assert prop
            pipeline=args.server_source.resolve().parent/'new-client/pipeline/build_server_classes.py';assert pipeline.exists()
            spec=importlib.util.spec_from_file_location('candidate_class_rules',pipeline)
            rules=importlib.util.module_from_spec(spec);spec.loader.exec_module(rules)
            disabled=rules.id_set(prop['Value']);report['qa_bainshee_previously_disabled']=39 in disabled;disabled.discard(39)
            db.execute("UPDATE ServerProperty SET Value=? WHERE Key='disabled_classes'",(';'.join(str(n) for n in sorted(disabled)),))
    if args.classic_class_batch is not None:
        config_data=json.loads(config_before);config_data['custom_class']=False
        config.write_text(json.dumps(config_data),encoding='utf-8')
    if args.bainshee_candidate:
        server_source=args.server_source.resolve();assert (server_source/'GameServer/playerclasses/hibernia/ClassBainshee.cs').exists()
        build=server_source/'Release';assert (build/'GameServer.dll').exists()
        for name in ['GameServer.dll','CoreBase.dll','CoreDatabase.dll']:
            for folder in [SERVER,SERVER/'lib',SERVER/'win-x64']:
                if folder==SERVER or (folder/name).exists():replace_private(build/name,folder/name)
        rules.GS=server_source/'GameServer';rules.DB=DB;rules.OUT=RUN/'bainshee_server_classes.json';rules.main()
        candidate=json.loads(rules.OUT.read_text());assert candidate['classes']['39']['gender']=='female' and candidate['classes']['39']['races']==[9,11,12]
        original_net=RUN/'LobbyProject/game/net/server.gd';saved_net=backup/'original_server.gd';shutil.copy2(original_net,saved_net)
        text=original_net.read_text(encoding='utf-8-sig');anchor='res://content/rules/server_classes.json';assert anchor in text
        restored_files.append((original_net,saved_net));original_net.write_text(text.replace(anchor,rules.OUT.as_posix()),encoding='utf-8')
        report['candidate_only']=True;report['server_build_sha256']=hashlib.sha256((build/'GameServer.dll').read_bytes()).hexdigest()
    for p in SOURCE.glob('*.gd'):shutil.copy2(p,RUN/'Godot'/p.name)
    p=RUN/'Godot/visual_bridge.gd';p.write_text(p.read_text(encoding='utf-8-sig').replace('port: int = 19727','port: int = 19737'),encoding='utf-8')
    # Observe the original parsed skill lists without changing their contents.
    p=RUN/'Godot/live_gateway.gd';text=p.read_text();anchor='var states:Array=[]';assert anchor in text
    p.write_text(text.replace(anchor,'transport.snapshot_metadata["qa_skill_audit"]={"skills":server.skills,"spell_lines":server.spell_lines}\n        '+anchor),encoding='utf-8')
    p=RUN/'Godot/visual_bridge.gd';text=p.read_text();assert '["character",' in text;p.write_text(text.replace('["character",','["qa_skill_audit","character",'),encoding='utf-8')
    (RUN/'SourceModels').mkdir(exist_ok=True);shutil.copy2(ROOT/'SourceModels/tasks.json',RUN/'SourceModels/tasks.json')
    tasks=json.loads((ROOT/'SourceModels/tasks.json').read_text())
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
    client=subprocess.Popen([str(game/'tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'),'--headless','--path',str(RUN/'LobbyProject'),'--script',str(RUN/'Godot/gateway_main.gd'),'--','--server=127.0.0.1','--server-port=10351','--account='+account,'--password='+password,'--no-world','--bridge-character-menu'],cwd=RUN,env=ce,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
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
    suffix=''.join(chr(97+int(x,16)) for x in hashlib.sha256(str(time.time_ns()).encode()).hexdigest()[:5])
    cases=[('Celt','cel',39,51),('Elf','elf',39,51),('Lurikeen','lur',39,51)] if args.bainshee_candidate else [('Celt','cel',47,53),('Firbolg','fir',47,53),('Elf','elf',41,51),('Lurikeen','lur',41,51),('Sylvan','syl',55,57)]
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
                row=db.execute('SELECT Class,Level,Gender FROM DOLCharacters WHERE Name=? AND AccountName=?',(name,account_name)).fetchone()
                assert row and row['Class']==base and row['Level']==1 and bool(row['Gender'])==female
            send('character_enter',lobby_revision=lobby()['revision'],name=name)
            wait(lambda:snapshot.get('in_game') and snapshot.get('character')==name and snapshot.get('classic_ui',{}).get('skills_ready') and snapshot.get('player_status',{}).get('ready'),'New character enters '+figure,45)
            wait(lambda:any(e.get('id')=='player:local' and e.get('look')==look and e.get('model_id')==models[figure] for e in snapshot.get('entities',[])),'Chosen figure and look reach world '+figure)
            audit=snapshot.get('qa_skill_audit',{});assert audit
            expected={str(x['name']) for x in audit['skills'] if int(x['page']) in [3,4]}
            for line in audit['spell_lines']:expected.update(str(x['name']) for x in line['spells'])
            actual={str(x['name']) for x in snapshot['classic_ui']['entries'] if x.get('kind')=='spell'}
            assert actual==expected,(figure,expected,actual)
            if args.classic_class_batch is not None:
                base_spells={51:{'Gleam Ray','Lesser Powerward'},52:set(),53:{'Minor Revigoration'},54:set(),57:{"Grove's Protection"}}
                assert actual==base_spells[base],('Unexpected original base-class spells',advanced,base,actual)
            send('chat',text='/quit')
            wait(lambda:not snapshot.get('in_game') and lobby().get('ready'),'Saved return '+figure,90)
            selected=next(c for c in lobby()['characters'] if c['name']==name);assert selected['look']==look and selected['prefix']==figure
            if args.classic_class_batch is not None:
                send('character_enter',lobby_revision=lobby()['revision'],name=name)
                wait(lambda:snapshot.get('in_game') and snapshot.get('character')==name and snapshot.get('classic_ui',{}).get('skills_ready') and snapshot.get('player_status',{}).get('ready'),'Existing character reenters '+name,45)
                wait(lambda:any(e.get('id')=='player:local' and e.get('look')==look and e.get('model_id')==models[figure] for e in snapshot.get('entities',[])),'Existing look restored '+name)
                retained={str(e['name']) for e in snapshot['classic_ui']['entries'] if e.get('kind')=='spell'}
                assert retained==expected,('Existing character spell loss',advanced,expected,retained)
                send('chat',text='/quit')
                wait(lambda:not snapshot.get('in_game') and lobby().get('ready'),'Second saved return '+name,90)
            report['cases'].append({'figure':figure,'selected_class':advanced,'created':True,'base_class':base,'level':1,'world_model':models[figure],'appearance_retained':True,'spell_list_complete':True,'spells':sorted(actual),'saved_return':True,'existing_character_reentry':args.classic_class_batch is not None});save_report()
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
