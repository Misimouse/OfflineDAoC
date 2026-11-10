"""Compile the inactive trade codec privately; never replace installed network files."""
import argparse,json,os,shutil,subprocess
from pathlib import Path
from datetime import datetime
from prepare_combined_expansion_data import digest

def verify(workspace,install,engine):
    qa=Path(__file__).resolve().parent;repo=qa.parents[2];normal=install/'new-client/godot'
    root=workspace/'PlayerTradeLab/Codec'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');source=root/'BackendSource';source.mkdir(parents=True)
    inputs={};normal_files=[normal/'game/net/DaocClient.cs',normal/'.godot/mono/temp/bin/Debug/MMOEngine.dll',normal/'.godot/mono/temp/bin/Debug/MMOEngine.pdb']
    normal_hashes={str(p):digest(p) for p in normal_files}
    for p in normal.rglob('*.cs'):
        if '.godot' in p.parts:continue
        target=source/p.relative_to(normal);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target);inputs[str(p)]=digest(p)
    codec=repo/'source/new-client/godot/game/net/DaocTradeCodec.cs';shutil.copy2(codec,source/'game/net/DaocTradeCodec.cs');inputs[str(codec)]=digest(codec)
    shutil.copy2(normal/'MMOEngine.csproj',source/'MMOEngine.csproj');inputs[str(normal/'MMOEngine.csproj')]=digest(normal/'MMOEngine.csproj')
    feed=install/'new-client/tools/godot_net/GodotSharp/Tools/nupkgs';assert feed.is_dir()
    (source/'nuget.config').write_text('<configuration><packageSources><clear/><add key="local" value="'+str(feed)+'"/></packageSources></configuration>')
    sdk=engine/'Binaries/ThirdParty/DotNet/10.0/win-x64';env=dict(os.environ,DOTNET_ROOT=str(sdk),DOTNET_ROOT_X64=str(sdk),DOTNET_CLI_HOME=str(root/'DotNetHome'),DOTNET_CLI_TELEMETRY_OPTOUT='1')
    def run(args,name):
        result=subprocess.run([str(sdk/'dotnet.exe')]+args,env=env,capture_output=True,text=True,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
        (root/(name+'.log')).write_text(result.stdout+result.stderr,encoding='utf-8');assert result.returncode==0,str(root/(name+'.log'));return result.stdout
    candidate=root/'BackendCandidate';run(['build',str(source/'MMOEngine.csproj'),'-c','Debug','-o',str(candidate),'-v:minimal'],'build')
    probe=root/'PacketProbe';probe.mkdir();original=qa/'player_trade_packet_probe.cs';shutil.copy2(original,probe/'Program.cs');inputs[str(original)]=digest(original)
    project=probe/'PacketProbe.csproj';project.write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup><ItemGroup><Reference Include="MMOEngine"><HintPath>'+str(candidate/'MMOEngine.dll')+'</HintPath></Reference><Reference Include="GodotSharp"><HintPath>'+str(candidate/'GodotSharp.dll')+'</HintPath></Reference></ItemGroup></Project>')
    (probe/'nuget.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>')
    output=run(['run','--project',str(project),'--no-launch-profile'],'packet_probe');result=json.loads(next(line for line in output.splitlines() if line.startswith('{')))
    assert result['passed'] and result['checks']>=100 and not result['failures']
    assert all(digest(Path(p))==h for p,h in inputs.items()) and all(digest(Path(p))==h for p,h in normal_hashes.items())
    result.update(source_inputs=inputs,normal_runtime_unchanged=True,server_started=False,decoder_dispatch_installed=False,ui_installed=False,candidate_backend=str(candidate/'MMOEngine.dll'))
    path=root/'verified.json';path.write_text(json.dumps(result,indent=2));return dict(passed=True,checks=result['checks'],proof=str(path),installed=False)
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ['workspace','install','engine']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.install.resolve(),a.engine.resolve())))
