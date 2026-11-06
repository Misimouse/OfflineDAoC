"""Observe actual UE PCM consumption and packet rules in the isolated audio candidate."""
import argparse
import json
from pathlib import Path
import subprocess

from prepare_combined_expansion_data import digest


def verify(workspace, engine, installed=False):
    root=workspace/'SpellAudioLab'
    built=json.loads((root/'native_build.json').read_text())
    resources=json.loads((root/'resources.json').read_text())
    assert built['passed'] and not built['normal_binary_modified'] and resources['passed'] and not resources['installed']
    project=Path(built['project'])
    binary=project.parent/'Plugins/DAoCVisualBridge/Binaries/Win64'
    assert all(digest(binary/name)==sha for name,sha in built['binaries_sha256'].items())
    assert all(digest(Path(path))==sha for path,sha in resources['files'].items())
    assert digest(Path(resources['catalog']))==resources['catalog_sha256']
    normal=workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    if installed:
        receipt=json.loads((root/'installed.json').read_text())
        assert receipt['installed'] and receipt['phase']=='complete'
        assert all(digest(Path(row['target']))==row['after_sha256'] for row in receipt['files'])
        assert digest(normal)==built['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll']
        assert digest(workspace/'Client/Plugins/DAoCVisualBridge/Content/OriginalAudio_v01/sounds.json')==resources['catalog_sha256']
    else:
        assert digest(normal)==built['normal_binary_sha256']
    normal_hash=digest(normal)
    output=root/('NativeInstalledAcceptance' if installed else 'NativeAcceptance')
    output.mkdir(exist_ok=True)
    report=output/'audio.json'
    report.unlink(missing_ok=True)
    command=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),str(project),'/Engine/Maps/Entry',
        '-game','-EnablePlugins=DAoCVisualBridge','-DaocBridge','-DaocBridgeReadOnly',
        '-DaocBridgeSpellAudioTest='+str(report),'-DaocBridgeSoundCatalog='+resources['catalog'],
        '-AudioMixer','-unattended','-nosplash','-d3d11','-RenderOffscreen','-windowed','-ResX=640','-ResY=360',
        '-abslog='+str(output/'engine.log')]
    if installed:command=[arg for arg in command if not arg.startswith('-DaocBridgeSoundCatalog=')]
    with (output/'stdout.log').open('w',encoding='utf-8') as log:
        result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode==0, 'Private audio host exited unsuccessfully'
    raw=report.read_bytes()
    row=json.loads(raw.decode('utf-16' if raw[:2] in [b'\xff\xfe',b'\xfe\xff'] else 'utf-8-sig'))
    assert row['passed'] and not row['failures'],row.get('failures')
    assert row['checks']>=12 and row['pcm_consumed_bytes']>0 and row['invalid_resources']==0
    assert row['active_voices']==0 and row['pending_clips']==0 and row['unresolved_references']==1
    assert not row['audible_owner_acceptance'] and row['test_gain_multiplier']==.03
    assert digest(normal)==normal_hash
    proof={'passed':True,'checks':row['checks'],'pcm_consumed_bytes':row['pcm_consumed_bytes'],
           'native_report_sha256':digest(report),'native_build_receipt_sha256':digest(root/'native_build.json'),
           'resources_receipt_sha256':digest(root/'resources.json'),'normal_binary_modified':False,
           'real_server_protocol_tested':False,'audible_owner_acceptance':False,'known_original_missing_sound_sets':[332]}
    proof['installed_client_resources_only']=installed
    (output/'verified.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
    return proof


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['workspace','engine']:parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--installed',action='store_true')
    args=parser.parse_args()
    print(json.dumps(verify(args.workspace.resolve(),args.engine.resolve(),args.installed)))
