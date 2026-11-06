"""Private actual combat playback plus regression of the installed original spell audio."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import subprocess
from prepare_combined_expansion_data import digest


def read(path):
    raw=path.read_bytes()
    return json.loads(raw.decode('utf-16' if raw[:2] in [b'\xff\xfe',b'\xfe\xff'] else 'utf-8-sig'))


def verify(workspace, engine, installed=False):
    root=workspace/'CombatAudioLab'
    built=read(root/'native_build.json')
    resources=read(root/'resources.json')
    assert built['passed'] and resources['passed'] and not resources['installed']
    normal=workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    if installed:
        receipt=read(root/'installed.json')
        assert receipt['installed'] and receipt['phase']=='complete'
        assert all(digest(Path(row['target']))==row['after_sha256'] for row in receipt['files'])
        assert digest(normal)==built['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll']
    else:assert digest(normal)==built['normal_binary_sha256']
    normal_hash=digest(normal)
    project=Path(built['project'])
    assert all(digest(project.parent/'Plugins/DAoCVisualBridge/Binaries/Win64'/p)==sha for p,sha in built['binaries_sha256'].items())
    assert all(digest(Path(p))==sha for p,sha in resources['files'].items())
    assert digest(Path(resources['catalog']))==resources['catalog_sha256']
    output=root/('NativeInstalledAcceptance' if installed else 'NativeAcceptance')
    # A later trigger delivery pins this proof. A new verification gets its own
    # folder rather than overwriting the historical evidence it depends on.
    if installed and (workspace/'WeaponModeAudioLab/installed.json').exists():
        output=root/'NativeInstalledAcceptanceRuns'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    output.mkdir(parents=True,exist_ok=True)
    reports={}
    for name,flag in [('combat','DaocBridgeCombatAudioTest'),('spell_regression','DaocBridgeSpellAudioTest')]:
        path=output/(name+'.json')
        path.unlink(missing_ok=True)
        command=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),str(project),'/Engine/Maps/Entry',
            '-game','-EnablePlugins=DAoCVisualBridge','-DaocBridge','-DaocBridgeReadOnly',
            '-'+flag+'='+str(path),'-DaocBridgeCombatSoundCatalog='+resources['catalog'],
            '-AudioMixer','-unattended','-nosplash','-d3d11','-RenderOffscreen','-windowed','-ResX=640','-ResY=360',
            '-abslog='+str(output/(name+'_engine.log'))]
        if installed:command=[arg for arg in command if not arg.startswith('-DaocBridgeCombatSoundCatalog=')]
        with (output/(name+'_stdout.log')).open('w',encoding='utf-8') as log:
            result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=100,creationflags=subprocess.CREATE_NO_WINDOW)
        assert result.returncode==0,(name,result.returncode)
        row=read(path)
        assert row['passed'] and not row['failures'],(name,row['failures'])
        assert row['pcm_consumed_bytes']>0 and row['invalid_resources']==0
        assert row['active_voices']==0 and row['pending_clips']==0
        assert row['unresolved_references']==1
        assert row['checks']>=(13 if name=='combat' else 15)
        reports[name]={'report_sha256':digest(path),'checks':row['checks'],'pcm_consumed_bytes':row['pcm_consumed_bytes']}
    assert digest(normal)==normal_hash
    proof={'passed':True,'normal_binary_modified':False,'real_server_protocol_tested':False,
        'audible_owner_acceptance':False,'reports':reports,'build_receipt_sha256':digest(root/'native_build.json'),
        'resources_receipt_sha256':digest(root/'resources.json')}
    proof['installed_client_resources_only']=installed
    proof['report_directory']=str(output)
    (output/'verified.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
    return proof


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['workspace','engine']:parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--installed',action='store_true')
    args=parser.parse_args()
    print(json.dumps(verify(args.workspace.resolve(),args.engine.resolve(),args.installed)))
