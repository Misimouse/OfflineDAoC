"""Build candidate server libraries with the canonical bridge overlay, without replacing source files."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from xml.sax.saxutils import escape


def build(server_source, overlay, workspace, output, dotnet):
    server_source,overlay,workspace,output,dotnet=(p.resolve() for p in (server_source,overlay,workspace,output,dotnet))
    assert output.is_relative_to(workspace) and not output.is_relative_to(server_source)
    output.mkdir(parents=True,exist_ok=True)
    definition=json.loads((overlay/'overlay-files.json').read_text(encoding='utf-8-sig'))
    files=definition['files']
    assert len(files)==3 and 'GameServer/commands/gmcommands/BridgeGmCombatMode.cs' in files
    inputs=output/'compile_inputs.txt';targets=output/'bridge_overlay.targets';libraries=output/'libraries'
    edits=[]
    for name in files:
        source=overlay/name
        assert source.is_file() and source.resolve().is_relative_to(overlay)
        relative=Path(name).relative_to('GameServer').as_posix()
        original=server_source/name
        variants=[relative,relative.replace('/','\\'),'.\\'+relative.replace('/','\\'),str(original)]
        edits.append('<Compile Remove="'+escape(';'.join(variants),{'"':'&quot;'})+'" />')
        edits.append('<Compile Include="'+escape(str(source),{'"':'&quot;'})+'" />')
    targets.write_text('<Project><Target Name="CanonicalBridgeOverlay" BeforeTargets="CoreCompile" Condition="\'$(MSBuildProjectName)\' == \'GameServer\'">'
        '<ItemGroup>'+''.join(edits)+'</ItemGroup><WriteLinesToFile File="'+escape(str(inputs),{'"':'&quot;'})+'" Lines="@(Compile->\'%(FullPath)\')" Overwrite="true" />'
        '<Message Importance="high" Text="Canonical bridge overlay applied" /></Target></Project>',encoding='utf-8')
    env=dict(os.environ,DOTNET_ROOT=str(dotnet.parent),DOTNET_ROOT_X64=str(dotnet.parent),PATH=str(dotnet.parent)+os.pathsep+os.environ['PATH'])
    command=[str(dotnet),'build',str(server_source/'GameServer/GameServer.csproj'),'-c','Release','--no-restore',
        '-p:CustomBeforeMicrosoftCommonTargets='+str(targets),'-p:OutputPath='+str(libraries)+os.sep,'-p:NuGetAudit=false','-v:minimal']
    with (output/'build.log').open('w',encoding='utf-8') as log:
        result=subprocess.run(command,cwd=server_source,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode==0, 'Candidate build failed; inspect private build.log'
    compiled={Path(line.strip()).resolve() for line in inputs.read_text(encoding='utf-8-sig').splitlines() if line.strip()}
    for name in files:
        assert (overlay/name).resolve() in compiled
        assert (server_source/name).resolve() not in compiled
    binaries={name:hashlib.sha256((libraries/name).read_bytes()).hexdigest() for name in ['GameServer.dll','CoreBase.dll','CoreDatabase.dll']}
    report={'passed':True,'installed':False,'source_root':str(server_source),'overlay_root':str(overlay),
        'overlay_base_commit':definition['base_commit'],'overlay_source_sha256':{name:hashlib.sha256((overlay/name).read_bytes()).hexdigest() for name in files},
        'compiled_bridge_overlay_verified':True,'libraries':str(libraries),'binaries_sha256':binaries}
    (output/'build_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['server-source','overlay','workspace','output','dotnet']:parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();report=build(args.server_source,args.overlay,args.workspace,args.output,args.dotnet)
    print(json.dumps(report))
