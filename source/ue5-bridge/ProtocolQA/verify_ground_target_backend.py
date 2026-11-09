"""Check production packet-header bytes without initializing a game or server."""
import argparse,json,os,subprocess
from pathlib import Path
from prepare_combined_expansion_data import digest

def verify(workspace,install,engine):
    lab=workspace/'GroundTargetLab';prepared=json.loads((lab/'backend_prepared.json').read_text());assert prepared['passed'] and all(digest(Path(p))==h for p,h in prepared['source_inputs'].items())
    candidate=lab/'BackendCandidate';assert (candidate/'MMOEngine.dll').is_file()
    probe=lab/'BackendHeaderProbe';probe.mkdir(exist_ok=True);source=Path(__file__).with_name('ground_target_header_probe.cs');(probe/'Program.cs').write_bytes(source.read_bytes())
    (probe/'BackendHeaderProbe.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup><ItemGroup><Reference Include="MMOEngine"><HintPath>'+str(candidate/'MMOEngine.dll')+'</HintPath></Reference><Reference Include="GodotSharp"><HintPath>'+str(candidate/'GodotSharp.dll')+'</HintPath></Reference></ItemGroup></Project>')
    (probe/'nuget.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>');sdk=engine/'Binaries/ThirdParty/DotNet/10.0/win-x64';env=dict(os.environ,DOTNET_ROOT=str(sdk),DOTNET_CLI_HOME=str(lab/'DotNetHome'))
    result=subprocess.run([str(sdk/'dotnet.exe'),'run','--project',str(probe/'BackendHeaderProbe.csproj'),'--no-launch-profile'],env=env,capture_output=True,text=True,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
    (lab/'backend_header_probe.log').write_text(result.stdout+result.stderr);assert result.returncode==0,result.stdout+result.stderr
    data=json.loads(next(l for l in result.stdout.splitlines() if l.startswith('{')));assert data['passed'] and data['checks']>=8
    normal=install/'new-client/godot';runtime=normal/'.godot/mono/temp/bin/Debug';assert digest(runtime/'GodotSharp.dll')==digest(candidate/'GodotSharp.dll')
    rows=[]
    for name in ['MMOEngine.dll','MMOEngine.pdb']:rows.append(dict(source=str(candidate/name),target=str(runtime/name),before_sha256=digest(runtime/name),after_sha256=digest(candidate/name)))
    source_network=Path(next(p for p in prepared['source_inputs'] if p.endswith('DaocClient.cs')));rows.append(dict(source=str(source_network),target=str(normal/'game/net/DaocClient.cs'),before_sha256=digest(normal/'game/net/DaocClient.cs'),after_sha256=digest(source_network)))
    data.update(source_inputs=prepared['source_inputs'],probe_source_sha256=digest(source),candidate_binary_sha256=digest(candidate/'MMOEngine.dll'),backend_files=rows,install_root=str(install.resolve()),normal_runtime_modified=False)
    (lab/'backend_verified.json').write_text(json.dumps(data,indent=2));return dict(passed=True,checks=data['checks'],backend_files=len(rows),normal_runtime_modified=False)
if __name__=='__main__':
    p=argparse.ArgumentParser();
    for k in ['workspace','install','engine']:p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.install.resolve(),a.engine.resolve())))
