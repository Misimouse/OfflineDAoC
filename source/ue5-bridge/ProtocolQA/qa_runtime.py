import sys as _bridge_sys
from pathlib import Path as _BridgePath
_bridge_sys.path.insert(0,str(_BridgePath(__file__).resolve().parents[1]))
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
from pathlib import Path
import json,os
ROOT=Path(__file__).resolve().parents[1]
prepared=json.loads((ROOT/"Reports/protocol_qa/prepared.json").read_text())
RUN=Path(prepared["root"]).resolve();SERVER=Path(prepared["server"]).resolve();DB=Path(prepared["database"]).resolve()
assert RUN.is_relative_to(ROOT/"ProtocolQA") and DB.is_relative_to(RUN)
env={key:os.environ[key] for key in ['SystemRoot','WINDIR','COMSPEC','SystemDrive','OS','PROCESSOR_ARCHITECTURE','NUMBER_OF_PROCESSORS','ProgramFiles','ProgramW6432'] if key in os.environ}
for key,relative in [('APPDATA','appdata'),('LOCALAPPDATA','localappdata'),('USERPROFILE','user'),('TEMP','tmp'),('TMP','tmp'),('DOTNET_CLI_HOME','dotnet-home')]:
    path=RUN/relative;path.mkdir(exist_ok=True);env[key]=str(path)
dotnet=Path(str(INSTALL / 'tools/dotnet/dotnet.exe'))
env.update(DOTNET_ROOT=str(dotnet.parent),DOTNET_ROOT_X64=str(dotnet.parent),PATH=str(dotnet.parent)+os.pathsep+os.environ.get('SystemRoot','C:/Windows')+'/System32',DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1',DOTNET_NOLOGO='1',DOTNET_PROCESSOR_COUNT='2',ASPNETCORE_URLS='http://127.0.0.1:0')
