"""Synthetic successor-receipt checks; no owner files or databases are touched."""
import argparse
import json
from pathlib import Path
import tempfile
from central_activation_receipts import verify_files, OPTIONS_TARGETS, DOOR_NATIVE_TARGETS, FOOTSTEP_NATIVE_TARGETS, SERVER_SOUND_NATIVE_TARGETS, WATER_NATIVE_TARGETS, JUMP_NATIVE_TARGETS, MOVEMENT_KEYS_NATIVE_TARGETS,TARGET_TRACKING_NATIVE_TARGETS,LIVE_RIDING_NATIVE_TARGETS,LIVE_RIDING_GODOT_TARGETS,LIVE_RIDING_NEW_NAMES,KEY_CONFIGURATION_NATIVE_TARGETS,KEY_CONFIGURATION_NEW_NAMES,INTERFACE_KEYS_NATIVE_TARGETS
from prepare_combined_expansion_data import digest


from central_activation_receipts import DISPLAY_NATIVE_TARGETS,DISPLAY_NEW_NAMES,GUILD_NATIVE_TARGETS,GUILD_GODOT_TARGETS,GUILD_NEW_NAMES,EMBLEM_NATIVE_TARGETS,EMBLEM_GODOT_TARGETS,EMBLEM_NEW_NAMES,EMBLEM_UI_TARGETS,HANDOVER_NATIVE_TARGETS,HANDOVER_GODOT_TARGETS,HANDOVER_NEW_NAMES,HOVER_NATIVE_TARGETS,HOVER_GODOT_TARGETS,HOVER_NEW_NAMES

def put(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value),encoding='utf-8')


