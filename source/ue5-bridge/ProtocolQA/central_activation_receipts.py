"""Verify central file receipts, allowing only the explicitly recorded rules successor."""
import json
from pathlib import Path

from prepare_combined_expansion_data import digest

OPTIONS_TARGETS=['Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll','Binaries/Win64/UnrealEditor.modules',
    'Source/DAoCVisualBridge/Public/DAoCBridgeSubsystem.h','Source/DAoCVisualBridge/Private/DAoCBridgeSubsystem.cpp',
    'Source/DAoCVisualBridge/Private/DAoCBridgeCameraControls.cpp','Source/DAoCVisualBridge/Private/DAoCBridgeWorldPointer.cpp',
    'Source/DAoCVisualBridge/Private/DAoCBridgeSpellAudio.cpp','Source/DAoCVisualBridge/Private/DAoCBridgeOptions.cpp',
    'Source/DAoCVisualBridge/Private/DAoCBridgeOptionsAcceptance.cpp','Content/ClassicUI/options.png']
DOOR_NATIVE_TARGETS=['Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll','Binaries/Win64/UnrealEditor.modules',
    'Source/DAoCVisualBridge/Public/DAoCBridgeSubsystem.h','Source/DAoCVisualBridge/Private/DAoCBridgeSpellAudio.cpp',
    'Source/DAoCVisualBridge/Private/DAoCBridgeSpellAudioAcceptance.cpp','Source/DAoCVisualBridge/Private/DAoCBridgeDoorAudioAcceptance.cpp']
FOOTSTEP_NATIVE_TARGETS=['Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll','Binaries/Win64/UnrealEditor.modules',
    'Source/DAoCVisualBridge/Public/DAoCBridgeSubsystem.h','Source/DAoCVisualBridge/Private/DAoCBridgeSubsystem.cpp',
    'Source/DAoCVisualBridge/Private/DAoCBridgeSpellAudio.cpp','Source/DAoCVisualBridge/Private/DAoCBridgeSpellAudioAcceptance.cpp',
    'Source/DAoCVisualBridge/Private/DAoCBridgeFootsteps.cpp']


SERVER_SOUND_NATIVE_TARGETS=['Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll','Binaries/Win64/UnrealEditor.modules',
    'Source/DAoCVisualBridge/Public/DAoCBridgeSubsystem.h','Source/DAoCVisualBridge/Private/DAoCBridgeSpellAudio.cpp',
    'Source/DAoCVisualBridge/Private/DAoCBridgeSpellAudioAcceptance.cpp','Source/DAoCVisualBridge/Private/DAoCBridgeServerSoundAcceptance.cpp']


WATER_NATIVE_TARGETS=['Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll','Binaries/Win64/UnrealEditor.modules',
    'Source/DAoCVisualBridge/Public/DAoCBridgeSubsystem.h','Source/DAoCVisualBridge/Private/DAoCBridgeSubsystem.cpp',
    'Source/DAoCVisualBridge/Private/DAoCBridgeAnimation.cpp','Source/DAoCVisualBridge/Private/DAoCBridgeFootsteps.cpp',
    'Source/DAoCVisualBridge/Private/DAoCBridgeSpellAudio.cpp','Source/DAoCVisualBridge/Private/DAoCBridgeSpellAudioAcceptance.cpp',
    'Source/DAoCVisualBridge/Private/DAoCBridgeWaterData.h','Source/DAoCVisualBridge/Private/DAoCBridgeWaterMovement.cpp',
    'Source/DAoCVisualBridge/Private/DAoCBridgeWaterAcceptance.cpp']


