"""Synthetic successor-receipt checks; no owner files or databases are touched."""
import argparse
import json
from pathlib import Path
import tempfile
from central_activation_receipts import verify_files, OPTIONS_TARGETS, DOOR_NATIVE_TARGETS, FOOTSTEP_NATIVE_TARGETS, SERVER_SOUND_NATIVE_TARGETS, WATER_NATIVE_TARGETS
from prepare_combined_expansion_data import digest


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
        put(original,{'installed':True,'only_race_enabled':21,'files':[{'target':str(gateway),'after_sha256':old_gateway}]})
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
        # Independent minimal eligibility chain: Shar may succeed the exact
        # accepted spell-class policy, never an arbitrary rules replacement.
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
