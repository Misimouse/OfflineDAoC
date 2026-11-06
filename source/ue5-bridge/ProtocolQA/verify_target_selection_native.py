"""Verify visible-body cursor selection privately; no server or owner login."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import subprocess
from prepare_combined_expansion_data import digest


def read(path):
    raw=path.read_bytes()
    return json.loads(raw.decode('utf-16' if raw[:2] in [b'\xff\xfe',b'\xfe\xff'] else 'utf-8-sig'))


def verify(workspace,engine,installed=False):
    root=workspace/'TargetSelectionLab';build=read(root/'native_build.json')
    assert build['passed'] and not build['normal_binary_modified']
    project=Path(build['project']);plugin=project.parent/'Plugins/DAoCVisualBridge'
    assert all(digest(plugin/'Binaries/Win64'/name)==sha for name,sha in build['binaries_sha256'].items())
    normal=workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    before=digest(normal)
    if installed:
        from central_activation_receipts import verify_files
        assert verify_files(workspace)['target_selection_installed']
        assert before==build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll']
        project=workspace/'Client/DAoCBridgeClient.uproject'
    else:assert before==build['normal_binary_sha256']
    output=root/('InstalledAcceptance' if installed else 'Acceptance')/datetime.now().strftime('%Y%m%d-%H%M%S-%f');output.mkdir(parents=True)
    fixture=output/'interaction.json'
    fixture.write_text(json.dumps({'cases':[{'revision':1,'target':{'id':''},'talk':{},'merchant':{},'dialogs':[],'messages':[],'feedback':''}]}),encoding='utf-8')
    reports={}
    for name,flag in [('selection','DaocBridgeInteractionTest'),('combat','DaocBridgeCombatAudioTest'),('spell','DaocBridgeSpellAudioTest')]:
        path=fixture if name=='selection' else output/(name+'.json')
        command=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),str(project),'/Engine/Maps/Entry',
            '-game','-EnablePlugins=DAoCVisualBridge','-DaocBridge','-DaocBridgeReadOnly','-'+flag+'='+str(path),
            '-AudioMixer','-unattended','-nosplash','-d3d11','-RenderOffscreen','-windowed','-ResX=1280','-ResY=720',
            '-abslog='+str(output/(name+'_engine.log'))]
        with (output/(name+'_stdout.log')).open('w',encoding='utf-8') as log:
            process=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=110,creationflags=subprocess.CREATE_NO_WINDOW)
        assert process.returncode==0,(name,process.returncode)
        path=Path(str(fixture)+'.native.json') if name=='selection' else path
        report=read(path);reports[name]=report
        assert report['passed'] and not report['failures'],(name,report['failures'])
        assert report['checks']>=(15 if name in ['selection','spell'] else 14)
        if name!='selection':assert report['pcm_consumed_bytes']>0 and report['invalid_resources']==0
    assert digest(normal)==before
    proof={'passed':True,'server_started':False,'normal_binary_modified':False,'installed_client':installed,'normal_sha256':before,
        'build_receipt_sha256':digest(root/'native_build.json'),'reports':reports,'report_directory':str(output)}
    (output/'verified.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
    return {'passed':True,'server_started':False,'normal_binary_modified':False,'checks':{name:row['checks'] for name,row in reports.items()},'report_directory':str(output)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['workspace','engine']:parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--installed',action='store_true')
    args=parser.parse_args();print(json.dumps(verify(args.workspace.resolve(),args.engine.resolve(),args.installed)))
