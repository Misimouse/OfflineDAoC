"""Build the audio candidate privately; central editor/plugin binaries remain untouched."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

from prepare_combined_expansion_data import digest


def build(workspace, engine, lab_name='SpellAudioLab'):
    repo=Path(__file__).resolve().parents[3]
    assert lab_name in ['SpellAudioLab','CombatAudioLab','TargetSelectionLab','OptionsAudioLab','DoorAudioLab','FootstepAudioLab','ServerSoundAudioLab','WaterMovementLab','JumpLandingLab','MovementKeysLab']
    root=workspace/lab_name
    assert not (root/'installed.json').exists(), 'This delivery build is sealed; use a fresh candidate lab for its successor'
    host=root/'NativeHost'
    plugin=host/'Plugins/DAoCVisualBridge'
    plugin.mkdir(parents=True,exist_ok=True)
    central=workspace/'Client/Plugins/DAoCVisualBridge'
    normal_binary=central/'Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    normal_hash=digest(normal_binary)
    quote=lambda p:"'"+str(p).replace("'","''")+"'"
    for target,source in [(host/'Content',workspace.parent/'DAoC-Enhanced-Unreal/Content'),(plugin/'Content',central/'Content')]:
        if target.exists():assert target.is_junction() and target.resolve()==source.resolve()
        else:subprocess.run(['powershell.exe','-NoProfile','-Command','New-Item -ItemType Junction -Path '+quote(target)+' -Target '+quote(source)+' | Out-Null'],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
    shutil.copy2(central/'DAoCVisualBridge.uplugin',plugin/'DAoCVisualBridge.uplugin')
    project=host/'SpellAudioHost.uproject'
    project.write_text(json.dumps({'FileVersion':3,'EngineAssociation':'5.8','Plugins':[{'Name':'DAoCVisualBridge','Enabled':True}]}),encoding='utf-8')
    build_host=workspace/'ExpansionRaceLab/StarterNativeBuild/HostProject'
    build_plugin=build_host/'Plugins/DAoCVisualBridge'
    assert build_plugin.resolve().is_relative_to(workspace/'ExpansionRaceLab')
    source=repo/'source/ue5-bridge/UnrealPlugin/DAoCVisualBridge/Source'
    hashes={str(p.relative_to(source)):digest(p) for p in source.rglob('*') if p.is_file()}
    shutil.copytree(source,build_plugin/'Source',dirs_exist_ok=True)
    command=[str(engine/'Build/BatchFiles/Build.bat'),'UnrealEditor','Win64','Development',
        '-Project='+str(build_host/'HostProject.uproject'),'-Plugin='+str(build_plugin/'DAoCVisualBridge.uplugin'),
        '-WaitMutex','-NoHotReload','-DisableLiveCoding']
    with (root/'native_build.log').open('w',encoding='utf-8') as log:
        result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode==0,'See SpellAudioLab/native_build.log'
    assert all(digest(source/path)==sha and digest(build_plugin/'Source'/path)==sha for path,sha in hashes.items())
    binary=plugin/'Binaries/Win64'
    binary.mkdir(parents=True,exist_ok=True)
    for name in ['UnrealEditor-DAoCVisualBridge.dll','UnrealEditor.modules']:shutil.copy2(build_plugin/'Binaries/Win64'/name,binary/name)
    assert digest(normal_binary)==normal_hash
    receipt={'passed':True,'normal_binary_modified':False,'normal_binary_sha256':normal_hash,'project':str(project),
        'source_sha256':hashes,'binaries_sha256':{name:digest(binary/name) for name in ['UnrealEditor-DAoCVisualBridge.dll','UnrealEditor.modules']}}
    (root/'native_build.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    return {k:v for k,v in receipt.items() if k not in ['source_sha256','binaries_sha256']}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['workspace','engine']:parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--combat-candidate',action='store_true')
    parser.add_argument('--target-selection-candidate',action='store_true')
    parser.add_argument('--options-audio-candidate',action='store_true')
    parser.add_argument('--door-audio-candidate',action='store_true')
    parser.add_argument('--footstep-audio-candidate',action='store_true')
    parser.add_argument('--server-sound-audio-candidate',action='store_true')
    parser.add_argument('--water-movement-candidate',action='store_true')
    parser.add_argument('--jump-landing-candidate',action='store_true')
    parser.add_argument('--movement-keys-candidate',action='store_true')
    args=parser.parse_args()
    assert sum([args.combat_candidate,args.target_selection_candidate,args.options_audio_candidate,args.door_audio_candidate,args.footstep_audio_candidate,args.server_sound_audio_candidate,args.water_movement_candidate,args.jump_landing_candidate,args.movement_keys_candidate])<=1
    print(json.dumps(build(args.workspace.resolve(),args.engine.resolve(),'MovementKeysLab' if args.movement_keys_candidate else 'JumpLandingLab' if args.jump_landing_candidate else 'WaterMovementLab' if args.water_movement_candidate else 'ServerSoundAudioLab' if args.server_sound_audio_candidate else 'FootstepAudioLab' if args.footstep_audio_candidate else 'DoorAudioLab' if args.door_audio_candidate else 'OptionsAudioLab' if args.options_audio_candidate else 'TargetSelectionLab' if args.target_selection_candidate else 'CombatAudioLab' if args.combat_candidate else 'SpellAudioLab')))
