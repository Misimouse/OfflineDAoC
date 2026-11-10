"""Compare original action identifiers with the bounded native editable surface."""
import argparse
import json
from pathlib import Path
import re
from prepare_combined_expansion_data import digest


def audit(workspace, install):
    source = Path(__file__).resolve().parents[1]
    game = install/'new-client/godot/game'
    original = game.parent/'content/ui/keybinds.json'
    native = workspace/'Client/Plugins/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeKeyConfiguration.cpp'
    evidence = [original,native,game/'ui/keybinds.gd',game/'ui/game_ui.gd',game/'zone_viewer.gd',
                game/'net/server.gd',source/'Godot/live_gateway.gd',source/'Godot/visual_bridge.gd',
                source.parents[0]/'server/GameServer/commands/playercommands/sprint.cs',
                source.parents[0]/'server/GameServer/gameobjects/GamePlayer.cs']
    original_runtime = [p for p in game.rglob('*.gd') if p.name != 'keybinds.gd']
    native_private=native.parent
    native_dispatch={name:(native_private/name).read_text(encoding='utf-8-sig') for name in ['DAoCBridgeChat.cpp','DAoCBridgeSubsystem.cpp','DAoCBridgeWorldPointer.cpp','DAoCBridgeClassicUI.cpp']}
    evidence += original_runtime+[native_private/name for name in native_dispatch]
    evidence=list(dict.fromkeys(evidence));hashes = {str(p):digest(p) for p in evidence}
    runtime_text={str(p.relative_to(game)):p.read_text(encoding='utf-8-sig') for p in original_runtime}
    fixed={
        'camera_toggle':('DAoCBridgeWorldPointer.cpp','EKeys::F11','F11 -> existing first person toggle'),
        'chat':('DAoCBridgeSubsystem.cpp','EKeys::Enter','Enter -> existing chat input'),
        'chat_page_up':('DAoCBridgeChat.cpp','EKeys::PageUp','PageUp, Shift selects main pane'),
        'chat_page_down':('DAoCBridgeChat.cpp','EKeys::PageDown','PageDown, Shift selects main pane'),
    }
    for file,needle,_ in fixed.values():assert needle in native_dispatch[file]
    data = json.loads(original.read_text(encoding='utf-8-sig'))
    text = native.read_text(encoding='utf-8-sig')
    editable = set(re.findall(r'(?:Add|UI)\(TEXT\("([^"]+)"\)',text))
    editable.update(f'qb{bar}_{slot}' for bar in range(1,4) for slot in range(1,11))
    editable.update(f'qbank_{bank}' for bank in range(1,11))
    if 'FString::Printf(TEXT("target_group_%d"),I+2)' in text:editable.update(f'target_group_{slot}' for slot in range(2,9))
    assert len(editable) >= 69
    aliases = {'torch':'personal_torch','delve':'inspect_item','target_group_1':'target_self'}
    rows = []
    for action in data['actions']:
        key = action['id']
        mapped = aliases.get(key,key)
        status = 'editable_native_action' if mapped in editable else 'not_in_editable_surface_requires_dispatch_review'
        if key in aliases:
            status = 'equivalent_native_action_different_identifier_or_binding'
        mentions=[name for name,value in runtime_text.items() if ('"'+key+'"') in value or ("'"+key+"'") in value]
        native_note=''
        if mapped not in editable and key in fixed:
            status='existing_native_fixed_shortcut';native_note=fixed[key][2]
        elif mapped not in editable and not mentions:
            status='catalogue_only_requires_DOL_contract_review'
        if key=='sell' and mapped in editable:native_note='Editable, starts unbound to preserve accepted backward walking.'
        rows.append(dict(original_id=key,label=action['label'],category=action['category'],
                         original_presets=action['presets'],native_id=mapped,status=status,
                         original_runtime_mentions=mentions,native_note=native_note))
    # A catalogue difference is not proof that a feature is missing: camera,
    # chat, warmap and group picking also have fixed shortcuts or UI dispatch.
    next_actions = [key for key in ['sprint','weapon_right','weapon_two_hand','weapon_ranged'] if key not in editable]
    server = (game/'net/server.gd').read_text(encoding='utf-8-sig')
    assert 'func switch_weapon(' in server and '"standard": 10, "twohand": 12, "ranged": 13' in server
    assert 'Server.command("/sprint")' in (game/'zone_viewer.gd').read_text(encoding='utf-8-sig')
    assert 'HasAbility(Abilities.Sprint)' in (source.parents[0]/'server/GameServer/commands/playercommands/sprint.cs').read_text(encoding='utf-8-sig')
    result = dict(passed=True,scope='Action identifiers and source contracts, not complete gameplay parity',
                  original_actions=len(rows),native_editable_actions=len(editable),rows=rows,
                  source_inputs=hashes,normal_runtime_modified=False,database_modified=False,
                  preset_conflicts=['Original RPG A/D turn; current accepted bridge A/D strafe.',
                                   'Original N selects two-hand; current bridge N sits.',
                                   'Original T torch; current bridge T training and Shift+T torch.'],
                  next_package='CLIENT-WEAPON-AND-SPRINT-CONTROLS' if next_actions else 'CLIENT-CONTROLS-DISPATCH-CLOSURE',next_actions=next_actions,
                  deferred_action_ids=[r['original_id'] for r in rows if r['status'] in ['catalogue_only_requires_DOL_contract_review','not_in_editable_surface_requires_dispatch_review']],
                  completeness_note='A catalogue identifier alone does not prove an implemented Godot feature. Existing fixed shortcuts and future DOL-backed additions remain distinct.',
                  delivery_contract=['Keep current accepted defaults and saved custom bindings.',
                                     'Reuse original UseSlot 10/12/13 and server-authorized /sprint.',
                                     'Do not fabricate speed, endurance, equipment or client-side acknowledgement.',
                                     'No wholesale RPG/FPS/MMO preset activation or unrelated art changes.'])
    assert all(digest(Path(p)) == sha for p,sha in hashes.items())
    lab = workspace/'OriginalControlsLab'
    lab.mkdir(exist_ok=True)
    receipt = lab/'installed.json'
    delivered = receipt.exists() and json.loads(receipt.read_text()).get('installed',False)
    (lab/('audit_current.json' if delivered else 'audit.json')).write_text(json.dumps(result,indent=2))
    return {k:v for k,v in result.items() if k not in ['rows','source_inputs']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--install',type=Path,required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.workspace.resolve(),args.install.resolve())))
