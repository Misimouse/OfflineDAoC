"""Rebuild and verify the private original network backend, never the played install."""
import argparse,json,os,shutil,subprocess
from pathlib import Path
from prepare_combined_expansion_data import digest

def verify(workspace,install,engine):
 lab=workspace/'RemotePlayerLab';root=lab/'BackendSource';root.mkdir(exist_ok=True)
 repo=Path(__file__).resolve().parents[3];network=repo/'source/new-client/godot/game/net/DaocClient.cs';normal=install/'new-client/godot';inputs={}
 for p in normal.rglob('*.cs'):
  if '.godot' in p.parts:continue
  origin=network if p==normal/'game/net/DaocClient.cs' else p;target=root/p.relative_to(normal);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(origin,target);inputs[str(origin)]=digest(origin)
 shutil.copy2(normal/'MMOEngine.csproj',root/'MMOEngine.csproj');inputs[str(normal/'MMOEngine.csproj')]=digest(normal/'MMOEngine.csproj')
 feed=install/'new-client/tools/godot_net/GodotSharp/Tools/nupkgs';assert feed.is_dir();(root/'nuget.config').write_text('<configuration><packageSources><clear/><add key="local" value="'+str(feed)+'"/></packageSources></configuration>')
 candidate=lab/'BackendCandidate';sdk=engine/'Binaries/ThirdParty/DotNet/10.0/win-x64';env=dict(os.environ,DOTNET_ROOT=str(sdk),DOTNET_ROOT_X64=str(sdk),DOTNET_CLI_HOME=str(lab/'DotNetHome'),DOTNET_CLI_TELEMETRY_OPTOUT='1')
 def run(args,log):
  result=subprocess.run([str(sdk/'dotnet.exe')]+args,env=env,capture_output=True,text=True,timeout=150,creationflags=subprocess.CREATE_NO_WINDOW);log.write_text(result.stdout+result.stderr);assert result.returncode==0,str(log);return result.stdout
 run(['build',str(root/'MMOEngine.csproj'),'-c','Debug','-o',str(candidate),'-v:minimal'],lab/'backend_build.log')
 checks=0
 for name,source,report in [('PacketProbe','remote_player_packet_probe.cs','packet_probe'),('HeaderProbe','ground_target_header_probe.cs','header_probe')]:
  directory=lab/name;directory.mkdir(exist_ok=True);original=Path(__file__).with_name(source);shutil.copy2(original,directory/'Program.cs');inputs[str(original)]=digest(original)
  project=directory/(name+'.csproj');project.write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup><ItemGroup><Reference Include="MMOEngine"><HintPath>'+str(candidate/'MMOEngine.dll')+'</HintPath></Reference><Reference Include="GodotSharp"><HintPath>'+str(candidate/'GodotSharp.dll')+'</HintPath></Reference></ItemGroup></Project>')
  (directory/'nuget.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>');text=run(['run','--project',str(project),'--no-launch-profile'],lab/(report+'.log'));data=json.loads(next(x for x in text.splitlines() if x.startswith('{')));assert data['passed'];checks+=data['checks'];(lab/(report+'.json')).write_text(json.dumps(data))
 assert checks>=73 and all(digest(Path(p))==h for p,h in inputs.items())
 runtime=normal/'.godot/mono/temp/bin/Debug';rows=[]
 for name in ['MMOEngine.dll','MMOEngine.pdb']:rows.append(dict(source=str(candidate/name),target=str(runtime/name),before_sha256=digest(runtime/name),after_sha256=digest(candidate/name)))
 rows.append(dict(source=str(network),target=str(normal/'game/net/DaocClient.cs'),before_sha256=digest(normal/'game/net/DaocClient.cs'),after_sha256=digest(network)))
 result=dict(passed=True,checks=checks,source_inputs=inputs,backend_files=rows,candidate_binary_sha256=digest(candidate/'MMOEngine.dll'),install_root=str(install),normal_runtime_modified=False)
 (lab/'backend_verified.json').write_text(json.dumps(result,indent=2));return dict(passed=True,checks=checks,normal_runtime_modified=False)
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for name in ['workspace','install','engine']:p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.install.resolve(),a.engine.resolve())))
