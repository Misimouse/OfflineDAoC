"""Verify central file receipts, allowing only the explicitly recorded rules successor."""
import json
from pathlib import Path

from prepare_combined_expansion_data import digest


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
    combat_path=workspace/'CombatAudioLab/installed.json'
    combat=json.loads(combat_path.read_text()) if combat_path.exists() else None
    if combat and not combat.get('installed'):combat=None
    replacements={}
    mode_path=workspace/'WeaponModeAudioLab/installed.json'
    mode=json.loads(mode_path.read_text()) if mode_path.exists() else None
    if mode and not mode.get('installed'):mode=None
    mode_replacements={}
    if mode:
        assert combat and mode['phase']=='complete' and not mode['database_modified']
        assert mode['predecessor_receipt_sha256']==digest(combat_path)
        assert mode['native_sha256']==combat['native_after_sha256']
        mode_replacements={row['target']:row for row in mode['files']}
        assert len(mode['files'])==len(mode_replacements)==2 and set(mode_replacements)=={str(workspace/'Godot/live_gateway.gd'),str(workspace/'Godot/weapon_mode_audio_state.gd')}
        assert mode_replacements[str(workspace/'Godot/weapon_mode_audio_state.gd')]['before_sha256'] is None
        for row in mode['files']:assert digest(Path(row['target']))==row['after_sha256']
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
            latest=mode_replacements.get(row['target'])
            if latest:assert latest['before_sha256']==row['after_sha256']
            assert digest(Path(row['target']))==(latest['after_sha256'] if latest else row['after_sha256'])
        for row in audio['files']:
            changed=replacements.get(row['target'])
            if changed:assert changed['before_sha256']==row['after_sha256']
            assert digest(Path(row['target']))==(changed['after_sha256'] if changed else row['after_sha256'])
    replaced=0
    for row in original['files']:
        path=Path(row['target'])
        expected=row['after_sha256']
        if successor and str(path)==successor['rules_target']:
            assert expected==successor['rules_before_sha256']
            expected=successor['rules_after_sha256']
            replaced+=1
        if str(path) in replacements:
            changed=replacements[str(path)]
            assert changed['before_sha256']==expected
            expected=changed['after_sha256']
        if str(path) in mode_replacements:
            changed=mode_replacements[str(path)]
            assert changed['before_sha256']==expected
            expected=changed['after_sha256']
        assert digest(path)==expected, ('Installed central file changed',str(path))
    assert not successor or replaced==1
    if combat:
        changed_original=[row for row in original['files'] if row['target'] in replacements]
        assert len(changed_original)==1 and Path(changed_original[0]['target'])==workspace/'Godot/live_gateway.gd'
    return {'passed':True,'minotaur_installed':True,'spellclasses_installed':bool(successor),'combat_audio_installed':bool(combat),'weapon_mode_audio_installed':bool(mode),'verified_files':len(original['files'])}
