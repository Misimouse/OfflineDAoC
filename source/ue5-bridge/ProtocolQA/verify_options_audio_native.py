"""Check original options UI, persisted volume and native regressions without a server."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import subprocess
from prepare_combined_expansion_data import digest


def read(path):
    raw=path.read_bytes();return json.loads(raw.decode('utf-16' if raw[:2] in [b'\xff\xfe',b'\xfe\xff'] else 'utf-8-sig'))


def verify(workspace,engine,installed=False):
    root=workspace/'OptionsAudioLab';build=read(root/'native_build.json');art=read(root/'resources.json')
    assert build['passed'] and art['passed'] and digest(Path(art['source']))==digest(Path(art['candidate']))==art['sha256']
    project=Path(build['project']);normal=workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    normal_hash=digest(normal)
    if installed:
        from central_activation_receipts import verify_files
        assert verify_files(workspace)['options_audio_installed']
        assert normal_hash==build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll']
        project=workspace/'Client/DAoCBridgeClient.uproject'
    else:
        assert normal_hash==build['normal_binary_sha256']
        assert all(digest(project.parent/'Plugins/DAoCVisualBridge/Binaries/Win64'/p)==sha for p,sha in build['binaries_sha256'].items())
    output=root/('InstalledAcceptance' if installed else 'Acceptance')/datetime.now().strftime('%Y%m%d-%H%M%S-%f');output.mkdir(parents=True)
    reports={}
    for name,flag in [('options','DaocBridgeOptionsAudioTest'),('selection','DaocBridgeInteractionTest'),('combat','DaocBridgeCombatAudioTest'),('spell','DaocBridgeSpellAudioTest')]:
        path=output/(name+'.json');settings=output/(name+'.ini')
        settings.write_text('[Audio]\nMaster=0.35\nEffects=0.65\n' if name=='options' else '[Audio]\nMaster=1\nEffects=1\n',encoding='utf-8')
        if name=='selection':path.write_text(json.dumps({'cases':[{'revision':1,'target':{'id':''},'talk':{},'merchant':{},'dialogs':[],'messages':[],'feedback':''}]}),encoding='utf-8')
        command=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),str(project),'/Engine/Maps/Entry',
            '-game','-EnablePlugins=DAoCVisualBridge','-DaocBridge','-DaocBridgeReadOnly','-'+flag+'='+str(path),
            '-DaocBridgeAudioSettings='+str(settings),'-DaocBridgeExpectedMaster=0.35','-DaocBridgeExpectedEffects=0.65',
            '-AudioMixer','-unattended','-nosplash','-d3d11','-RenderOffscreen','-windowed','-ResX=1280','-ResY=720',
            '-abslog='+str(output/(name+'_engine.log'))]
        if not installed:command+=['-DaocBridgeOptionsArt='+art['candidate']]
        with (output/(name+'_stdout.log')).open('w',encoding='utf-8') as log:
            process=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=110,creationflags=subprocess.CREATE_NO_WINDOW)
        assert process.returncode==0,(name,process.returncode)
        report_path=Path(str(path)+'.native.json') if name=='selection' else path
        report=read(report_path);assert report['passed'] and not report['failures'],(name,report['failures'])
        assert report['checks']>={'options':17,'selection':15,'combat':14,'spell':15}[name]
        if name!='selection':assert report['pcm_consumed_bytes']>0
        reports[name]=report;print(name+' passed',flush=True)
    assert digest(normal)==normal_hash
    proof={'passed':True,'server_started':False,'installed_client':installed,'normal_binary_modified':False,'normal_sha256':normal_hash,
        'build_receipt_sha256':digest(root/'native_build.json'),'art_receipt_sha256':digest(root/'resources.json'),
        'reports':reports,'report_directory':str(output),'owner_volume_acceptance':False}
    (output/'verified.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
    return {'passed':True,'checks':{name:row['checks'] for name,row in reports.items()},'report_directory':str(output)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['workspace','engine']:parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--installed',action='store_true');args=parser.parse_args()
    print(json.dumps(verify(args.workspace.resolve(),args.engine.resolve(),args.installed)))
