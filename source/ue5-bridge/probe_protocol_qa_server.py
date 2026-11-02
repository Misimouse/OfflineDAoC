"""Boot and normally stop only the disposable server prepared by prepare_protocol_qa.py."""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
from pathlib import Path
import json,os,socket,sqlite3,subprocess,time,xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent;REPORT=ROOT/'Reports/protocol_qa'
prepared=json.loads((REPORT/'prepared.json').read_text(encoding='utf-8'))
RUN=Path(prepared['root']).resolve();SERVER=Path(prepared['server']).resolve();DB=Path(prepared['database']).resolve()
assert RUN.is_relative_to((ROOT/'ProtocolQA').resolve()) and SERVER.is_relative_to(RUN) and DB.is_relative_to(RUN)
assert prepared['accounts_copied']==0 and prepared['characters_copied']==0 and not prepared['credentials_file_copied']
cfg=ET.parse(SERVER/'config/serverconfig.xml').getroot()
assert str(DB).replace('\\','/') in cfg.findtext('.//DBConnectionString')
assert cfg.findtext('.//Port')=='10351' and cfg.findtext('.//IP')=='127.0.0.1'
assert cfg.findtext('.//EnableUPnP')=='False' and cfg.findtext('.//MetricsEnabled')=='False'
assert not (SERVER/'lib/GameServerScripts.dll').exists()
with socket.socket() as guard:guard.bind(('127.0.0.1',10351))

def data_counts():
    with sqlite3.connect(DB) as db:
        marker=db.execute('SELECT RunId FROM CodexQaIsolationMarker').fetchone()[0];assert marker==RUN.name
        return {name:db.execute('SELECT count(*) FROM "'+name+'"').fetchone()[0] for name in ['Account','DOLCharacters','Mob','Regions','Zones','Spell']}
before=data_counts();assert before['Account']==before['DOLCharacters']==0
# The core creates its own three epic encounters on first startup; none came from the source database.
with sqlite3.connect(DB) as db:
    assert all(row[0] in ['DOL.GS.Cailean','DOL.GS.GreenMaw','DOL.GS.Evern'] for row in db.execute('SELECT ClassType FROM Mob'))
env={key:os.environ[key] for key in ['SystemRoot','WINDIR','COMSPEC','SystemDrive','OS','PROCESSOR_ARCHITECTURE','NUMBER_OF_PROCESSORS','ProgramFiles','ProgramW6432'] if key in os.environ}
for key,relative in [('APPDATA','appdata'),('LOCALAPPDATA','localappdata'),('USERPROFILE','user'),('TEMP','tmp'),('TMP','tmp'),('DOTNET_CLI_HOME','dotnet-home')]:
    path=RUN/relative;path.mkdir(exist_ok=True);env[key]=str(path)
dotnet=Path(str(INSTALL / 'tools/dotnet/dotnet.exe'))
env.update(DOTNET_ROOT=str(dotnet.parent),DOTNET_ROOT_X64=str(dotnet.parent),PATH=str(dotnet.parent)+os.pathsep+os.environ.get('SystemRoot','C:/Windows')+'/System32',DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1',DOTNET_NOLOGO='1',DOTNET_PROCESSOR_COUNT='2',ASPNETCORE_URLS='http://127.0.0.1:0')
state={'prepared_root':str(RUN),'game_port':10351,'source_server_port':10300,'before':before,'normal_server_modified':False,'normal_shutdown':False,'ready':False,'errors':[]}
logpath=RUN/'bootstrap_console.log';process=None
try:
    with logpath.open('w',encoding='utf-8') as log:
        process=subprocess.Popen([str(dotnet),str(SERVER/'CoreServer.dll'),'--start'],cwd=SERVER,env=env,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
        state['server_pid']=process.pid;print('Isolated server launched on its own configuration.',flush=True)
        end=time.monotonic()+50
        while process.poll() is None and time.monotonic()<end:
            with socket.socket() as peer:
                peer.settimeout(.2)
                if peer.connect_ex(('127.0.0.1',10351))==0:state['ready']=True;break
            time.sleep(.3)
        if not state['ready']:raise RuntimeError('Disposable server did not open its own port; inspect its private log.')
        time.sleep(1);state['after_start']=data_counts()
        assert state['after_start']['Account']==state['after_start']['DOLCharacters']==0
        print('Isolated endpoint ready; original accounts and characters are absent.',flush=True)
except Exception as error:state['errors'].append(str(error))
finally:
    if process is not None and process.poll() is None:
        try:
            process.stdin.write('exit\n');process.stdin.flush();process.wait(timeout=45);state['normal_shutdown']=True
        except (OSError,subprocess.TimeoutExpired):
            state['errors'].append('Disposable process did not finish its normal shutdown; stopped only its own process.')
            process.kill();process.wait(timeout=10)
    if process is not None:state['exit_code']=process.returncode
    state['passed']=state['ready'] and state['normal_shutdown'] and not state['errors'] and state.get('exit_code')==0
    (REPORT/'bootstrap.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
    print(json.dumps({'passed':state['passed'],'ready':state['ready'],'normal_shutdown':state['normal_shutdown'],'errors':state['errors']}),flush=True)
if not state['passed']:raise SystemExit(1)
