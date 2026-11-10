"""Exercise actual native controls page/capture and isolated settings, without starting a server."""
import argparse,json,subprocess
from pathlib import Path
from datetime import datetime
from prepare_combined_expansion_data import digest
from verify_options_audio_native import read

def verify(workspace,engine,installed=False,lab_name="KeyConfigurationLab"):
    assert lab_name in ["KeyConfigurationLab","InterfaceKeysLab","DisplaySettingsLab","DisplaySettingsFixLab","GuildWindowLab","EmblemWindowLab","ItemHandoverLab","HoverDetailsLab","UIScaleLab","WindowRecoveryLab","PlayerVitalsLab","CompassLab","WorldClockLab","StealthLab","GroundTargetLab","SiegeWorldLab","PersonalTorchLab","OriginalControlsLab","KeyboardTurningLab","GroupTargetKeysLab","GroundObjectRuntimeLab","ChatReplyLab","InterfaceVisibilityLab","ItemShortcutsLab"]
    root=workspace/lab_name;build=read(root/'native_build.json')
    normal=workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    assert build['passed']
    if installed:
        from central_activation_receipts import verify_files
        assert verify_files(workspace)['item_shortcuts_installed' if lab_name=='ItemShortcutsLab' else 'interface_visibility_installed' if lab_name=='InterfaceVisibilityLab' else 'chat_reply_installed' if lab_name=='ChatReplyLab' else 'ground_objects_installed' if lab_name=='GroundObjectRuntimeLab' else 'group_target_keys_installed' if lab_name=='GroupTargetKeysLab' else 'keyboard_turning_installed' if lab_name=='KeyboardTurningLab' else 'weapon_sprint_installed' if lab_name=='OriginalControlsLab' else 'window_recovery_installed' if lab_name=='WindowRecoveryLab' else 'ui_scale_installed' if lab_name=='UIScaleLab' else 'hover_details_installed' if lab_name=='HoverDetailsLab' else 'item_handover_installed' if lab_name=='ItemHandoverLab' else 'emblem_window_installed' if lab_name=='EmblemWindowLab' else 'guild_window_installed' if lab_name=='GuildWindowLab' else 'display_settings_installed' if lab_name in ['DisplaySettingsLab','DisplaySettingsFixLab','GuildWindowLab','EmblemWindowLab','ItemHandoverLab','HoverDetailsLab','UIScaleLab','WindowRecoveryLab','PlayerVitalsLab','CompassLab','WorldClockLab','StealthLab','GroundTargetLab','SiegeWorldLab','PersonalTorchLab','OriginalControlsLab','KeyboardTurningLab','GroupTargetKeysLab','GroundObjectRuntimeLab','ChatReplyLab','InterfaceVisibilityLab','ItemShortcutsLab'] else 'interface_keys_installed' if lab_name=='InterfaceKeysLab' else 'key_configuration_installed'] and digest(normal)==build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll']
    else:assert digest(normal)==build['normal_binary_sha256']
    repo=Path(__file__).resolve().parents[3]
    source=repo/'source/ue5-bridge/UnrealPlugin/DAoCVisualBridge/Source'
    assert all(digest(source/p)==h for p,h in build['source_sha256'].items())
    project=Path(build['project'])
    assert all(digest(project.parent/'Plugins/DAoCVisualBridge/Binaries/Win64'/p)==h for p,h in build['binaries_sha256'].items())
    if installed:project=workspace/'Client/DAoCBridgeClient.uproject'
    output=root/('InstalledKeyAcceptance' if installed and lab_name in ['GroundTargetLab','SiegeWorldLab','PersonalTorchLab','OriginalControlsLab','KeyboardTurningLab','GroupTargetKeysLab','GroundObjectRuntimeLab','ChatReplyLab','InterfaceVisibilityLab','ItemShortcutsLab'] else 'KeyAcceptance' if lab_name in ['GroundTargetLab','SiegeWorldLab','PersonalTorchLab','OriginalControlsLab','KeyboardTurningLab','GroupTargetKeysLab','GroundObjectRuntimeLab','ChatReplyLab','InterfaceVisibilityLab','ItemShortcutsLab'] else 'InstalledControlsAcceptance' if installed else 'Acceptance')/datetime.now().strftime('%Y%m%d-%H%M%S-%f');output.mkdir(parents=True)
    report=output/'controls.json';settings=output/'camera.json';keys=output/'keybindings.ini'
    settings.write_text(json.dumps({'mouse_sensitivity':.25,'invert_mouse':False,'preserved_test_field':'retained'}))
    args=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),str(project),'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeReadOnly',
          '-DaocBridgeKeyConfigurationTest='+str(report),'-DaocBridgeControlsSettings='+str(settings),'-DaocBridgeKeyConfiguration='+str(keys),
          '-nosound','-unattended','-nosplash','-d3d11','-RenderOffscreen','-windowed','-ResX=1280','-ResY=720','-abslog='+str(output/'engine.log')]
    if lab_name in ['InterfaceKeysLab','DisplaySettingsLab','DisplaySettingsFixLab','GuildWindowLab','EmblemWindowLab','ItemHandoverLab','HoverDetailsLab','UIScaleLab','WindowRecoveryLab','PlayerVitalsLab','CompassLab','WorldClockLab','StealthLab','GroundTargetLab','SiegeWorldLab','PersonalTorchLab','OriginalControlsLab','KeyboardTurningLab','GroupTargetKeysLab','GroundObjectRuntimeLab','ChatReplyLab','InterfaceVisibilityLab','ItemShortcutsLab']:
        import shutil
        fixture=output/'fixture.json';shutil.copy2(workspace/'Reports/ui_integration/fixture.json',fixture);args.extend(['-DaocBridgeInterfaceKeysFixture='+str(fixture),'-DaocBridgeMovementBindingsMigrationTest']);keys.write_text('[KeyConfiguration]\nVersion=1\n[Bindings]\nmove_forward0=Q\n',encoding='utf-8')
    if lab_name in ['OriginalControlsLab','KeyboardTurningLab','GroupTargetKeysLab','GroundObjectRuntimeLab','ChatReplyLab','InterfaceVisibilityLab','ItemShortcutsLab']:args.append('-DaocBridgeWeaponSprintTest')
    if lab_name in ['KeyboardTurningLab','GroupTargetKeysLab','GroundObjectRuntimeLab','ChatReplyLab','InterfaceVisibilityLab','ItemShortcutsLab']:args.extend(['-DaocBridgeKeyboardTurnInputTest','-DaocBridgeAutoTargetTrackingTest'])
    if lab_name in ['GroupTargetKeysLab','GroundObjectRuntimeLab','ChatReplyLab','InterfaceVisibilityLab','ItemShortcutsLab']:args.append('-DaocBridgeGroupTargetKeysTest')
    if lab_name in ['GroundObjectRuntimeLab','ChatReplyLab','InterfaceVisibilityLab','ItemShortcutsLab']:args.extend(['-DaocBridgeGroundObjects','-DaocBridgeGroundObjectKeysTest'])
    if lab_name in ['ChatReplyLab','InterfaceVisibilityLab','ItemShortcutsLab']:args.append('-DaocBridgeChatReplyKeysTest')
    if lab_name in ['InterfaceVisibilityLab','ItemShortcutsLab']:args.append('-DaocBridgeInterfaceVisibilityTest')
    if lab_name=='ItemShortcutsLab':args.append('-DaocBridgeItemShortcutsTest')
    with (output/'stdout.log').open('w',encoding='utf-8') as log:
        result=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode==0 and report.exists(),str(output)
    data=read(report);assert data['passed'] and not data['failures'] and data['checks']>=(257 if lab_name in ['GuildWindowLab','EmblemWindowLab','ItemHandoverLab','HoverDetailsLab','UIScaleLab','WindowRecoveryLab','PlayerVitalsLab','CompassLab','WorldClockLab','StealthLab','GroundTargetLab','SiegeWorldLab','PersonalTorchLab','OriginalControlsLab','KeyboardTurningLab','GroupTargetKeysLab','GroundObjectRuntimeLab','ChatReplyLab','InterfaceVisibilityLab','ItemShortcutsLab'] else 256 if lab_name in ['InterfaceKeysLab','DisplaySettingsLab','DisplaySettingsFixLab','GuildWindowLab','EmblemWindowLab','ItemHandoverLab','HoverDetailsLab','UIScaleLab','WindowRecoveryLab','PlayerVitalsLab','CompassLab','WorldClockLab','StealthLab','GroundTargetLab','SiegeWorldLab','PersonalTorchLab','OriginalControlsLab','KeyboardTurningLab','GroupTargetKeysLab','GroundObjectRuntimeLab','ChatReplyLab','InterfaceVisibilityLab','ItemShortcutsLab'] else 51),data
    assert digest(normal)==(build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll'] if installed else build['normal_binary_sha256'])
    data.update(installed_client=installed,server_started=False,normal_installation_modified=False,build_receipt_sha256=digest(root/'native_build.json'),screenshot=str(report)+'.png')
    (output/'verified.json').write_text(json.dumps(data,indent=2))
    return dict(passed=True,checks=data['checks'],output=str(output))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['workspace','engine']:p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--installed',action='store_true');p.add_argument('--interface-keys',action='store_true');a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.engine.resolve(),a.installed,'InterfaceKeysLab' if a.interface_keys else 'KeyConfigurationLab')))