def verify_files(workspace):
    base=workspace/'ExpansionRaceLab/CentralDelivery'
    original_path=base/'MinotaurActivation/installed.json'
    original=json.loads(original_path.read_text())
    assert original['installed'] and original['only_race_enabled']==21
    successor_path=base/'SpellClassActivation/installed.json'
    successor=json.loads(successor_path.read_text()) if successor_path.exists() else None
    if successor:
        assert successor['installed'] and successor['phase']=='complete'
        assert successor['minotaur_receipt_sha256']==digest(original_path)
        assert successor['classes_enabled']==[39,58] and not successor['races_changed']
        plan_path=base/'SpellClassActivation/plan.json'
        assert successor['plan_sha256']==digest(plan_path)
        plan=json.loads(plan_path.read_text())
        assert successor['rules_after_sha256']==plan['rules_after_sha256']
    shar_path=base/'SharActivation/installed.json'
    shar=json.loads(shar_path.read_text()) if shar_path.exists() else None
    if shar and not shar.get('installed'):shar=None
    if shar:
        assert successor and shar['phase']=='complete' and shar['only_race_enabled']==18
        assert shar['predecessor_receipt_sha256']==digest(successor_path)
        assert shar['rules_before_sha256']==successor['rules_after_sha256'] and shar['rules_target']==successor['rules_target']
        shar_plan_path=base/'SharActivation/plan.json';assert shar['plan_sha256']==digest(shar_plan_path)
        shar_plan=json.loads(shar_plan_path.read_text())
        assert shar['rules_after_sha256']==shar_plan['rules_after_sha256']
    combat_path=workspace/'CombatAudioLab/installed.json'
    combat=json.loads(combat_path.read_text()) if combat_path.exists() else None
    if combat and not combat.get('installed'):combat=None
    replacements={}
    mode_path=workspace/'WeaponModeAudioLab/installed.json'
    mode=json.loads(mode_path.read_text()) if mode_path.exists() else None
    if mode and not mode.get('installed'):mode=None
    mode_replacements={}
    selection_path=workspace/'TargetSelectionLab/installed.json'
    selection=json.loads(selection_path.read_text()) if selection_path.exists() else None
    if selection and not selection.get('installed'):selection=None
    selection_replacements={}
    options_path=workspace/'OptionsAudioLab/installed.json'
    options=json.loads(options_path.read_text()) if options_path.exists() else None
    if options and not options.get('installed'):options=None
    options_replacements={}
    door_path=workspace/'DoorAudioLab/installed.json'
    door=json.loads(door_path.read_text()) if door_path.exists() else None
    if door and not door.get('installed'):door=None
    door_replacements={}
    foot_path=workspace/'FootstepAudioLab/installed.json'
    foot=json.loads(foot_path.read_text()) if foot_path.exists() else None
    if foot and not foot.get('installed'):foot=None
    foot_replacements={}
    server_path=workspace/'ServerSoundAudioLab/installed.json'
    server=json.loads(server_path.read_text()) if server_path.exists() else None
    if server and not server.get('installed'):server=None
    server_replacements={}
    water_path=workspace/'WaterMovementLab/installed.json'
    water=json.loads(water_path.read_text()) if water_path.exists() else None
    if water and not water.get('installed'):water=None
    water_replacements={}
    if water:
        assert server and water['phase']=='complete' and not water['database_modified']
        assert water['predecessor_receipt_sha256']==digest(server_path) and water['native_before_sha256']==server['native_after_sha256']
        resource_path=workspace/'WaterMovementLab/resources.json';assert water['resources_receipt_sha256']==digest(resource_path)
        resource=json.loads(resource_path.read_text());assert Path(resource['catalog'])==workspace/'WaterMovementLab/water_field.json'
        plugin=workspace/'Client/Plugins/DAoCVisualBridge'
        catalog=str(plugin/'Content/WaterMovement_v01/water_field.json')
        expected={str(plugin/p) for p in WATER_NATIVE_TARGETS}|{str(workspace/'Godot'/p) for p in ['live_gateway.gd','movement_flags_state.gd']}|{catalog}
        water_replacements={row['target']:row for row in water['files']}
        assert len(water['files'])==len(water_replacements)==len(expected) and set(water_replacements)==expected
        assert water_replacements[catalog]['after_sha256']==resource['catalog_sha256']
        new_names=['DAoCBridgeWaterData.h','DAoCBridgeWaterMovement.cpp','DAoCBridgeWaterAcceptance.cpp','movement_flags_state.gd','water_field.json']
        for row in water['files']:
            if Path(row['target']).name in new_names:assert row['before_sha256'] is None
            assert digest(Path(row['target']))==row['after_sha256']
        binary=water_replacements[str(plugin/'Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll')]
        assert binary['before_sha256']==water['native_before_sha256'] and binary['after_sha256']==water['native_after_sha256']
    def latest_water(row,expected):
        changed=water_replacements.get(row['target'])
        if changed:assert changed['before_sha256']==expected;return changed['after_sha256']
        return expected
    if server:
        assert foot and server['phase']=='complete' and not server['database_modified']
        assert server['predecessor_receipt_sha256']==digest(foot_path) and server['native_before_sha256']==foot['native_after_sha256']
        resource_path=workspace/'ServerSoundAudioLab/resources.json';assert server['resources_receipt_sha256']==digest(resource_path)
        resource=json.loads(resource_path.read_text());catalog=Path(resource['catalog']);library=catalog.parent
        assert library==workspace/'ServerSoundAudioLab/OriginalServerSoundAudio_v01' and len(resource['files'])==28
        plugin=workspace/'Client/Plugins/DAoCVisualBridge'
        sound_targets={str(plugin/'Content/OriginalServerSoundAudio_v01'/Path(p).relative_to(library)) for p in list(resource['files'])+[str(catalog)]}
        expected={str(plugin/p) for p in SERVER_SOUND_NATIVE_TARGETS}|{str(workspace/'Godot'/p) for p in ['live_gateway.gd','visual_bridge.gd','server_sound_state.gd']}|sound_targets
        server_replacements={row['target']:row for row in server['files']}
        assert len(server['files'])==len(server_replacements)==len(expected) and set(server_replacements)==expected
        for origin,sha in {**resource['files'],str(catalog):resource['catalog_sha256']}.items():
            target=str(plugin/'Content/OriginalServerSoundAudio_v01'/Path(origin).relative_to(library));assert server_replacements[target]['after_sha256']==sha
        for target in sound_targets|{str(workspace/'Godot/server_sound_state.gd'),str(plugin/'Source/DAoCVisualBridge/Private/DAoCBridgeServerSoundAcceptance.cpp')}:assert server_replacements[target]['before_sha256'] is None
        binary=server_replacements[str(plugin/'Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll')]
        assert binary['before_sha256']==server['native_before_sha256'] and binary['after_sha256']==server['native_after_sha256']
        for row in server['files']:assert digest(Path(row['target']))==latest_water(row,row['after_sha256'])
    def latest_server(row,expected):
        changed=server_replacements.get(row['target'])
        if changed:assert changed['before_sha256']==expected;expected=changed['after_sha256']
        return latest_water(row,expected)
    if foot:
        assert door and foot['phase']=='complete' and not foot['database_modified']
        assert foot['predecessor_receipt_sha256']==digest(door_path) and foot['native_before_sha256']==door['native_after_sha256']
        resource_path=workspace/'FootstepAudioLab/resources.json';assert foot['resources_receipt_sha256']==digest(resource_path)
        resource=json.loads(resource_path.read_text());catalog=Path(resource['catalog']);library=catalog.parent
        assert library==workspace/'FootstepAudioLab/OriginalFootstepAudio_v01' and len(resource['files'])==16
        plugin=workspace/'Client/Plugins/DAoCVisualBridge'
        sound_targets={str(plugin/'Content/OriginalFootstepAudio_v01'/Path(p).relative_to(library)) for p in list(resource['files'])+[str(catalog)]}
        expected={str(plugin/p) for p in FOOTSTEP_NATIVE_TARGETS}|sound_targets
        foot_replacements={row['target']:row for row in foot['files']}
        assert len(foot['files'])==len(foot_replacements)==len(expected) and set(foot_replacements)==expected
        for origin,sha in {**resource['files'],str(catalog):resource['catalog_sha256']}.items():
            target=str(plugin/'Content/OriginalFootstepAudio_v01'/Path(origin).relative_to(library));assert foot_replacements[target]['after_sha256']==sha
        for target in sound_targets|{str(plugin/'Source/DAoCVisualBridge/Private/DAoCBridgeFootsteps.cpp')}:assert foot_replacements[target]['before_sha256'] is None
        binary=foot_replacements[str(plugin/'Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll')]
        assert binary['before_sha256']==foot['native_before_sha256'] and binary['after_sha256']==foot['native_after_sha256']
        for row in foot['files']:assert digest(Path(row['target']))==latest_server(row,row['after_sha256'])
    def latest_foot(row,expected):
        changed=foot_replacements.get(row['target'])
        if changed:assert changed['before_sha256']==expected;expected=changed['after_sha256']
        return latest_server(row,expected)
    if door:
        assert options and mode and door['phase']=='complete' and not door['database_modified']
        assert door['predecessor_receipt_sha256']==digest(options_path) and door['gateway_predecessor_receipt_sha256']==digest(mode_path)
        assert door['native_before_sha256']==options['native_after_sha256']
        resources_path=workspace/'DoorAudioLab/resources.json';assert door['resources_receipt_sha256']==digest(resources_path)
        resources=json.loads(resources_path.read_text());catalog=Path(resources['catalog']);library=catalog.parent
        assert library==workspace/'DoorAudioLab/OriginalDoorAudio_v01' and len(resources['files'])==25
        plugin=workspace/'Client/Plugins/DAoCVisualBridge'
        sound_targets={str(plugin/'Content/OriginalDoorAudio_v01'/Path(p).relative_to(library)) for p in list(resources['files'])+[str(catalog)]}
        expected={str(plugin/p) for p in DOOR_NATIVE_TARGETS}|{str(workspace/'Godot'/p) for p in ['live_gateway.gd','door_audio_state.gd']}|sound_targets
        door_replacements={row['target']:row for row in door['files']}
        assert len(door['files'])==len(door_replacements)==len(expected) and set(door_replacements)==expected
        for origin,sha in {**resources['files'],str(catalog):resources['catalog_sha256']}.items():
            target=str(plugin/'Content/OriginalDoorAudio_v01'/Path(origin).relative_to(library))
            assert door_replacements[target]['after_sha256']==sha
        new_targets=sound_targets|{str(workspace/'Godot/door_audio_state.gd'),str(plugin/'Source/DAoCVisualBridge/Private/DAoCBridgeDoorAudioAcceptance.cpp')}
        for target in new_targets:assert door_replacements[target]['before_sha256'] is None
        binary=door_replacements[str(plugin/'Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll')]
        assert binary['before_sha256']==door['native_before_sha256'] and binary['after_sha256']==door['native_after_sha256']
        for row in door['files']:assert digest(Path(row['target']))==latest_foot(row,row['after_sha256'])
    def latest_door(row,expected):
        changed=door_replacements.get(row['target'])
        if changed:assert changed['before_sha256']==expected;expected=changed['after_sha256']
        return latest_foot(row,expected)
    if options:
        assert selection and options['phase']=='complete' and not options['database_modified']
        assert options['predecessor_receipt_sha256']==digest(selection_path)
        assert options['native_before_sha256']==selection['native_after_sha256']
        plugin=workspace/'Client/Plugins/DAoCVisualBridge'
        options_replacements={row['target']:row for row in options['files']}
        assert len(options['files'])==len(options_replacements)==len(OPTIONS_TARGETS)
        assert set(options_replacements)=={str(plugin/p) for p in OPTIONS_TARGETS}
        for name in ['Source/DAoCVisualBridge/Private/DAoCBridgeOptions.cpp','Source/DAoCVisualBridge/Private/DAoCBridgeOptionsAcceptance.cpp','Content/ClassicUI/options.png']:
            assert options_replacements[str(plugin/name)]['before_sha256'] is None
        binary=options_replacements[str(plugin/'Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll')]
        assert binary['before_sha256']==options['native_before_sha256'] and binary['after_sha256']==options['native_after_sha256']
        for row in options['files']:assert digest(Path(row['target']))==latest_door(row,row['after_sha256'])
    if selection:
        assert mode and combat and selection['phase']=='complete' and not selection['database_modified']
        assert selection['predecessor_receipt_sha256']==digest(mode_path)
        assert selection['native_before_sha256']==mode['native_sha256']==combat['native_after_sha256']
        plugin=workspace/'Client/Plugins/DAoCVisualBridge'
        expected={str(plugin/p) for p in ['Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll','Binaries/Win64/UnrealEditor.modules',
            'Source/DAoCVisualBridge/Public/DAoCBridgeSubsystem.h','Source/DAoCVisualBridge/Private/DAoCBridgeInteraction.cpp','Source/DAoCVisualBridge/Private/DAoCBridgeInteractionAcceptance.cpp']}
        selection_replacements={row['target']:row for row in selection['files']}
        assert len(selection['files'])==len(selection_replacements)==5 and set(selection_replacements)==expected
        binary=selection_replacements[str(plugin/'Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll')]
        assert binary['before_sha256']==selection['native_before_sha256'] and binary['after_sha256']==selection['native_after_sha256']
        for row in selection['files']:
            latest=options_replacements.get(row['target'])
            if latest:assert latest['before_sha256']==row['after_sha256']
            assert digest(Path(row['target']))==latest_door(row,latest['after_sha256'] if latest else row['after_sha256'])
    if mode:
        assert combat and mode['phase']=='complete' and not mode['database_modified']
        assert mode['predecessor_receipt_sha256']==digest(combat_path)
        assert mode['native_sha256']==combat['native_after_sha256']
        mode_replacements={row['target']:row for row in mode['files']}
        assert len(mode['files'])==len(mode_replacements)==2 and set(mode_replacements)=={str(workspace/'Godot/live_gateway.gd'),str(workspace/'Godot/weapon_mode_audio_state.gd')}
        assert mode_replacements[str(workspace/'Godot/weapon_mode_audio_state.gd')]['before_sha256'] is None
        for row in mode['files']:assert digest(Path(row['target']))==latest_door(row,row['after_sha256'])
    if combat:
        assert combat['phase']=='complete' and not combat['database_modified']
        assert combat['minotaur_receipt_sha256']==digest(original_path)
        audio_path=workspace/'SpellAudioLab/installed.json'
        assert combat['spell_audio_receipt_sha256']==digest(audio_path)
        audio=json.loads(audio_path.read_text())
        assert audio['installed'] and audio['phase']=='complete'
        assert combat['native_before_sha256']==audio['normal_native_sha256']
        replacements={row['target']:row for row in combat['files']}
        assert len(replacements)==len(combat['files'])
        native_target=str(workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll')
        assert replacements[native_target]['before_sha256']==combat['native_before_sha256']
        assert replacements[native_target]['after_sha256']==combat['native_after_sha256']
        for row in combat['files']:
            middle=selection_replacements.get(row['target']) or mode_replacements.get(row['target'])
            if middle:assert middle['before_sha256']==row['after_sha256']
            latest=options_replacements.get(row['target'])
            if latest:assert latest['before_sha256']==(middle['after_sha256'] if middle else row['after_sha256'])
            latest=latest or middle
            assert digest(Path(row['target']))==latest_door(row,latest['after_sha256'] if latest else row['after_sha256'])
        for row in audio['files']:
            changed=replacements.get(row['target'])
            if changed:assert changed['before_sha256']==row['after_sha256']
            expected=changed['after_sha256'] if changed else row['after_sha256']
            latest=selection_replacements.get(row['target'])
            if latest:assert latest['before_sha256']==expected;expected=latest['after_sha256']
            latest=options_replacements.get(row['target'])
            if latest:assert latest['before_sha256']==expected;expected=latest['after_sha256']
            assert digest(Path(row['target']))==latest_door(row,expected)
    replaced=0
    for row in original['files']:
        path=Path(row['target'])
        expected=row['after_sha256']
        if successor and str(path)==successor['rules_target']:
            assert expected==successor['rules_before_sha256']
            expected=successor['rules_after_sha256']
            replaced+=1
            if shar:expected=shar['rules_after_sha256']
        if str(path) in replacements:
            changed=replacements[str(path)]
            assert changed['before_sha256']==expected
            expected=changed['after_sha256']
        if str(path) in mode_replacements:
            changed=mode_replacements[str(path)]
            assert changed['before_sha256']==expected
            expected=changed['after_sha256']
        assert digest(path)==latest_door(row,expected), ('Installed central file changed',str(path))
    assert not successor or replaced==1
    if combat:
        changed_original=[row for row in original['files'] if row['target'] in replacements]
        assert len(changed_original)==1 and Path(changed_original[0]['target'])==workspace/'Godot/live_gateway.gd'
    return {'passed':True,'minotaur_installed':True,'spellclasses_installed':bool(successor),'shar_installed':bool(shar),'combat_audio_installed':bool(combat),'weapon_mode_audio_installed':bool(mode),'target_selection_installed':bool(selection),'options_audio_installed':bool(options),'door_audio_installed':bool(door),'footstep_audio_installed':bool(foot),'server_sound_audio_installed':bool(server),'water_movement_installed':bool(water),'verified_files':len(original['files'])}