def verify(workspace):
    root=workspace/'CombatAudioLab/SyntheticReceiptTests'
    root.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root,prefix='case_') as name:
        w=Path(name).resolve()
        assert w.is_relative_to(root.resolve())
        gateway=w/'Godot/live_gateway.gd';gateway.parent.mkdir();gateway.write_text('old gateway')
        old_gateway=digest(gateway)
        original=w/'ExpansionRaceLab/CentralDelivery/MinotaurActivation/installed.json'
        server_rows=[]
        for folder in [w/'runtime/server',w/'runtime/server/lib',w/'runtime/server/win-x64']:
            folder.mkdir(parents=True,exist_ok=True)
            for name in ['GameServer.dll','CoreBase.dll','CoreDatabase.dll']:
                target=folder/name;target.write_bytes(b'original synthetic server');server_rows.append(dict(target=str(target),after_sha256=digest(target)))
        put(original,{'installed':True,'only_race_enabled':21,'files':[{'target':str(gateway),'after_sha256':old_gateway}]+server_rows})
        binary=w/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
        binary.parent.mkdir(parents=True);binary.write_bytes(b'old synthetic DLL');old_binary=digest(binary)
        wave=w/'Client/Plugins/DAoCVisualBridge/Content/OriginalAudio_v01/files/one.wav'
        wave.parent.mkdir(parents=True);wave.write_bytes(b'unchanged synthetic sound')
        audio_path=w/'SpellAudioLab/installed.json'
        put(audio_path,{'installed':True,'phase':'complete','normal_native_sha256':old_binary,
            'files':[{'target':str(binary),'after_sha256':old_binary},{'target':str(wave),'after_sha256':digest(wave)}]})
        binary.write_bytes(b'new synthetic DLL');gateway.write_text('new gateway')
        path=w/'CombatAudioLab/installed.json'
        receipt={'installed':True,'phase':'complete','database_modified':False,'minotaur_receipt_sha256':digest(original),
            'spell_audio_receipt_sha256':digest(audio_path),'native_before_sha256':old_binary,'native_after_sha256':digest(binary),
            'files':[{'target':str(binary),'before_sha256':old_binary,'after_sha256':digest(binary)},
                     {'target':str(gateway),'before_sha256':old_gateway,'after_sha256':digest(gateway)}]}
        put(path,receipt)
        assert verify_files(w)['combat_audio_installed']
        checks=1
        def rejected():
            try:verify_files(w)
            except AssertionError:return
            raise AssertionError('Broken receipt chain was accepted')
        before=wave.read_bytes();wave.write_bytes(b'changed original sound');rejected();wave.write_bytes(before);checks+=1
        receipt['files'][1]['before_sha256']='0'*64;put(path,receipt);rejected();checks+=1
        receipt['files'][1]['before_sha256']=old_gateway
        receipt['native_after_sha256']='0'*64;put(path,receipt);rejected();checks+=1
        receipt['native_after_sha256']=digest(binary)
        receipt['spell_audio_receipt_sha256']='0'*64;put(path,receipt);rejected();checks+=1
        receipt['spell_audio_receipt_sha256']=digest(audio_path);put(path,receipt)
        gateway_before=digest(gateway)
        gateway.write_text('newest gateway')
        trigger=w/'Godot/weapon_mode_audio_state.gd';trigger.write_text('synthetic trigger')
        mode_path=w/'WeaponModeAudioLab/installed.json'
        mode={'installed':True,'phase':'complete','database_modified':False,'native_sha256':digest(binary),
            'predecessor_receipt_sha256':digest(path),'files':[
                {'target':str(gateway),'before_sha256':gateway_before,'after_sha256':digest(gateway)},
                {'target':str(trigger),'before_sha256':None,'after_sha256':digest(trigger)}]}
        put(mode_path,mode)
        assert verify_files(w)['weapon_mode_audio_installed'];checks+=1
        mode['files'][0]['before_sha256']='0'*64;put(mode_path,mode);rejected();checks+=1
        mode['files'][0]['before_sha256']=gateway_before
        mode['native_sha256']='0'*64;put(mode_path,mode);rejected();checks+=1
        mode['native_sha256']=digest(binary);put(mode_path,mode)
        trigger.write_text('tampered trigger');rejected();trigger.write_text('synthetic trigger');checks+=1
        wave.write_bytes(b'changed original with successor');rejected();checks+=1
        wave.write_bytes(before)
        plugin=w/'Client/Plugins/DAoCVisualBridge'
        selection_rows=[]
        for relative in ['Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll','Binaries/Win64/UnrealEditor.modules',
            'Source/DAoCVisualBridge/Public/DAoCBridgeSubsystem.h','Source/DAoCVisualBridge/Private/DAoCBridgeInteraction.cpp','Source/DAoCVisualBridge/Private/DAoCBridgeInteractionAcceptance.cpp']:
            target=plugin/relative;target.parent.mkdir(parents=True,exist_ok=True)
            if not target.exists():target.write_bytes(b'old synthetic source')
            previous=digest(target);target.write_bytes(b'new synthetic selection '+relative.encode())
            selection_rows.append({'target':str(target),'before_sha256':previous,'after_sha256':digest(target)})
        selection_path=w/'TargetSelectionLab/installed.json'
        selection={'installed':True,'phase':'complete','database_modified':False,'predecessor_receipt_sha256':digest(mode_path),
            'native_before_sha256':mode['native_sha256'],'native_after_sha256':digest(binary),'files':selection_rows}
        put(selection_path,selection);assert verify_files(w)['target_selection_installed'];checks+=1
        selection['predecessor_receipt_sha256']='0'*64;put(selection_path,selection);rejected();checks+=1
        selection['predecessor_receipt_sha256']=digest(mode_path)
        selection['files'][0]['before_sha256']='0'*64;put(selection_path,selection);rejected();checks+=1
        selection['files'][0]['before_sha256']=selection['native_before_sha256'];put(selection_path,selection)
        binary.write_bytes(b'tampered installed selection');rejected();checks+=1
        binary.write_bytes(b'new synthetic selection Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll')
        previous_native=digest(binary);option_rows=[]
        new_names={'Source/DAoCVisualBridge/Private/DAoCBridgeOptions.cpp','Source/DAoCVisualBridge/Private/DAoCBridgeOptionsAcceptance.cpp','Content/ClassicUI/options.png'}
        for name in OPTIONS_TARGETS:
            target=plugin/name;target.parent.mkdir(parents=True,exist_ok=True)
            if not target.exists() and name not in new_names:target.write_bytes(b'old options predecessor')
            previous=digest(target) if target.exists() else None
            target.write_bytes(b'new synthetic options '+name.encode())
            option_rows.append({'target':str(target),'before_sha256':previous,'after_sha256':digest(target)})
        options_path=w/'OptionsAudioLab/installed.json';options={'installed':True,'phase':'complete','database_modified':False,
            'predecessor_receipt_sha256':digest(selection_path),'native_before_sha256':previous_native,'native_after_sha256':digest(binary),'files':option_rows}
        put(options_path,options);assert verify_files(w)['options_audio_installed'];checks+=1
        options['predecessor_receipt_sha256']='0'*64;put(options_path,options);rejected();checks+=1
        options['predecessor_receipt_sha256']=digest(selection_path);options['files'][0]['before_sha256']='0'*64;put(options_path,options);rejected();checks+=1
        options['files'][0]['before_sha256']=previous_native;put(options_path,options)
        wave.write_bytes(b'tampered old wave after options');rejected();checks+=1
        wave.write_bytes(before)
        library=w/'DoorAudioLab/OriginalDoorAudio_v01';library.mkdir(parents=True)
        files={}
        for i in range(25):
            p=library/('files/'+str(i)+'.wav');p.parent.mkdir(exist_ok=True);p.write_bytes(b'original door '+str(i).encode());files[str(p)]=digest(p)
        catalog=library/'sounds.json';catalog.write_text('synthetic original door catalog')
        resources_path=w/'DoorAudioLab/resources.json';put(resources_path,{'catalog':str(catalog),'catalog_sha256':digest(catalog),'files':files})
        door_rows=[];previous_native=digest(binary)
        targets=[(plugin/name) for name in DOOR_NATIVE_TARGETS]+[gateway,w/'Godot/door_audio_state.gd']
        targets += [plugin/'Content/OriginalDoorAudio_v01'/Path(p).relative_to(library) for p in list(files)+[str(catalog)]]
        new_native=plugin/'Source/DAoCVisualBridge/Private/DAoCBridgeDoorAudioAcceptance.cpp'
        for target in targets:
            target.parent.mkdir(parents=True,exist_ok=True)
            if not target.exists() and target in [plugin/name for name in DOOR_NATIVE_TARGETS] and target!=new_native:target.write_bytes(b'old door predecessor')
            previous=digest(target) if target.exists() else None;target.write_bytes(b'new door '+str(target).encode())
            if target.is_relative_to(plugin/'Content/OriginalDoorAudio_v01'):target.write_bytes((library/target.relative_to(plugin/'Content/OriginalDoorAudio_v01')).read_bytes())
            door_rows.append({'target':str(target),'before_sha256':previous,'after_sha256':digest(target)})
        door_path=w/'DoorAudioLab/installed.json';door={'installed':True,'phase':'complete','database_modified':False,
            'predecessor_receipt_sha256':digest(options_path),'gateway_predecessor_receipt_sha256':digest(mode_path),
            'resources_receipt_sha256':digest(resources_path),'native_before_sha256':previous_native,'native_after_sha256':digest(binary),'files':door_rows}
        put(door_path,door);assert verify_files(w)['door_audio_installed'];checks+=1
        door['predecessor_receipt_sha256']='0'*64;put(door_path,door);rejected();checks+=1
        door['predecessor_receipt_sha256']=digest(options_path);door['gateway_predecessor_receipt_sha256']='0'*64;put(door_path,door);rejected();checks+=1
        door['gateway_predecessor_receipt_sha256']=digest(mode_path);door['files'][0]['before_sha256']='0'*64;put(door_path,door);rejected();checks+=1
        door['files'][0]['before_sha256']=previous_native;put(door_path,door)
        door_wave=targets[-1];saved=door_wave.read_bytes();door_wave.write_bytes(b'corrupt door WAV');rejected();checks+=1;door_wave.write_bytes(saved)
        wave.write_bytes(b'tampered old combat wave after doors');rejected();checks+=1;wave.write_bytes(before)
        library=w/'FootstepAudioLab/OriginalFootstepAudio_v01';library.mkdir(parents=True);files={}
        for i in range(16):
            p=library/('files/'+str(i)+'.wav');p.parent.mkdir(exist_ok=True);p.write_bytes(b'original step '+str(i).encode());files[str(p)]=digest(p)
        catalog=library/'sounds.json';catalog.write_text('synthetic original foot contacts')
        resources_path=w/'FootstepAudioLab/resources.json';put(resources_path,{'catalog':str(catalog),'catalog_sha256':digest(catalog),'files':files})
        step_rows=[];previous_native=digest(binary)
        targets=[plugin/name for name in FOOTSTEP_NATIVE_TARGETS]+[plugin/'Content/OriginalFootstepAudio_v01'/Path(p).relative_to(library) for p in list(files)+[str(catalog)]]
        new_native=plugin/'Source/DAoCVisualBridge/Private/DAoCBridgeFootsteps.cpp'
        for target in targets:
            target.parent.mkdir(parents=True,exist_ok=True)
            if not target.exists() and target in [plugin/name for name in FOOTSTEP_NATIVE_TARGETS] and target!=new_native:target.write_bytes(b'old step predecessor')
            previous=digest(target) if target.exists() else None;target.write_bytes(b'new step '+str(target).encode())
            if target.is_relative_to(plugin/'Content/OriginalFootstepAudio_v01'):target.write_bytes((library/target.relative_to(plugin/'Content/OriginalFootstepAudio_v01')).read_bytes())
            step_rows.append({'target':str(target),'before_sha256':previous,'after_sha256':digest(target)})
        step_path=w/'FootstepAudioLab/installed.json';step={'installed':True,'phase':'complete','database_modified':False,
            'predecessor_receipt_sha256':digest(door_path),'resources_receipt_sha256':digest(resources_path),
            'native_before_sha256':previous_native,'native_after_sha256':digest(binary),'files':step_rows}
        put(step_path,step);assert verify_files(w)['footstep_audio_installed'];checks+=1
        step['predecessor_receipt_sha256']='0'*64;put(step_path,step);rejected();checks+=1
        step['predecessor_receipt_sha256']=digest(door_path);step['files'][0]['before_sha256']='0'*64;put(step_path,step);rejected();checks+=1
        step['files'][0]['before_sha256']=previous_native;put(step_path,step)
        saved=targets[-1].read_bytes();targets[-1].write_bytes(b'corrupt step WAV');rejected();checks+=1;targets[-1].write_bytes(saved)
        wave.write_bytes(b'corrupt original combat WAV after steps');rejected();checks+=1;wave.write_bytes(before)
        library=w/'ServerSoundAudioLab/OriginalServerSoundAudio_v01';library.mkdir(parents=True);files={}
        for i in range(28):
            p=library/('files/'+str(i)+'.wav');p.parent.mkdir(exist_ok=True);p.write_bytes(b'original event '+str(i).encode());files[str(p)]=digest(p)
        catalog=library/'sounds.json';catalog.write_text('synthetic original event rows')
        resources_path=w/'ServerSoundAudioLab/resources.json';put(resources_path,{'catalog':str(catalog),'catalog_sha256':digest(catalog),'files':files})
        event_rows=[];previous_native=digest(binary)
        native_targets=[plugin/name for name in SERVER_SOUND_NATIVE_TARGETS]
        targets=native_targets+[w/'Godot'/name for name in ['live_gateway.gd','visual_bridge.gd','server_sound_state.gd']]+[plugin/'Content/OriginalServerSoundAudio_v01'/Path(p).relative_to(library) for p in list(files)+[str(catalog)]]
        new_native=plugin/'Source/DAoCVisualBridge/Private/DAoCBridgeServerSoundAcceptance.cpp'
        for target in targets:
            target.parent.mkdir(parents=True,exist_ok=True)
            if not target.exists() and target in native_targets and target!=new_native:target.write_bytes(b'old event predecessor')
            previous=digest(target) if target.exists() else None;target.write_bytes(b'new event '+str(target).encode())
            if target.is_relative_to(plugin/'Content/OriginalServerSoundAudio_v01'):target.write_bytes((library/target.relative_to(plugin/'Content/OriginalServerSoundAudio_v01')).read_bytes())
            event_rows.append({'target':str(target),'before_sha256':previous,'after_sha256':digest(target)})
        event_path=w/'ServerSoundAudioLab/installed.json';event={'installed':True,'phase':'complete','database_modified':False,
            'predecessor_receipt_sha256':digest(step_path),'resources_receipt_sha256':digest(resources_path),
            'native_before_sha256':previous_native,'native_after_sha256':digest(binary),'files':event_rows}
        put(event_path,event);assert verify_files(w)['server_sound_audio_installed'];checks+=1
        event['predecessor_receipt_sha256']='0'*64;put(event_path,event);rejected();checks+=1
        event['predecessor_receipt_sha256']=digest(step_path);event['files'][0]['before_sha256']='0'*64;put(event_path,event);rejected();checks+=1
        event['files'][0]['before_sha256']=previous_native;put(event_path,event)
        saved=targets[-1].read_bytes();targets[-1].write_bytes(b'corrupt event WAV');rejected();checks+=1;targets[-1].write_bytes(saved)
        wave.write_bytes(b'corrupt original combat WAV after events');rejected();checks+=1;wave.write_bytes(before)
        water_library=w/'WaterMovementLab';water_library.mkdir();water_catalog=water_library/'water_field.json';water_catalog.write_text('original water mask')
        water_resources=water_library/'resources.json';put(water_resources,{'catalog':str(water_catalog),'catalog_sha256':digest(water_catalog)})
        water_rows=[];previous_native=digest(binary)
        native_targets=[plugin/name for name in WATER_NATIVE_TARGETS]
        targets=native_targets+[w/'Godot'/name for name in ['live_gateway.gd','movement_flags_state.gd']]+[plugin/'Content/WaterMovement_v01/water_field.json']
        new_names=['DAoCBridgeWaterData.h','DAoCBridgeWaterMovement.cpp','DAoCBridgeWaterAcceptance.cpp','movement_flags_state.gd','water_field.json']
        for target in targets:
            target.parent.mkdir(parents=True,exist_ok=True)
            if not target.exists() and target.name not in new_names:target.write_bytes(b'old water predecessor')
            previous=digest(target) if target.exists() else None;target.write_bytes(b'new water '+str(target).encode())
            if target.name=='water_field.json':target.write_bytes(water_catalog.read_bytes())
            water_rows.append({'target':str(target),'before_sha256':previous,'after_sha256':digest(target)})
        water_path=water_library/'installed.json';water={'installed':True,'phase':'complete','database_modified':False,
            'predecessor_receipt_sha256':digest(event_path),'resources_receipt_sha256':digest(water_resources),
            'native_before_sha256':previous_native,'native_after_sha256':digest(binary),'files':water_rows}
        put(water_path,water);assert verify_files(w)['water_movement_installed'];checks+=1
        water['predecessor_receipt_sha256']='0'*64;put(water_path,water);rejected();checks+=1
        water['predecessor_receipt_sha256']=digest(event_path);water['files'][0]['before_sha256']='0'*64;put(water_path,water);rejected();checks+=1
        water['files'][0]['before_sha256']=previous_native;put(water_path,water)
        saved=targets[-1].read_bytes();targets[-1].write_bytes(b'corrupt water mask');rejected();checks+=1;targets[-1].write_bytes(saved)
        wave.write_bytes(b'corrupt original combat WAV after water');rejected();checks+=1;wave.write_bytes(before)
        gateway=w/'Godot/live_gateway.gd';entry=next(row for row in water_rows if row['target']==str(gateway));old_gateway=entry['before_sha256'];entry['before_sha256']='0'*64;put(water_path,water);rejected();checks+=1;entry['before_sha256']=old_gateway;put(water_path,water)
        # Jump successor must retain every prior audio/water target and exact predecessor.
        previous_native=digest(binary);jump_rows=[]
        for target in [plugin/p for p in JUMP_NATIVE_TARGETS]:
            target.parent.mkdir(parents=True,exist_ok=True)
            if not target.exists() and target.name!='DAoCBridgeJumpLandingAcceptance.cpp':target.write_bytes(b'old jump predecessor')
            previous=digest(target) if target.exists() else None;target.write_bytes(b'new jump '+str(target).encode())
            jump_rows.append({'target':str(target),'before_sha256':previous,'after_sha256':digest(target)})
        jump_path=w/'JumpLandingLab/installed.json';jump={'installed':True,'phase':'complete','database_modified':False,
            'predecessor_receipt_sha256':digest(water_path),'native_before_sha256':previous_native,'native_after_sha256':digest(binary),'files':jump_rows}
        put(jump_path,jump);assert verify_files(w)['jump_landing_installed'];checks+=1
        jump['predecessor_receipt_sha256']='0'*64;put(jump_path,jump);rejected();checks+=1
        jump['predecessor_receipt_sha256']=digest(water_path);jump['files'][0]['before_sha256']='0'*64;put(jump_path,jump);rejected();checks+=1
        jump['files'][0]['before_sha256']=previous_native;put(jump_path,jump)
        saved=targets[-1].read_bytes();targets[-1].write_bytes(b'bad old water after jump');rejected();checks+=1;targets[-1].write_bytes(saved)
        wave.write_bytes(b'bad old combat after jump');rejected();checks+=1;wave.write_bytes(before)
        previous_native=digest(binary);key_root=w/'MovementKeysLab';key_catalog=key_root/'movement.json';put(key_catalog,{'version':1,'models':{}})
        key_resources=key_root/'resources.json';put(key_resources,{'catalog':str(key_catalog),'catalog_sha256':digest(key_catalog)})
        key_rows=[];key_target=plugin/'Content/MovementKeys_v01/movement.json'
        for target in [plugin/p for p in MOVEMENT_KEYS_NATIVE_TARGETS]+[key_target]:
            target.parent.mkdir(parents=True,exist_ok=True)
            if not target.exists() and target.name not in ['DAoCBridgeMovementKeys.h','DAoCBridgeMovementKeysAcceptance.cpp','movement.json']:target.write_bytes(b'old movement keys predecessor')
            previous=digest(target) if target.exists() else None;target.write_bytes(key_catalog.read_bytes() if target==key_target else b'new keys '+str(target).encode())
            key_rows.append({'target':str(target),'before_sha256':previous,'after_sha256':digest(target)})
        key_path=key_root/'installed.json';key_receipt={'installed':True,'phase':'complete','database_modified':False,
            'predecessor_receipt_sha256':digest(jump_path),'resources_receipt_sha256':digest(key_resources),
            'native_before_sha256':previous_native,'native_after_sha256':digest(binary),'files':key_rows}
        put(key_path,key_receipt);assert verify_files(w)['movement_keys_installed'];checks+=1
        key_receipt['predecessor_receipt_sha256']='0'*64;put(key_path,key_receipt);rejected();checks+=1
        key_receipt['predecessor_receipt_sha256']=digest(jump_path);key_receipt['files'][0]['before_sha256']='0'*64;put(key_path,key_receipt);rejected();checks+=1
        key_receipt['files'][0]['before_sha256']=previous_native;put(key_path,key_receipt)
        saved=key_target.read_bytes();key_target.write_bytes(b'bad movement stride');rejected();checks+=1;key_target.write_bytes(saved)
        wave.write_bytes(b'bad old combat after movement keys');rejected();checks+=1;wave.write_bytes(before)
        previous_native=digest(binary);track_root=w/'TargetTrackingLab';track_resources=track_root/'resources.json';put(track_resources,{'passed':True})
        track_rows=[];track_targets=[plugin/p for p in TARGET_TRACKING_NATIVE_TARGETS]+[w/'Godot'/n for n in ['live_gateway.gd','visual_bridge.gd','target_tracking_state.gd']]
        new_names=['DAoCBridgeTargetTracking.h','DAoCBridgeTargetTracking.cpp','DAoCBridgeTargetTrackingAcceptance.cpp','target_tracking_state.gd']
        for target in track_targets:
            target.parent.mkdir(parents=True,exist_ok=True)
            if not target.exists() and target.name not in new_names:target.write_bytes(b'old tracking predecessor')
            previous=digest(target) if target.exists() else None;target.write_bytes(b'new tracking '+str(target).encode())
            track_rows.append({'target':str(target),'before_sha256':previous,'after_sha256':digest(target)})
        track_path=track_root/'installed.json';track={'installed':True,'phase':'complete','database_modified':False,
            'predecessor_receipt_sha256':digest(key_path),'resources_receipt_sha256':digest(track_resources),
            'native_before_sha256':previous_native,'native_after_sha256':digest(binary),'files':track_rows}
        put(track_path,track);assert verify_files(w)['target_tracking_installed'];checks+=1
        track['predecessor_receipt_sha256']='0'*64;put(track_path,track);rejected();checks+=1
        track['predecessor_receipt_sha256']=digest(key_path);track['files'][0]['before_sha256']='0'*64;put(track_path,track);rejected();checks+=1
        track['files'][0]['before_sha256']=previous_native;put(track_path,track)
        state_target=w/'Godot/target_tracking_state.gd';saved=state_target.read_bytes();state_target.write_bytes(b'bad tracking state');rejected();checks+=1;state_target.write_bytes(saved)
        wave.write_bytes(b'bad old combat after tracking');rejected();checks+=1;wave.write_bytes(before)
        # The riding successor may replace only its exact code/catalog files
        # and introduce files inside its own new content namespace.
        previous_native=digest(binary);ride_root=w/'LiveRidingLab';ride_root.mkdir();ride_resources=ride_root/'resources.json';put(ride_resources,{'passed':True})
        content=[plugin/'Content/LiveRiding_v01'/n for n in ['riding.json','travel_routes.json','Audio/sounds.json']]
        targets=[plugin/p for p in LIVE_RIDING_NATIVE_TARGETS]+[w/'Godot'/n for n in LIVE_RIDING_GODOT_TARGETS]+[w/'models.json']+content
        ride_rows=[]
        for target in targets:
            target.parent.mkdir(parents=True,exist_ok=True)
            if not target.exists() and target.name not in LIVE_RIDING_NEW_NAMES and target not in content:target.write_bytes(b'old riding predecessor')
            previous=digest(target) if target.exists() else None;target.write_bytes(b'new riding '+str(target).encode());ride_rows.append({'target':str(target),'before_sha256':previous,'after_sha256':digest(target)})
        ride_path=ride_root/'installed.json';ride={'installed':True,'phase':'complete','database_modified':False,'server_rules_modified':False,
            'predecessor_receipt_sha256':digest(track_path),'resources_receipt_sha256':digest(ride_resources),'native_before_sha256':previous_native,'native_after_sha256':digest(binary),
            'content_targets':[str(p) for p in content],'files':ride_rows}
        put(ride_path,ride);assert verify_files(w)['live_riding_installed'];checks+=1
        ride['predecessor_receipt_sha256']='0'*64;put(ride_path,ride);rejected();checks+=1;ride['predecessor_receipt_sha256']=digest(track_path)
        ride['files'][0]['before_sha256']='0'*64;put(ride_path,ride);rejected();checks+=1;ride['files'][0]['before_sha256']=previous_native
        ride['content_targets'][0]=str(plugin/'Content/unrelated.json');put(ride_path,ride);rejected();checks+=1;ride['content_targets'][0]=str(content[0]);put(ride_path,ride)
        for target in [w/'Godot/inventory_state.gd',plugin/'Source/DAoCVisualBridge/Private/DAoCBridgeLiveRidingController.cpp',content[2]]:
            saved=target.read_bytes();target.write_bytes(b'changed riding file');rejected();checks+=1;target.write_bytes(saved)
        wave.write_bytes(b'changed old audio after riding');rejected();checks+=1;wave.write_bytes(before)
        assert verify_files(w)['live_riding_installed'];checks+=1
        prior=digest(binary);configuration_rows=[]
        for relative in KEY_CONFIGURATION_NATIVE_TARGETS:
            target=plugin/relative;target.parent.mkdir(parents=True,exist_ok=True)
            if not target.exists() and target.name not in KEY_CONFIGURATION_NEW_NAMES:target.write_bytes(b'old configuration predecessor')
            old=digest(target) if target.exists() else None;target.write_bytes(b'new controls '+relative.encode())
            configuration_rows.append(dict(target=str(target),before_sha256=old,after_sha256=digest(target)))
        config_path=w/'KeyConfigurationLab/installed.json';config=dict(installed=True,phase='complete',database_modified=False,server_rules_modified=False,
            predecessor_receipt_sha256=digest(ride_path),native_before_sha256=prior,native_after_sha256=digest(binary),files=configuration_rows)
        put(config_path,config);assert verify_files(w)['key_configuration_installed'];checks+=1
        config['predecessor_receipt_sha256']='0'*64;put(config_path,config);rejected();checks+=1;config['predecessor_receipt_sha256']=digest(ride_path)
        config['files'][0]['before_sha256']='0'*64;put(config_path,config);rejected();checks+=1;config['files'][0]['before_sha256']=prior;put(config_path,config)
        for target in [binary,plugin/'Source/DAoCVisualBridge/Private/DAoCBridgeKeyConfiguration.cpp',content[0],wave]:
            saved=target.read_bytes();target.write_bytes(b'tampered controls or protected predecessor');rejected();checks+=1;target.write_bytes(saved)
        config['files'].append(dict(target=str(plugin/'unrelated.txt'),before_sha256=None,after_sha256='0'*64));put(config_path,config);rejected();checks+=1;config['files'].pop();put(config_path,config)
        assert verify_files(w)['key_configuration_installed'];checks+=1
        prior=digest(binary);interface_rows=[]
        for relative in INTERFACE_KEYS_NATIVE_TARGETS:
            target=plugin/relative;target.parent.mkdir(parents=True,exist_ok=True)
            if not target.exists():target.write_bytes(b'old synthetic interface predecessor')
            old=digest(target);target.write_bytes(b'new interface keys '+relative.encode());interface_rows.append(dict(target=str(target),before_sha256=old,after_sha256=digest(target)))
        interface_path=w/'InterfaceKeysLab/installed.json';interface=dict(installed=True,phase='complete',database_modified=False,server_rules_modified=False,
            predecessor_receipt_sha256=digest(config_path),native_before_sha256=prior,native_after_sha256=digest(binary),files=interface_rows)
        put(interface_path,interface);assert verify_files(w)['interface_keys_installed'];checks+=1
        interface['predecessor_receipt_sha256']='0'*64;put(interface_path,interface);rejected();checks+=1;interface['predecessor_receipt_sha256']=digest(config_path)
        interface['files'][0]['before_sha256']='0'*64;put(interface_path,interface);rejected();checks+=1;interface['files'][0]['before_sha256']=prior;put(interface_path,interface)
        for target in [binary,plugin/'Source/DAoCVisualBridge/Private/DAoCBridgeClassicUI.cpp',content[0],wave]:
            saved=target.read_bytes();target.write_bytes(b'tampered UI keys or protected predecessor');rejected();checks+=1;target.write_bytes(saved)
        interface['files'].append(dict(target=str(plugin/'unrelated.txt'),before_sha256=None,after_sha256='0'*64));put(interface_path,interface);rejected();checks+=1;interface['files'].pop();put(interface_path,interface)
        assert verify_files(w)['interface_keys_installed'];checks+=1
        prior=digest(binary);display_rows=[]
        for relative in DISPLAY_NATIVE_TARGETS:
            target=plugin/relative;target.parent.mkdir(parents=True,exist_ok=True)
            old=None if target.name in DISPLAY_NEW_NAMES else digest(target)
            target.write_bytes(b'new display settings '+relative.encode());display_rows.append(dict(target=str(target),before_sha256=old,after_sha256=digest(target)))
        display_path=w/'DisplaySettingsLab/installed.json';display=dict(installed=True,phase='complete',database_modified=False,server_rules_modified=False,
            predecessor_receipt_sha256=digest(interface_path),native_before_sha256=prior,native_after_sha256=digest(binary),files=display_rows)
        put(display_path,display);assert verify_files(w)['display_settings_installed'];checks+=1
        display['predecessor_receipt_sha256']='0'*64;put(display_path,display);rejected();checks+=1;display['predecessor_receipt_sha256']=digest(interface_path)
        display['files'][0]['before_sha256']='0'*64;put(display_path,display);rejected();checks+=1;display['files'][0]['before_sha256']=prior;put(display_path,display)
        for target in [binary,plugin/'Source/DAoCVisualBridge/Private/DAoCBridgeDisplaySettings.cpp',content[0],wave]:
            saved=target.read_bytes();target.write_bytes(b'tampered display or protected predecessor');rejected();checks+=1;target.write_bytes(saved)
        display['files'].append(dict(target=str(plugin/'unrelated.txt'),before_sha256=None,after_sha256='0'*64));put(display_path,display);rejected();checks+=1;display['files'].pop();put(display_path,display)
        assert verify_files(w)['display_settings_installed'];checks+=1
        # Independent minimal eligibility chain: Shar may succeed the exact
        # accepted spell-class policy, never an arbitrary rules replacement.
        prior=digest(binary);guild_rows=[]
        targets=[plugin/r for r in GUILD_NATIVE_TARGETS]+[w/'Godot'/r for r in GUILD_GODOT_TARGETS]+[plugin/'Content/GuildUI_v01/radiobutton1.png']+[Path(r['target']) for r in server_rows]
        for target in targets:
            target.parent.mkdir(parents=True,exist_ok=True)
            if not target.exists() and target.name not in GUILD_NEW_NAMES:target.write_bytes(b'old guild predecessor')
            old=None if target.name in GUILD_NEW_NAMES else digest(target)
            target.write_bytes(b'new guild '+str(target).encode());guild_rows.append(dict(target=str(target),before_sha256=old,after_sha256=digest(target)))
        guild_path=w/'GuildWindowLab/installed.json';guild=dict(installed=True,phase='complete',database_modified=False,server_rules_modified=False,predecessor_receipt_sha256=digest(display_path),native_before_sha256=prior,native_after_sha256=digest(binary),files=guild_rows)
        put(guild_path,guild);assert verify_files(w)['guild_window_installed'];checks+=1
        guild['predecessor_receipt_sha256']='0'*64;put(guild_path,guild);rejected();checks+=1;guild['predecessor_receipt_sha256']=digest(display_path)
        guild['files'][0]['before_sha256']='0'*64;put(guild_path,guild);rejected();checks+=1;guild['files'][0]['before_sha256']=prior;put(guild_path,guild)
        for target in [binary,w/'Godot/guild_state.gd',plugin/'Content/GuildUI_v01/radiobutton1.png',Path(server_rows[0]['target']),wave]:
            old=target.read_bytes();target.write_bytes(b'tampered guild or protected predecessor');rejected();checks+=1;target.write_bytes(old)
        guild['files'].append(dict(target=str(plugin/'unrelated.txt'),before_sha256=None,after_sha256='0'*64));put(guild_path,guild);rejected();checks+=1;guild['files'].pop();put(guild_path,guild)
        assert verify_files(w)['guild_window_installed'];checks+=1
        prior=digest(binary);emblem_rows=[]
        targets=[plugin/r for r in EMBLEM_NATIVE_TARGETS+EMBLEM_UI_TARGETS]+[w/'Godot'/r for r in EMBLEM_GODOT_TARGETS]
        for target in targets:
            target.parent.mkdir(parents=True,exist_ok=True)
            if not target.exists() and target.name not in EMBLEM_NEW_NAMES:target.write_bytes(b'old emblem predecessor')
            old=None if target.name in EMBLEM_NEW_NAMES else digest(target)
            target.write_bytes(b'new emblem '+str(target).encode());emblem_rows.append(dict(target=str(target),before_sha256=old,after_sha256=digest(target)))
        emblem_path=w/'EmblemWindowLab/installed.json';emblem=dict(installed=True,phase='complete',database_modified=False,server_rules_modified=False,predecessor_receipt_sha256=digest(guild_path),native_before_sha256=prior,native_after_sha256=digest(binary),files=emblem_rows)
        put(emblem_path,emblem);assert verify_files(w)['emblem_window_installed'];checks+=1
        emblem['predecessor_receipt_sha256']='0'*64;put(emblem_path,emblem);rejected();checks+=1;emblem['predecessor_receipt_sha256']=digest(guild_path)
        emblem['files'][0]['before_sha256']='0'*64;put(emblem_path,emblem);rejected();checks+=1;emblem['files'][0]['before_sha256']=prior;put(emblem_path,emblem)
        for target in [binary,w/'Godot/emblem_picker_state.gd',plugin/'Content/EmblemUI_v01/picker.json',plugin/'Source/DAoCVisualBridge/Private/DAoCBridgeEmblemPreview.cpp',Path(server_rows[0]['target']),wave]:
            old=target.read_bytes();target.write_bytes(b'tampered emblem or protected predecessor');rejected();checks+=1;target.write_bytes(old)
        emblem['files'].append(dict(target=str(plugin/'unrelated.txt'),before_sha256=None,after_sha256='0'*64));put(emblem_path,emblem);rejected();checks+=1;emblem['files'].pop();put(emblem_path,emblem)
        assert verify_files(w)['emblem_window_installed'];checks+=1
        # Inventory was not changed by the emblem UI delivery. Anchor its old
        # bytes to that delivery's already-sealed source evidence as well.
        (w/'Godot/classic_ui_state.gd').write_text('unchanged synthetic classic UI')
        inventory_proof=w/'EmblemWindowLab/prior_inventory_source.json';put(inventory_proof,{'source_inputs':{str(w/'source/inventory_state.gd'):digest(w/'Godot/inventory_state.gd'),str(w/'source/classic_ui_state.gd'):digest(w/'Godot/classic_ui_state.gd')}})
        emblem['evidence']={str(inventory_proof):digest(inventory_proof)};put(emblem_path,emblem)
        prior=digest(binary);handover_rows=[]
        for target in [plugin/r for r in HANDOVER_NATIVE_TARGETS]+[w/'Godot'/r for r in HANDOVER_GODOT_TARGETS]:
            target.parent.mkdir(parents=True,exist_ok=True)
            old=None if target.name in HANDOVER_NEW_NAMES else digest(target)
            target.write_bytes(b'new item handover '+str(target).encode());handover_rows.append(dict(target=str(target),before_sha256=old,after_sha256=digest(target)))
        handover_path=w/'ItemHandoverLab/installed.json';handover=dict(installed=True,phase='complete',database_modified=False,server_rules_modified=False,predecessor_receipt_sha256=digest(emblem_path),native_before_sha256=prior,native_after_sha256=digest(binary),inventory_predecessor_proof=str(inventory_proof),files=handover_rows)
        put(handover_path,handover);assert verify_files(w)['item_handover_installed'];checks+=1
        handover['predecessor_receipt_sha256']='0'*64;put(handover_path,handover);rejected();checks+=1;handover['predecessor_receipt_sha256']=digest(emblem_path)
        handover['files'][0]['before_sha256']='0'*64;put(handover_path,handover);rejected();checks+=1;handover['files'][0]['before_sha256']=prior;put(handover_path,handover)
        for target in [binary,w/'Godot/inventory_state.gd',plugin/'Source/DAoCVisualBridge/Private/DAoCBridgeItemHandover.cpp',plugin/'Content/EmblemUI_v01/picker.json',inventory_proof,Path(server_rows[0]['target']),wave]:
            old=target.read_bytes();target.write_bytes(b'tampered item handover or protected predecessor');rejected();checks+=1;target.write_bytes(old)
        row=next(r for r in handover['files'] if r['target']==str(w/'Godot/inventory_state.gd'));saved=row['before_sha256'];row['before_sha256']='0'*64;put(handover_path,handover);rejected();checks+=1;row['before_sha256']=saved;put(handover_path,handover)
        handover['files'].append(dict(target=str(plugin/'unrelated.txt'),before_sha256=None,after_sha256='0'*64));put(handover_path,handover);rejected();checks+=1;handover['files'].pop();put(handover_path,handover)
        assert verify_files(w)['item_handover_installed'];checks+=1
        target=w/'Godot/inventory_state.gd';before=digest(target);target.write_text('poison-capable synthetic inventory')
        poison_proof=w/'WeaponPoisonLab/proof.json';put(poison_proof,{'passed':True,'synthetic':True})
        poison_path=w/'WeaponPoisonLab/installed.json';poison=dict(installed=True,phase='complete',database_modified=False,server_rules_modified=False,predecessor_receipt_sha256=digest(handover_path),native_sha256=digest(binary),files=[dict(target=str(target),before_sha256=before,after_sha256=digest(target))],evidence={str(poison_proof):digest(poison_proof)})
        put(poison_path,poison);assert verify_files(w)['weapon_poison_installed'];checks+=1
        for field in ['predecessor_receipt_sha256','native_sha256']:
            old=poison[field];poison[field]='0'*64;put(poison_path,poison);rejected();checks+=1;poison[field]=old;put(poison_path,poison)
        poison['files'][0]['before_sha256']='0'*64;put(poison_path,poison);rejected();checks+=1;poison['files'][0]['before_sha256']=before;put(poison_path,poison)
        for q in [target,poison_proof,binary,Path(server_rows[0]['target']),wave]:
            old=q.read_bytes();q.write_bytes(b'tampered poison or protected predecessor');rejected();checks+=1;q.write_bytes(old)
        poison['files'].append(dict(target=str(plugin/'unrelated.txt'),before_sha256=None,after_sha256='0'*64));put(poison_path,poison);rejected();checks+=1;poison['files'].pop();put(poison_path,poison)
        assert verify_files(w)['weapon_poison_installed'];checks+=1
        before=digest(target);target.write_text('equipment refusal synthetic inventory')
        refusal_proof=w/'EquipmentRefusalLab/proof.json';put(refusal_proof,{'passed':True,'synthetic':True})
        refusal_path=w/'EquipmentRefusalLab/installed.json';refusal=dict(installed=True,phase='complete',database_modified=False,server_rules_modified=False,predecessor_receipt_sha256=digest(poison_path),native_sha256=digest(binary),files=[dict(target=str(target),before_sha256=before,after_sha256=digest(target))],evidence={str(refusal_proof):digest(refusal_proof)})
        put(refusal_path,refusal);assert verify_files(w)['equipment_refusals_installed'];checks+=1
        for field in ['predecessor_receipt_sha256','native_sha256']:
            old=refusal[field];refusal[field]='0'*64;put(refusal_path,refusal);rejected();checks+=1;refusal[field]=old;put(refusal_path,refusal)
        refusal['files'][0]['before_sha256']='0'*64;put(refusal_path,refusal);rejected();checks+=1;refusal['files'][0]['before_sha256']=before;put(refusal_path,refusal)
        for q in [target,refusal_proof,binary,Path(server_rows[0]['target']),wave]:
            old=q.read_bytes();q.write_bytes(b'tampered refusal or protected predecessor');rejected();checks+=1;q.write_bytes(old)
        refusal['files'].append(dict(target=str(plugin/'unrelated.txt'),before_sha256=None,after_sha256='0'*64));put(refusal_path,refusal);rejected();checks+=1;refusal['files'].pop();put(refusal_path,refusal)
        assert verify_files(w)['equipment_refusals_installed'];checks+=1
        prior=digest(binary);hover_rows=[]
        for target in [plugin/r for r in HOVER_NATIVE_TARGETS]+[w/'Godot'/r for r in HOVER_GODOT_TARGETS]:
            target.parent.mkdir(parents=True,exist_ok=True);old=None if target.name in HOVER_NEW_NAMES else digest(target)
            target.write_bytes(b'new hover details '+str(target).encode());hover_rows.append(dict(target=str(target),before_sha256=old,after_sha256=digest(target)))
        hover_path=w/'HoverDetailsLab/installed.json';hover=dict(installed=True,phase='complete',database_modified=False,server_rules_modified=False,predecessor_receipt_sha256=digest(refusal_path),native_before_sha256=prior,native_after_sha256=digest(binary),classic_predecessor_proof=str(inventory_proof),files=hover_rows,evidence={str(poison_proof):digest(poison_proof)})
        put(hover_path,hover);assert verify_files(w)['hover_details_installed'];checks+=1
        hover['predecessor_receipt_sha256']='0'*64;put(hover_path,hover);rejected();checks+=1;hover['predecessor_receipt_sha256']=digest(refusal_path);put(hover_path,hover)
        for q in [binary,w/'Godot/classic_ui_state.gd',w/'Godot/live_gateway.gd',plugin/'Source/DAoCVisualBridge/Private/DAoCBridgeHoverDetailsAcceptance.cpp',inventory_proof,poison_proof,Path(server_rows[0]['target']),wave]:
            old=q.read_bytes();q.write_bytes(b'tampered hover or protected predecessor');rejected();checks+=1;q.write_bytes(old)
        row=next(r for r in hover['files'] if r['target']==str(w/'Godot/classic_ui_state.gd'));old=row['before_sha256'];row['before_sha256']='0'*64;put(hover_path,hover);rejected();checks+=1;row['before_sha256']=old;put(hover_path,hover)
        hover['files'].append(dict(target=str(plugin/'unrelated.txt'),before_sha256=None,after_sha256='0'*64));put(hover_path,hover);rejected();checks+=1;hover['files'].pop();put(hover_path,hover)
        assert verify_files(w)['hover_details_installed'];checks+=1
        sw=w/'shar_case';rules=sw/'rules.json';rules.parent.mkdir();rules.write_text('old rules');old_rules=digest(rules)
        sb=sw/'ExpansionRaceLab/CentralDelivery';original=sb/'MinotaurActivation/installed.json'
        put(original,{'installed':True,'only_race_enabled':21,'files':[{'target':str(rules),'after_sha256':old_rules}]})
        rules.write_text('spellclass rules');middle=digest(rules)
        previous=sb/'SpellClassActivation/installed.json';previous_plan=previous.parent/'plan.json'
        put(previous_plan,{'rules_after_sha256':middle})
        put(previous,{'installed':True,'phase':'complete','minotaur_receipt_sha256':digest(original),'classes_enabled':[39,58],
            'races_changed':False,'plan_sha256':digest(previous_plan),'rules_before_sha256':old_rules,'rules_after_sha256':middle,'rules_target':str(rules)})
        rules.write_text('shar rules');shar_plan=sb/'SharActivation/plan.json';put(shar_plan,{'rules_after_sha256':digest(rules)})
        shar_path=shar_plan.parent/'installed.json';shar={'installed':True,'phase':'complete','only_race_enabled':18,
            'predecessor_receipt_sha256':digest(previous),'rules_before_sha256':middle,'rules_after_sha256':digest(rules),'rules_target':str(rules),'plan_sha256':digest(shar_plan)}
        put(shar_path,shar);assert verify_files(sw)['shar_installed'];checks+=1
        shar['predecessor_receipt_sha256']='0'*64;put(shar_path,shar)
        try:verify_files(sw)
        except AssertionError:checks+=1
        else:raise AssertionError('Unrelated Shar predecessor accepted')
        shar['predecessor_receipt_sha256']=digest(previous);shar['rules_before_sha256']='0'*64;put(shar_path,shar)
        try:verify_files(sw)
        except AssertionError:checks+=1
        else:raise AssertionError('Incorrect previous Shar rules accepted')
    return {'passed':True,'checks':checks,'synthetic_only':True,'normal_installation_modified':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--workspace',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(verify(args.workspace.resolve())))
