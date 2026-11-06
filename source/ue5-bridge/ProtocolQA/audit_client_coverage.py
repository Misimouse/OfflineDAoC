"""Inventory original client surfaces and explicit bridge contract, without claiming full parity."""
import argparse,ast,json,re
from pathlib import Path
from prepare_combined_expansion_data import digest

def audit(workspace,install):
    source=Path(__file__).resolve().parents[1];game=install/'new-client/godot/game';native=source/'UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private'
    transport=source/'Godot/visual_bridge.gd';gateway=source/'Godot/live_gateway.gd';text=transport.read_text(encoding='utf-8-sig')
    actions=ast.literal_eval(re.search(r'if gameplay_enabled and action in (\[[^\n]+?\])',text).group(1))
    metadata=ast.literal_eval(re.search(r'for key in (\[[^\n]+?\])',text).group(1))
    surfaces=sorted(game.glob('ui/*.gd'));inputs={str(p):digest(p) for p in surfaces+[game/'player.gd',game/'zone_viewer.gd',game/'world/horse_routes.gd',transport,gateway]}
    rows=[]
    def row(feature,original,bridge,status,notes):
        files=[game/p for p in original]+[source/p for p in bridge]
        assert all(p.exists() for p in files),(feature,files)
        for p in files:inputs[str(p)]=digest(p)
        rows.append(dict(feature=feature,source_evidence=[str(p) for p in files],status=status,notes=notes))
    row('Character selection/creation/customization',['ui/game_ui.gd'],['Godot/character_lobby.gd','UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeCharacterLobby.cpp'],'source_integrated_visual_review_pending','Enabled race/class matrix is explicit; original level-five progression retained. Appearance review remains separate.')
    row('Inventory, equipment and quickbars',['ui/inventory_sheet.gd','ui/quickbar.gd'],['Godot/inventory_state.gd','Godot/classic_ui_state.gd'],'source_integrated_not_full_parity_claim','Use existing data/art; source presence alone does not certify all items, classes and equipment combinations.')
    row('Merchants, training, journal, vault, party and exchange',['ui/merchant_window.gd','ui/trainer_window.gd','ui/journal_window.gd','ui/vault_window.gd','ui/exchange_window.gd'],['Godot/interaction_state.gd','Godot/trainer_state.gd','Godot/journal_state.gd','Godot/vault_state.gd','Godot/party_state.gd','Godot/exchange_state.gd'],'source_integrated_not_full_parity_claim','Realm Exchange is a marketplace; do not confuse it with player-to-player trading. Quest UI modernization remains deferred.')
    row('Movement, selection, audio and sound options',['player.gd','ui/options_window.gd'],['UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeMovementKeys.h','UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeWaterMovement.cpp','UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeOptions.cpp'],'installed_automated_evidence_owner_review_pending','Recent scoped deliveries are receipt/hash protected; this does not cover climbing/diving or the entire settings window.')
    row('Client face/follow/stick commands',['ui/chat_window.gd','player.gd','zone_viewer.gd'],['Godot/live_gateway.gd','Godot/target_tracking_state.gd','UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeTargetTracking.cpp'],'installed_automated_evidence_owner_review_pending','Local face/follow/stick delivered with original ranges and native collision; no pathfinding. Owner gameplay review pending.')
    riding_receipt=workspace/'LiveRidingLab/installed.json';riding_installed=riding_receipt.exists() and json.loads(riding_receipt.read_text(encoding='utf-8-sig')).get('installed',False)
    row('Stable horse route execution',['world/horse_routes.gd','net/server_world.gd','net/DaocClient.cs','zone_viewer.gd'],['Godot/live_gateway.gd','Godot/live_riding_state.gd','Godot/live_travel_routes.gd','UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeLiveRidingController.cpp'],'installed_bounded_itinerary_owner_review_pending' if riding_installed else 'private_candidate_final_regressions_pending','Original server Riding0xC8, posed and instance-scaled saddle, original ride_horse, mounted input/dismount, original hoof sounds and unavailable-destination purchase gate. Only completed in-bounds Carsten-to-Druim-Ligen itinerary; no unrestricted cross-zone, personal mounts, boats or multiple seats claim.')
    row('Full keyboard/settings interface',['ui/keybinds.gd','ui/options_window.gd','ui/boot_settings.gd'],['UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeOptions.cpp'],'partial_sound_page_only','Default movement keys are restored; editable presets and the remaining original settings pages require their own package.')
    row('Guild and emblem windows',['ui/guild_window.gd','ui/emblem_window.gd'],['Godot/visual_bridge.gd'],'no_explicit_bridge_window_contract_found','Review original packets, permissions and UI together before implementing. No guild state snapshot is currently advertised.')
    row('Realm war map and siege windows',['ui/warmap_window.gd','ui/siege_window.gd'],['Godot/visual_bridge.gd'],'no_explicit_bridge_window_contract_found','Separate from the current local M zone map; prioritize with the relevant world/RvR systems.')
    result=dict(passed=True,scope='Source inventory and explicit contract comparison, not end-to-end migration acceptance',original_ui_source_count=len(surfaces),original_ui_sources=[str(p) for p in surfaces],bridge_actions=actions,snapshot_metadata=metadata,features=rows,input_hashes=inputs,next_package='CLIENT-CONTROLS: audit original editable keybind/settings UI, then close one bounded controls package' if riding_installed else 'CLIENT-LIVE-RIDING: finish current candidate regressions and receipt installation',normal_installation_modified=False,database_modified=False)
    out=workspace/'Reports/client_coverage';out.mkdir(parents=True,exist_ok=True);(out/'coverage.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    assert all(digest(Path(p))==sha for p,sha in inputs.items());return dict(passed=True,original_ui_sources=len(surfaces),bridge_actions=len(actions),metadata_fields=len(metadata),next_package=result['next_package'],report=str(out/'coverage.json'))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['workspace','install']:p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();print(json.dumps(audit(a.workspace.resolve(),a.install.resolve())))
