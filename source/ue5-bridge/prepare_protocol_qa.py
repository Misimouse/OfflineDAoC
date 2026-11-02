"""Prepare a fresh local QA server with game definitions, never with existing accounts/characters."""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
from pathlib import Path
import datetime,hashlib,json,shutil,socket,sqlite3,xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent
INSTALL=Path(str(INSTALL))
SOURCE=INSTALL/'runtime/server'
SOURCE_DB=INSTALL/'runtime/data/opendaoc.sqlite3.db'
REPORT=ROOT/'Reports/protocol_qa';REPORT.mkdir(exist_ok=True)
PARENT=ROOT/'ProtocolQA'
RUN=PARENT/datetime.datetime.now().strftime('run-%Y%m%d-%H%M%S')
assert RUN.resolve().is_relative_to(ROOT.resolve()) and not RUN.exists()
PORTS={'tcp':10351,'udp':10451,'bridge':19737}
for kind,port in PORTS.items():
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM if kind=='udp' else socket.SOCK_STREAM) as guard:
        guard.bind(('127.0.0.1',port))

STATIC={'Ability','ClassXRealmAbility_Atlas','ClassXSpecialization','ItemTemplate','LineXSpell',
        'NpcTemplate','Race','Specialization','SpecXAbility','Spell','SpellLine','SpellXCustomValues',
        'StarterEquipment','StartupLocation','Style','StyleXSpell','TimeXLevel','LanguageSystem','Salvage','SalvageYield',
        'Regions','Zones'}
FORBIDDEN={'Account','DOLCharacters','Inventory','Guild','PlayerInfo','PlayerXEffect','ServerProperty',
           'offline_local_options','offline_world_bots','bot_profiles','bot_settings','Mob','WorldObject'}
assert not STATIC.intersection(FORBIDDEN)

SERVER=RUN/'runtime/server';DATA=RUN/'runtime/data';SERVER.mkdir(parents=True);DATA.mkdir(parents=True)
copied=[]
def copy_binary(file,relative):
    assert file.suffix.lower()=='.dll' or file.name.endswith(('.deps.json','.runtimeconfig.json'))
    assert file.name.lower()!='gameserverscripts.dll' and 'credentials' not in [p.lower() for p in file.parts]
    target=SERVER/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,target);copied.append(str(relative))
for file in SOURCE.iterdir():
    if file.is_file() and (file.suffix.lower()=='.dll' or file.name.endswith(('.deps.json','.runtimeconfig.json'))):
        copy_binary(file,Path(file.name))
for directory in ['lib','runtimes']:
    for file in (SOURCE/directory).rglob('*'):
        if file.is_file() and file.suffix.lower()=='.dll' and file.name.lower()!='gameserverscripts.dll':
            copy_binary(file,file.relative_to(SOURCE))
for file in (SOURCE/'languages').rglob('*'):
    if file.is_file() and file.suffix.lower() in ['.txt','.xml','.json'] and file.name.lower()!='account.txt':
        target=SERVER/file.relative_to(SOURCE);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,target)

DB=DATA/'protocol-qa.sqlite3.db'
assert DB.resolve().is_relative_to(RUN.resolve()) and DB.resolve()!=SOURCE_DB.resolve()
source=sqlite3.connect(SOURCE_DB.as_uri()+'?mode=ro',uri=True)
source.execute('PRAGMA query_only=ON');source.execute('BEGIN')
destination=sqlite3.connect(DB)
counts={}
def quote(name):return '"'+name.replace('"','""')+'"'
try:
    schema=source.execute("select name,sql from sqlite_master where type='table' and name not like 'sqlite_%' order by name").fetchall()
    for name,sql in schema:
        assert sql and sql.lstrip().upper().startswith('CREATE TABLE')
        destination.execute(sql)
    for name in sorted(STATIC):
        where=' WHERE RegionID=200' if name in ['Regions','Zones'] else ' WHERE RealmID=3' if name=='StartupLocation' else ''
        cursor=source.execute('SELECT * FROM '+quote(name)+where)
        values='('+','.join('?' for _ in cursor.description)+')';total=0
        while rows:=cursor.fetchmany(500):
            destination.executemany('INSERT INTO '+quote(name)+' VALUES '+values,rows);total+=len(rows)
        counts[name]=total
    # Test spawn and network endpoints belong only to this new database.
    destination.execute("UPDATE Regions SET IP='127.0.0.1',Port=?",(PORTS['udp'],))
    destination.execute('UPDATE StartupLocation SET XPos=341280,YPos=468312,ZPos=5200,Heading=0,Region=200,ClientRegionID=0')
    for sql, in source.execute("select sql from sqlite_master where type='index' and sql is not null"):
        assert sql.lstrip().upper().startswith(('CREATE INDEX','CREATE UNIQUE INDEX'))
        destination.execute(sql)
    for name in FORBIDDEN:
        assert destination.execute('SELECT count(*) FROM '+quote(name)).fetchone()[0]==0,name
    destination.execute('CREATE TABLE CodexQaIsolationMarker (RunId TEXT NOT NULL, Scope TEXT NOT NULL)')
    destination.execute('INSERT INTO CodexQaIsolationMarker VALUES (?,?)',(RUN.name,'Fresh disposable accounts only; no real account data copied'))
    destination.commit()
