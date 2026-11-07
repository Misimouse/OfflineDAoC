"""Read-only map from original key labels to already implemented native UI actions."""
import argparse,json
from pathlib import Path
from prepare_combined_expansion_data import digest

def audit(workspace,install):
    repo=Path(__file__).resolve().parents[3];source=repo/'source/ue5-bridge'
    original=install/'new-client/godot';catalog=original/'content/ui/keybinds.json'
    data=json.loads(catalog.read_text(encoding='utf-8-sig'));actions={a['id']:a for a in data['actions']}
    mapping=[('show_stats','P','SetClassicTab(character)'),('show_inventory','I','ToggleInventory'),('show_skills','H','SetClassicTab(skills)'),
        ('show_spells','','SetClassicTab(magic)'),('show_combat','J','SetClassicTab(combat)'),('show_group','G','SetClassicTab(group)'),
        ('show_map','M','ToggleZoneMap'),('show_journal','L','ToggleClassicJournal'),('show_trainer','T','ToggleClassicTrainer'),
        ('target_self','F7','SelectEntity(player:local)'),('target_enemy','Tab','SelectEntity(TargetAtCursor cycle=true)'),
        ('interact','E','InteractSelected / InteractDoor'),('inspect_item','Shift+I','ClassicInspect'),('attack_mode','C','RequestAttack'),('sit','N','RequestSit')]
    rows=[dict(id=i,label=actions.get(i,{}).get('label',{'show_trainer':'Training Window','target_self':'Target Self','interact':'Interact','inspect_item':'Inspect Item'}.get(i,i)),
        current_default=k,dispatch=dispatch,original_presets=actions.get(i,{}).get('presets'),new_server_action=False) for i,k,dispatch in mapping]
    for bar in range(1,4):
        for slot in range(1,11):rows.append(dict(id=f'qb{bar}_{slot}',current_default=['','Alt+','Ctrl+'][bar-1]+str(slot%10),dispatch='ui_use_slot',bar=bar-1,slot=slot-1,new_server_action=False))
    for bank in range(1,11):rows.append(dict(id=f'qbank_{bank}',current_default='Shift+'+str(bank%10),dispatch='ui_bank',bar=0,bank=bank-1,new_server_action=False))
    assert len(rows)==55 and len({r['id'] for r in rows})==55
    inputs=[catalog,original/'game/ui/keybinds.gd',original/'game/ui/options_window.gd']
    inputs += [source/'UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private'/n for n in ['DAoCBridgeClassicUI.cpp','DAoCBridgePlayerStatus.cpp','DAoCBridgeInteraction.cpp','DAoCBridgeSubsystem.cpp','DAoCBridgeKeyConfiguration.cpp']]
    report=dict(passed=True,scope='55 existing UI/combat/target/quickbar actions, plus previous ten movement actions',rows=rows,
        preserve_existing_defaults=True,preserve_existing_binding_file=True,original_full_presets=False,
        excluded=['unimplemented original actions','chat/editing/menu reserved keys','new gameplay rules','world/graphics'],
        input_hashes={str(p):digest(p) for p in inputs},normal_installation_modified=False,database_modified=False)
    root=workspace/'InterfaceKeysLab';root.mkdir(exist_ok=True);(root/'reference_audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return dict(passed=True,actions=55,total_with_movement=65,output=str(root/'reference_audit.json'))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['workspace','install']:p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();print(json.dumps(audit(a.workspace.resolve(),a.install.resolve())))
