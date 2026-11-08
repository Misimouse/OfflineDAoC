"""Private water candidate audio/UI regressions; water trajectory is checked separately."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import subprocess
from prepare_combined_expansion_data import digest
from verify_options_audio_native import read

def verify(workspace,engine,installed=False,lab_name="WaterMovementLab"):
    assert lab_name in ["WaterMovementLab","JumpLandingLab","MovementKeysLab","TargetTrackingLab","LiveRidingLab","KeyConfigurationLab","InterfaceKeysLab","DisplaySettingsLab","DisplaySettingsFixLab","GuildWindowLab","EmblemWindowLab","ItemHandoverLab","HoverDetailsLab","UIScaleLab","WindowRecoveryLab"]
    root=workspace/lab_name;build=read(root/'native_build.json');resource_path=workspace/'WaterMovementLab/resources.json';resources=read(resource_path)
    normal=workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    before=digest(normal);assert build['passed'] and resources['passed']
    if installed:
        from central_activation_receipts import verify_files
        assert verify_files(workspace)['window_recovery_installed' if lab_name=='WindowRecoveryLab' else 'ui_scale_installed' if lab_name=='UIScaleLab' else 'hover_details_installed' if lab_name=='HoverDetailsLab' else 'item_handover_installed' if lab_name=='ItemHandoverLab' else 'emblem_window_installed' if lab_name=='EmblemWindowLab' else 'guild_window_installed' if lab_name=='GuildWindowLab' else 'display_settings_installed' if lab_name in ['DisplaySettingsLab','DisplaySettingsFixLab','GuildWindowLab','EmblemWindowLab','ItemHandoverLab','HoverDetailsLab','UIScaleLab','WindowRecoveryLab'] else 'interface_keys_installed' if lab_name=='InterfaceKeysLab' else 'key_configuration_installed' if lab_name=='KeyConfigurationLab' else 'live_riding_installed' if lab_name=='LiveRidingLab' else 'target_tracking_installed' if lab_name=='TargetTrackingLab' else 'movement_keys_installed' if lab_name=='MovementKeysLab' else 'jump_landing_installed' if lab_name=='JumpLandingLab' else 'water_movement_installed'] and before==build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll']
    else:assert before==build['normal_binary_sha256']
    project=Path(build['project']);assert all(digest(project.parent/'Plugins/DAoCVisualBridge/Binaries/Win64'/p)==sha for p,sha in build['binaries_sha256'].items())
    if installed:project=workspace/'Client/DAoCBridgeClient.uproject'
    catalog=Path(resources['catalog']);assert digest(catalog)==resources['catalog_sha256']
    assert all(digest(Path(p))==sha for p,sha in resources['input_hashes'].items())
    output=root/('InstalledAcceptance' if installed else 'NativeAcceptance')/datetime.now().strftime('%Y%m%d-%H%M%S-%f');output.mkdir(parents=True);reports={}
    cases=[('server_sound','DaocBridgeServerSoundTest',40),('footstep','DaocBridgeFootstepTest',149),('door','DaocBridgeDoorAudioTest',15),('options','DaocBridgeOptionsAudioTest',17),('selection','DaocBridgeInteractionTest',15),('combat','DaocBridgeCombatAudioTest',14),('spell','DaocBridgeSpellAudioTest',15)]
    for name,flag,minimum in cases:
        path=output/(name+'.json');settings=output/(name+'.ini')
        settings.write_text('[Audio]\nMaster=0.35\nEffects=0.65\n' if name=='options' else '[Audio]\nMaster=0.03\nEffects=1\n' if name in ['footstep','server_sound'] else '[Audio]\nMaster=1\nEffects=1\n',encoding='utf-8')
        if name=='selection':path.write_text(json.dumps({'cases':[{'revision':1,'target':{'id':''},'talk':{},'merchant':{},'dialogs':[],'messages':[],'feedback':''}]}),encoding='utf-8')
        command=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),str(project),'/Engine/Maps/Entry','-game','-EnablePlugins=DAoCVisualBridge','-DaocBridge','-DaocBridgeReadOnly','-'+flag+'='+str(path),'-DaocBridgeAudioSettings='+str(settings),'-DaocBridgeExpectedMaster=0.35','-DaocBridgeExpectedEffects=0.65','-DaocBridgeWaterField='+str(catalog),'-DaocBridgeFootstepSoundCatalog='+str(workspace/'FootstepAudioLab/OriginalFootstepAudio_v01/sounds.json'),'-DaocBridgeCatalog='+str(workspace/'models.json'),'-AudioMixer','-unattended','-nosplash','-d3d11','-RenderOffscreen','-windowed','-ResX=1280','-ResY=720','-abslog='+str(output/(name+'_engine.log'))]
        if installed:command=[arg for arg in command if not arg.startswith(('-DaocBridgeFootstepSoundCatalog=','-DaocBridgeWaterField='))]
        with (output/(name+'_stdout.log')).open('w',encoding='utf-8') as log:
            process=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=150,creationflags=subprocess.CREATE_NO_WINDOW)
        assert process.returncode==0,(name,process.returncode)
        report=read(Path(str(path)+'.native.json') if name=='selection' else path)
        assert report['passed'] and not report['failures'] and report['checks']>=minimum,(name,report.get('failures'),report['checks'])
        if name!='selection':assert report['pcm_consumed_bytes']>0
        reports[name]=report;print(name+' passed',flush=True)
    assert digest(normal)==before
    proof={'passed':True,'reports':reports,'report_directory':str(output),'normal_binary_modified':False,'build_receipt_sha256':digest(root/'native_build.json'),'resources_receipt_sha256':digest(resource_path),'server_started':False,'owner_listening_accepted':False,'water_steps_implemented':True,'npc_steps_enabled':False,'surface_swimming_candidate':True}
    proof['installed_client']=installed
    (output/'verified.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
    return {'passed':True,'checks':{key:row['checks'] for key,row in reports.items()},'report_directory':str(output)}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['workspace','engine']:parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--installed',action='store_true')
    args=parser.parse_args();print(json.dumps(verify(args.workspace.resolve(),args.engine.resolve(),args.installed)))
