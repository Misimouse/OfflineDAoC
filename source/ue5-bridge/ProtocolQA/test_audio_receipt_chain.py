"""Synthetic successor-receipt checks; no owner files or databases are touched."""
import argparse
import json
from pathlib import Path
import tempfile
from central_activation_receipts import verify_files
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
