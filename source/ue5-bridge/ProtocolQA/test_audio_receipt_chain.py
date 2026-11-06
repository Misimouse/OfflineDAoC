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
    return {'passed':True,'checks':checks,'synthetic_only':True,'normal_installation_modified':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--workspace',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(verify(args.workspace.resolve())))