finally:
    destination.close();source.close()

config=SERVER/'config';config.mkdir(exist_ok=True)
root=ET.Element('root');section=ET.SubElement(root,'Server')
settings={'Port':PORTS['tcp'],'IP':'127.0.0.1','RegionIP':'127.0.0.1','RegionPort':PORTS['udp'],
          'UdpIP':'127.0.0.1','UdpPort':PORTS['udp'],'EnableUPnP':'False','DetectRegionIP':'False',
          'ServerName':'Codex isolated protocol QA','ServerNameShort':'CodexQA','LogConfigFile':'./config/logconfig.xml',
          'ScriptCompilationTarget':'./lib/GameServerScripts.dll','ScriptAssemblies':'System.dll','EnableCompilation':'False',
          'AutoAccountCreation':'True','GameType':'Normal','CheatLoggerName':'cheats','GMActionLoggerName':'gm',
          'InvalidNamesFile':'./config/invalidnames.txt','DBType':'SQLITE',
          'DBConnectionString':'Data Source='+DB.as_posix()+';Version=3;Pooling=True;Journal Mode=WAL;Synchronous=Normal;Foreign Keys=True;Default Timeout=60',
          'DBAutosave':'True','DBAutosaveInterval':1,'MetricsEnabled':'False','MetricsInterval':60,'OtlpEndpoint':'http://127.0.0.1:0'}
for key,value in settings.items():ET.SubElement(section,key).text=str(value)
ET.indent(root);ET.ElementTree(root).write(config/'serverconfig.xml',encoding='utf-8',xml_declaration=True)
(config/'invalidnames.txt').write_text('',encoding='utf-8')
(config/'logconfig.xml').write_text('''<log4net><appender name="Console" type="log4net.Appender.ConsoleAppender"><layout type="log4net.Layout.PatternLayout"><conversionPattern value="%date %-5level %logger - %message%newline" /></layout></appender><root><level value="INFO" /><appender-ref ref="Console" /></root></log4net>''',encoding='utf-8')

# Copy the tested adapter into its own folder so reports and quickbars stay separate.
scripts=RUN/'Godot';scripts.mkdir()
for file in (ROOT/'Godot').glob('*.gd'):
    if not file.name.startswith('test_'):shutil.copy2(file,scripts/file.name)
bridge=scripts/'visual_bridge.gd';text=bridge.read_text(encoding='utf-8')
assert '19727' in text
text=text.replace('19727','19737');bridge.write_text(text,encoding='utf-8')
for name in ['models.json','collision_catalog.json','bridge_config.json']:
    file=ROOT/name
    if file.exists():shutil.copy2(file,RUN/name)
(RUN/'Reports/live').mkdir(parents=True);(RUN/'Client/Saved/ClassicUI').mkdir(parents=True)
state={'prepared':True,'server_started':False,'root':str(RUN),'server':str(SERVER),'database':str(DB),'ports':PORTS,
       'game_definition_rows':counts,'accounts_copied':0,'characters_copied':0,'inventory_copied':0,'mobs_copied':0,
       'credentials_file_copied':False,'external_world_scripts_loaded':False,'copied_binary_files':len(copied),
       'core_server_sha256':hashlib.sha256((SERVER/'CoreServer.dll').read_bytes()).hexdigest(),
       'original_server_modified':False,'original_server_port':10300}
(RUN/'isolation.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
(REPORT/'prepared.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
print(json.dumps({'prepared':True,'root':str(RUN),'accounts_copied':0,'characters_copied':0,'mobs_copied':0,'server_started':False}))
