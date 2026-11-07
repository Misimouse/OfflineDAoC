"""Build candidate server libraries with the canonical bridge overlay, without replacing source files."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from xml.sax.saxutils import escape


def build(server_source, overlay, workspace, output, dotnet, vampiir_creation=False, minotaur_reference=None, guild_roster=False):
    server_source,overlay,workspace,output,dotnet=(p.resolve() for p in (server_source,overlay,workspace,output,dotnet))
    assert output.is_relative_to(workspace) and not output.is_relative_to(server_source)
    if guild_roster:assert not (output.parent/"installed.json").exists(), "Installed guild delivery is sealed"
    output.mkdir(parents=True,exist_ok=True)
    definition=json.loads((overlay/'overlay-files.json').read_text(encoding='utf-8-sig'))
    files=definition['files']
    assert len(files)==3 and 'GameServer/commands/gmcommands/BridgeGmCombatMode.cs' in files
    inputs=output/'compile_inputs.txt';targets=output/'bridge_overlay.targets';libraries=output/'libraries'
    edits=[]
    sources={name:overlay/name for name in files}
    variants_report={}
    if minotaur_reference:
        from prepare_minotaur_rule_variants import variants
        manifest=variants(minotaur_reference,server_source,output/'SourceVariants')
        assert manifest['passed'] and not manifest['mauler_enabled']
        for name,row in manifest['files'].items():
            sources[name]=Path(row['path'])
            variants_report[name]={**row,'scope':'Private Hibernian Minotaur base stats and four source-authorized advanced class eligibility rules.'}
    if vampiir_creation:
        name='GameServer/GlobalConstants.cs';original=server_source/name
        original_raw=original.read_bytes()
        raw=sources[name].read_bytes() if name in sources else original_raw
        anchor=b'// eCharacterClass.Vampiir,'
        assert raw.count(anchor)==1, 'Review changed original Vampiir starting-class rule'
        candidate=output/('SourceVariants/CombinedGlobalConstants.cs' if minotaur_reference else 'SourceVariants/GlobalConstants.cs');candidate.parent.mkdir(exist_ok=True)
        candidate.write_bytes(raw.replace(anchor,b'eCharacterClass.Vampiir,',1))
        sources[name]=candidate
        variants_report[name]={'original_sha256':hashlib.sha256(original_raw).hexdigest(),
            'candidate_sha256':hashlib.sha256(candidate.read_bytes()).hexdigest(),
            'path':str(candidate),'scope':'Enable the existing Vampiir starting-class rule only in this private build.'+(' Preserve the separately verified Hibernian Minotaur stats variant.' if minotaur_reference else '')}
    if guild_roster:
        from prepare_guild_server_variants import variants as guild_variants
        manifest=guild_variants(server_source,output/'GuildSourceVariants')
        assert manifest['passed']
        for name,row in manifest['files'].items():sources[name]=Path(row['path']);variants_report[name]=row
    for name,source in sources.items():
        assert source.is_file() and (source.resolve().is_relative_to(overlay) or source.resolve().is_relative_to(output))
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
    for name,source in sources.items():
        assert source.resolve() in compiled
        assert (server_source/name).resolve() not in compiled
    for name,row in variants_report.items():
        assert hashlib.sha256((server_source/name).read_bytes()).hexdigest()==row['original_sha256'], 'Normal source changed during private variant build'
    binaries={name:hashlib.sha256((libraries/name).read_bytes()).hexdigest() for name in ['GameServer.dll','CoreBase.dll','CoreDatabase.dll']}
    report={'passed':True,'installed':False,'source_root':str(server_source),'overlay_root':str(overlay),
        'overlay_base_commit':definition['base_commit'],'overlay_source_sha256':{name:hashlib.sha256((overlay/name).read_bytes()).hexdigest() for name in files},
        'compiled_bridge_overlay_verified':True,'libraries':str(libraries),'binaries_sha256':binaries,
        'candidate_features':(['vampiir_creation'] if vampiir_creation else [])+(['minotaur_creation'] if minotaur_reference else [])+(['guild_roster_cache'] if guild_roster else []),'source_variants':variants_report}
    (output/'build_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['server-source','overlay','workspace','output','dotnet']:parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--vampiir-creation',action='store_true',help='Private source variant only; never changes normal source or settings')
    parser.add_argument('--minotaur-reference',type=Path,help='Pinned DOL source; private four-class Minotaur candidate only, excluding Mauler')
    parser.add_argument('--guild-roster',action='store_true')
    args=parser.parse_args();report=build(args.server_source,args.overlay,args.workspace,args.output,args.dotnet,args.vampiir_creation,args.minotaur_reference,args.guild_roster)
    print(json.dumps(report))
