"""Actual private door PCM playback and existing native sound/UI regressions."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import subprocess
from prepare_combined_expansion_data import digest
from verify_options_audio_native import read


def verify(workspace,engine,installed=False):
    root=workspace/'DoorAudioLab';build=read(root/'native_build.json');resources=read(root/'resources.json')
    assert build['passed'] and resources['passed']
    normal=workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    before=digest(normal)
    if installed:
        from central_activation_receipts import verify_files
        assert verify_files(workspace)['door_audio_installed'] and before==build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll']
    else:assert before==build['normal_binary_sha256']
    project=Path(build['project'])
    assert all(digest(project.parent/'Plugins/DAoCVisualBridge/Binaries/Win64'/p)==sha for p,sha in build['binaries_sha256'].items())
    if installed:project=workspace/'Client/DAoCBridgeClient.uproject'
    catalog=root/'OriginalDoorAudio_v01/sounds.json'
    output=root/('InstalledAcceptance' if installed else 'NativeAcceptance')/datetime.now().strftime('%Y%m%d-%H%M%S-%f');output.mkdir(parents=True)
    reports={}
    for name,flag,minimum in [('door','DaocBridgeDoorAudioTest',15),('options','DaocBridgeOptionsAudioTest',17),('selection','DaocBridgeInteractionTest',15),('combat','DaocBridgeCombatAudioTest',14),('spell','DaocBridgeSpellAudioTest',15)]:
        path=output/(name+'.json');settings=output/(name+'.ini')
        settings.write_text('[Audio]\nMaster=0.35\nEffects=0.65\n' if name=='options' else '[Audio]\nMaster=1\nEffects=1\n',encoding='utf-8')
        if name=='selection':path.write_text(json.dumps({'cases':[{'revision':1,'target':{'id':''},'talk':{},'merchant':{},'dialogs':[],'messages':[],'feedback':''}]}),encoding='utf-8')
        command=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),str(project),'/Engine/Maps/Entry','-game','-EnablePlugins=DAoCVisualBridge','-DaocBridge','-DaocBridgeReadOnly','-'+flag+'='+str(path),'-DaocBridgeAudioSettings='+str(settings),'-DaocBridgeExpectedMaster=0.35','-DaocBridgeExpectedEffects=0.65','-DaocBridgeDoorSoundCatalog='+str(catalog),'-AudioMixer','-unattended','-nosplash','-d3d11','-RenderOffscreen','-windowed','-ResX=1280','-ResY=720','-abslog='+str(output/(name+'_engine.log'))]
        if installed:command=[arg for arg in command if not arg.startswith('-DaocBridgeDoorSoundCatalog=')]
        with (output/(name+'_stdout.log')).open('w',encoding='utf-8') as log:
            process=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=110,creationflags=subprocess.CREATE_NO_WINDOW)
        assert process.returncode==0,(name,process.returncode)
        report=read(Path(str(path)+'.native.json') if name=='selection' else path)
        assert report['passed'] and not report['failures'] and report['checks']>=minimum,(name,report)
        if name!='selection':assert report['pcm_consumed_bytes']>0
        reports[name]=report;print(name+' passed',flush=True)
    assert digest(normal)==before
    proof={'passed':True,'reports':reports,'report_directory':str(output),'server_started':False,'normal_binary_modified':False,'build_receipt_sha256':digest(root/'native_build.json'),'resource_receipt_sha256':digest(root/'resources.json'),'catalog_sha256':digest(catalog),'owner_listening_accepted':False}
    proof['installed_client']=installed
    (output/'verified.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
    return {'passed':True,'checks':{key:row['checks'] for key,row in reports.items()},'report_directory':str(output)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['workspace','engine']:parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--installed',action='store_true')
    args=parser.parse_args();print(json.dumps(verify(args.workspace.resolve(),args.engine.resolve(),args.installed)))
