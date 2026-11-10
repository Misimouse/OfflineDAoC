"""Compile and exercise the inactive reward codec; do not install or dispatch it."""
import argparse,json,os,shutil,subprocess
from pathlib import Path
from datetime import datetime
from prepare_combined_expansion_data import digest

def verify(workspace,install,engine,wire=False):
    qa=Path(__file__).resolve().parent;repo=qa.parents[2];normal=install/'new-client/godot'
    root=workspace/'QuestRewardsLab'/('WireCodec' if wire else 'Codec')/datetime.now().strftime('%Y%m%d-%H%M%S-%f');source=root/'BackendSource';source.mkdir(parents=True)
    inputs={};normal_files=[normal/'game/net/DaocClient.cs',normal/'.godot/mono/temp/bin/Debug/MMOEngine.dll',normal/'.godot/mono/temp/bin/Debug/MMOEngine.pdb']
    normal_hashes={str(p):digest(p) for p in normal_files}
    for path in normal.rglob('*.cs'):
        if '.godot' in path.parts:continue
        target=source/path.relative_to(normal);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target);inputs[str(path)]=digest(path)
    codec=repo/'source/new-client/godot/game/net/DaocQuestRewardCodec.cs';inputs[str(codec)]=digest(codec);shutil.copy2(codec,source/'game/net'/codec.name)
    if wire:
        dispatch=source/'game/net/DaocClient.cs';text=dispatch.read_text(encoding='utf-8-sig')
        line=next(l for l in text.splitlines() if 'case 0x81:' in l);assert text.count(line)==1
        dispatch.write_text(text.replace(line,line+'\n\t\t\t\tif (r.Left >= 2 && (r.At(1) == 0x21 || r.At(1) == 0x22)) return ReadQuestRewardDialog1127(r);',1))
    project=source/'MMOEngine.csproj';shutil.copy2(normal/project.name,project);inputs[str(normal/project.name)]=digest(normal/project.name)
    feed=install/'new-client/tools/godot_net/GodotSharp/Tools/nupkgs';assert feed.is_dir()
    (source/'nuget.config').write_text('<configuration><packageSources><clear/><add key="local" value="'+str(feed)+'"/></packageSources></configuration>')
    sdk=engine/'Binaries/ThirdParty/DotNet/10.0/win-x64';env=dict(os.environ,DOTNET_ROOT=str(sdk),DOTNET_ROOT_X64=str(sdk),DOTNET_CLI_HOME=str(root/'DotNetHome'),DOTNET_CLI_TELEMETRY_OPTOUT='1')
    def run(args,name):
        value=subprocess.run([str(sdk/'dotnet.exe')]+args,env=env,capture_output=True,text=True,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
        (root/(name+'.log')).write_text(value.stdout+value.stderr,encoding='utf-8');assert value.returncode==0,str(root/(name+'.log'));return value.stdout
    candidate=root/'BackendCandidate';run(['build',str(project),'-c','Debug','-o',str(candidate),'-v:minimal'],'build')
    probe=root/'PacketProbe';probe.mkdir();original=qa/'quest_reward_packet_probe.cs';shutil.copy2(original,probe/'Program.cs');inputs[str(original)]=digest(original)
    project=probe/'PacketProbe.csproj';project.write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup><ItemGroup><Reference Include="MMOEngine"><HintPath>'+str(candidate/'MMOEngine.dll')+'</HintPath></Reference><Reference Include="GodotSharp"><HintPath>'+str(candidate/'GodotSharp.dll')+'</HintPath></Reference></ItemGroup></Project>')
    (probe/'nuget.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>')
    text=run(['run','--project',str(project),'--no-launch-profile'],'packet_probe');result=json.loads(next(line for line in text.splitlines() if line.startswith('{')))
    assert result['passed'] and result['checks']>=100 and not result['failures']
    assert all(digest(Path(p))==h for p,h in inputs.items()) and all(digest(Path(p))==h for p,h in normal_hashes.items())
    result.update(source_inputs=inputs,normal_runtime_unchanged=True,server_started=False,decoder_dispatch_installed=False,ui_installed=False,candidate_dispatch_enabled=wire,candidate_backend=str(candidate/'MMOEngine.dll'),candidate_backend_sha256=digest(candidate/'MMOEngine.dll'))
    path=root/'verified.json';path.write_text(json.dumps(result,indent=2));return dict(passed=True,checks=result['checks'],proof=str(path),installed=False)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ['workspace','install','engine']:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--wire-candidate',action='store_true')
    a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.install.resolve(),a.engine.resolve(),a.wire_candidate)))
