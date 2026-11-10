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
    guild_receipt=workspace/'GuildWindowLab/installed.json';guild_installed=guild_receipt.exists() and json.loads(guild_receipt.read_text(encoding='utf-8-sig')).get('installed',False)
    config_receipt=workspace/'KeyConfigurationLab/installed.json';config_installed=config_receipt.exists() and json.loads(config_receipt.read_text(encoding='utf-8-sig')).get('installed',False)
    interface_receipt=workspace/'InterfaceKeysLab/installed.json';interface_installed=interface_receipt.exists() and json.loads(interface_receipt.read_text(encoding='utf-8-sig')).get('installed',False)
    row('Full keyboard/settings interface',['ui/keybinds.gd','ui/options_window.gd','ui/boot_settings.gd'],['UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeOptions.cpp'],'partial_editable_66_supported_controls' if guild_installed else 'partial_editable_65_supported_controls' if interface_installed else 'partial_editable_movement_controls' if config_installed else 'partial_sound_page_only','Two bindings per supported action plus sensitivity/inversion are delivered. The interface/quickbar successor covers 65 supported actions, with the guild successor adding a 66th; full original presets, character-specific maps and remaining settings pages remain gaps.')
    display_receipt=workspace/'DisplaySettingsLab/installed.json';display_installed=display_receipt.exists() and json.loads(display_receipt.read_text(encoding='utf-8-sig')).get('installed',False)
    row('Basic display settings',['ui/options_window.gd','ui/boot_settings.gd'],['UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeDisplaySettings.cpp','UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeDisplayOptions.cpp'],'installed_owner_monitor_review_pending' if display_installed else 'private_candidate_final_evidence_pending','Resolution, mode and original frame caps; confirmed persistence, rollback timer and restart override. UE borderless fills desktop. Rendering presets and optimization remain separate.')
    guild_receipt=workspace/'GuildWindowLab/installed.json';guild_installed=guild_receipt.exists() and json.loads(guild_receipt.read_text(encoding='utf-8-sig')).get('installed',False)
    row('Guild roster and alliance',['ui/guild_window.gd'],['Godot/guild_state.gd','UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeGuild.inl'],'installed_owner_review_pending' if guild_installed else 'candidate','Original UI, authoritative social roster, pages/sort/offline members and confirmed commands. Offline DOL roster cache correction retains permissions. Shift+G is editable.')
    emblem_receipt=workspace/'EmblemWindowLab/installed.json';emblem_installed=emblem_receipt.exists() and json.loads(emblem_receipt.read_text(encoding='utf-8-sig')).get('installed',False)
    row('Guild emblem editor',['ui/emblem_window.gd'],['Godot/emblem_picker_state.gd','UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeEmblemPicker.inl'],'installed_owner_review_pending' if emblem_installed else 'private_candidate_final_evidence_pending','Original editor, 255 logos and original packet. Real server controls permissions and free/paid choice; item handover for equipped emblems remains separate.')
    handover_receipt=workspace/'ItemHandoverLab/installed.json';handover_installed=handover_receipt.exists() and json.loads(handover_receipt.read_text(encoding='utf-8-sig')).get('installed',False)
    row('Inventory item handover to NPC',['ui/inventory_sheet.gd','net/DaocClient.cs'],['Godot/inventory_state.gd','UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeItemHandover.cpp'],'installed_owner_review_pending' if handover_installed else 'private_candidate','Original MoveItem NPC destination, actual viewport picking and carried item identity. Real emblemeer cost/cancel/application/save and level/rank/money refusals verified. Original server retains worn-item smith exception. No ground fallback or player trade; other services need their own checks.')
    poison_receipt=workspace/'WeaponPoisonLab/installed.json';poison_installed=poison_receipt.exists() and json.loads(poison_receipt.read_text(encoding='utf-8-sig')).get('installed',False)
    row('Original poison application',['ui/inventory_sheet.gd'],['Godot/inventory_state.gd'],'installed_owner_review_pending' if poison_installed else 'not_yet_verified','Original MoveItem onto occupied weapon; DOL retains Envenom, level, ability, combat and consumption rules. Isolated tests verify application/refusals/save; no skills or items granted to played characters.')
    hover_receipt=workspace/'HoverDetailsLab/installed.json';hover_installed=hover_receipt.exists() and json.loads(hover_receipt.read_text(encoding='utf-8-sig')).get('installed',False)
    row('Original hover descriptions',['ui/item_tooltip.gd','net/server.gd'],['Godot/classic_ui_state.gd','UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeClassicUI.cpp'],'installed_owner_review_pending' if hover_installed else 'private_candidate','Original item/skill/effect cache keys, live server detail and stale identity guards; explicit inspection and dragging retained.')
    row('Realm war map and siege windows',['ui/warmap_window.gd','ui/siege_window.gd'],['Godot/visual_bridge.gd'],'no_explicit_bridge_window_contract_found','Separate from the current local M zone map; prioritize with the relevant world/RvR systems.')
    result=dict(passed=True,scope='Source inventory and explicit contract comparison, not end-to-end migration acceptance',original_ui_source_count=len(surfaces),original_ui_sources=[str(p) for p in surfaces],bridge_actions=actions,snapshot_metadata=metadata,features=rows,input_hashes=inputs,next_package='CLIENT-ITEM-DYES: verify original backpack dye combination and authoritative color/consumption/save' if poison_installed else 'CLIENT-NPC-SERVICES: verify original blacksmith repair confirmation, worn-item eligibility, payment and persistence' if handover_installed else 'CLIENT-ITEM-HANDOVER: audit original inventory-to-NPC transaction for emblem application before broader player trade' if emblem_installed else 'CLIENT-EMBLEM: original emblem editor, server permissions and confirmed cost' if guild_installed else 'CLIENT-GUILD: original roster/alliance window and server-authorized commands' if display_installed else 'CLIENT-DISPLAY: original basic window/resolution/frame-cap settings' if interface_installed else 'CLIENT-CONTROLS-UI: migrate existing interface/quickbar bindings' if config_installed else 'CLIENT-CONTROLS: audit original editable keybind/settings UI, then close one bounded controls package' if riding_installed else 'CLIENT-LIVE-RIDING: finish current candidate regressions and receipt installation',normal_installation_modified=False,database_modified=False)
    if hover_installed:result['next_package']='CLIENT-VAULT: verify original keeper access, deposit, withdrawal and saved slots'
    if (workspace/'VaultPersistenceLab/verified.json').exists():result['next_package']='CLIENT-CONSUMABLES: verify original potion use, refusals, charge count and save'
    consumable_receipt=workspace/'ConsumableUseLab/installed.json';consumable_installed=consumable_receipt.exists() and json.loads(consumable_receipt.read_text()).get('installed',False)
    if consumable_installed:
        row('Original consumables and charge descriptions',['net/server.gd','ui/quickbar.gd'],['Godot/classic_ui_state.gd'],'installed_owner_review_pending','Original UseSlot, level/posture/cooldown/charge rules; refresh authoritative item descriptions after use without predicting charges.')
        result['next_package']='CLIENT-UI-SCALE: audit original interface scale preference and native viewport/layout behavior'
    scale_receipt=workspace/'UIScaleLab/installed.json';scale_installed=scale_receipt.exists() and json.loads(scale_receipt.read_text()).get('installed',False)
    if scale_installed:
        row('Original interface scale',['ui/options_window.gd','ui/game_ui.gd'],['UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeInterfaceSettings.cpp','UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeInterfaceOptions.cpp'],'installed_owner_review_pending','Original 60-160% slider applies on release, persists across processes and reflows existing windows with viewport fit. Other original Interface/Options settings remain separate.')
        result['next_package']='CLIENT-WINDOW-RESTORE: audit original Options / Windows recovery and reset against existing native windows; do not add unavailable world services'
    windows_receipt=workspace/'WindowRecoveryLab/installed.json';windows_installed=windows_receipt.exists() and json.loads(windows_receipt.read_text()).get('installed',False)
    if windows_installed:
        row('Original window recovery',['ui/options_window.gd','ui/game_ui.gd'],['UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeWindowRecovery.cpp'],'installed_owner_review_pending','Six existing closable windows, retained positions and reset of native layout defaults; custom chat filters, quickbar actions, key bindings and scale retained. Unavailable original surfaces remain separate.')
        result['next_package']='CLIENT-VITALS: audit the confirmed positive absolute-health versus rounded-zero-percent ambiguity against original Godot/DOL state, with isolated proof before changing runtime'
    vitals_receipt=workspace/'PlayerVitalsLab/installed.json';vitals_installed=vitals_receipt.exists() and json.loads(vitals_receipt.read_text()).get('installed',False)
    if vitals_installed:
        row('Positive absolute player health',['net/server_world.gd'],['Godot/player_combat_state.gd','Godot/player_release.gd','Godot/combat_audio_state.gd','Godot/weapon_mode_audio_state.gd','UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgePlayerStatus.cpp'],'installed_owner_review_pending','Original positive absolute HP remains alive at rounded zero percent; actual Status/Death/Revive retain authority. Real one-HP, potion and native corpse/return checks passed; no invented local damage or resurrection.')
        result['next_package']='CLIENT-PARTY: audit and verify original group invite/accept/target/remove/leave using ordinary disposable players and current bridge; preserve original server permissions'
    party_proof=workspace/'PartyLifecycleLab/verified.json'
    if party_proof.exists() and json.loads(party_proof.read_text()).get('passed',False):
        row('Original ordinary-player group lifecycle',['ui/panel_sheets.gd'],['Godot/party_state.gd','Godot/interaction_state.gd'],'installed_existing_runtime_verified_owner_review_pending','Nine real checks with ordinary players; decline/accept, roster vitals, member target, leader permissions, stale roster, removal and leave. 43 state and 79 installed native checks. No runtime replacement; cross-region/raid behavior remains separate.')
        result['next_package']='CLIENT-CONCENTRATION: original concentration list, pool, owner-bound cancellation and confirmed effect removal; inspect existing Godot/DOL implementation before changes'
    concentration_proof=workspace/'ConcentrationLifecycleLab/verified.json'
    if concentration_proof.exists() and json.loads(concentration_proof.read_text()).get('passed',False):
        row('Original concentration lifecycle',['net/server.gd','ui/game_ui.gd'],['Godot/concentration_state.gd'],'installed_existing_runtime_verified_owner_review_pending','14 real checks with ordinary accounts, two self buffs and foreign cancellation refusal; 26 state and 82 installed native checks. Pool, list indices, owners, icons and refunds retain server authority. Cross-player casting geometry and general timed effects are outside this package.')
        result['next_package']='CLIENT-PETS: audit original owned pet summon/commands/release and stale identity; verify disposable ordinary-player behavior before choosing changes'
    pet_proof=workspace/'PetLifecycleLab/verified.json'
    if pet_proof.exists() and json.loads(pet_proof.read_text()).get('passed',False):
        row('Original owned-pet lifecycle',['net/server.gd','ui/game_ui.gd'],['Godot/pet_state.gd'],'installed_existing_runtime_verified_owner_review_pending','17 real ordinary-account checks, 28 state and 80 installed native checks. Original summon/model/ownership, seven orders, mode acknowledgements, release and safe quickbar rebinding. Live combat/navigation and every class pet remain separate.')
        result['next_package']='CLIENT-COMPASS: audit original compass art, character heading, visibility and retained layout before adding the missing native surface'
    ground_receipt=workspace/'GroundTargetLab/installed.json'
    if ground_receipt.exists() and json.loads(ground_receipt.read_text()).get('installed',False):
        row('Original physical ground target',['zone_viewer.gd','net/DaocClient.cs'],['Godot/ground_target_state.gd','Godot/live_gateway.gd'],'installed_owner_review_deferred','Ctrl+G configurable; original yellow geometry/bitmap; physical ray and independent terrain sight; original ground target and ability header bits. 26 state,21 private live checks,8 production header checks,26 native checks; original navigation rules retained. No full siege/world frontier claim.')
        result['next_package']='CLIENT-SIEGE-WORLD-ANIMATION-AUDIT'
    impact_receipt=workspace/'SiegeImpactLab/installed.json'
    if impact_receipt.exists() and json.loads(impact_receipt.read_text()).get('installed',False):
        row('Original fixed-world siege impacts',['net/server_world.gd','combat/spell_fx.gd'],['Godot/spell_visual_state.gd','UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeSpellVisuals.cpp'],'installed_owner_review_deferred','Original effect-to-target-stage mapping, server point/timer, independent noncolliding world anchor. 25 state,15 private live,58 native plus236 weapon regression checks. Flight/audio/frontier world remain separate.')
    siege_world_receipt=workspace/'SiegeWorldLab/installed.json'
    if siege_world_receipt.exists() and json.loads(siege_world_receipt.read_text()).get('installed',False):
        row('Original siege world bodies and animation',['weapon_models.gd','npcs/npc.gd','net/server_world.gd'],['Godot/siege_visual_state.gd','UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeAnimation.cpp'],'installed_owner_review_deferred','Ten original bodies, seven animated and three originally static. Original server announcements, constant idle preservation, owner/non-owner lifecycle. 22 state,24 real,125 native checks. Projectile impacts/sound and full frontier world remain separate.')
        result['next_package']='CLIENT-SIEGE-IMPACT-EFFECTS'
    if impact_receipt.exists() and json.loads(impact_receipt.read_text()).get('installed',False):result['next_package']='CLIENT-DIVE-CLIMB-AUDIT'
    if (workspace/'DiveClimbLab/audit.json').exists():
        row('Original diving and climbing contracts',['player.gd','zone_loader.gd','zone_viewer.gd'],['Godot/movement_flags_state.gd'],'audited_implementation_pending_relevant_world','Connacht diving disabled by original zone/region data; no original climb_ surfaces in its GLTFs.37 installed original ladder clips already present. Preserve surface swimming and server permissions; do not invent climbable walls or change world rules.')
        result['next_package']='CLIENT-TORCH-AUDIT'
    if (workspace/'RemotePlayerLab/verified.json').exists() and json.loads((workspace/'RemotePlayerLab/verified.json').read_text()).get('passed',False):
        row('Original remote player position and recovery',['net/DaocClient.cs','net/server_world.gd'],['Godot/decoded_world_adapter.gd','Godot/live_gateway.gd'],'installed_owner_review_deferred','Original1.127 absolute position and separate player-session recovery; two ordinary accounts verified appearance/movement/stop/sit/stand/logout.73network,69state,18real,55native pose,387NPC collision and25combat checks. No full RvR or all remote states live acceptance claim.')
        result['next_package']='CLIENT-PERSONAL-TORCH'
    torch_receipt=workspace/'PersonalTorchLab/installed.json'
    if torch_receipt.exists() and json.loads(torch_receipt.read_text()).get('installed',False):
        row('Original personal and peer torch',['player.gd','zone_loader.gd','sky_system.gd'],['Godot/personal_torch_state.gd','Godot/live_gateway.gd','UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgePersonalTorch.cpp'],'installed_owner_review_deferred','Editable Shift+T preserves Training T and saved assignments; merged persistent preference, original player action flag0x80, original day/storm weighting. Bounded white no-shadow sources.1502state,338gateway/regression,23real,486native,260controls checks and rendered off/day/night. World/building lights and character materials unchanged.')
        result['next_package']='CLIENT-NPC-VISUAL-FLAGS-AUDIT'
        for feature in rows:
            if feature['feature']=='Full keyboard/settings interface':feature.update(status='partial_editable_69_supported_controls',notes='69 supported actions, two bindings per action, saved assignment precedence. Full original presets and unsupported actions remain separate.')
            if feature['feature']=='Realm war map and siege windows':feature.update(status='installed_owner_review_deferred',notes='Original bounded realm-war/siege UI contracts delivered separately. Full frontier world and battle-scale performance remain separate.')
    if (workspace/'NpcVisualFlagsLab/installed.json').exists() and json.loads((workspace/'NpcVisualFlagsLab/installed.json').read_text()).get('installed',False):
        row('Original NPC ghost appearance',['npcs/npc.gd'],['Godot/npc_visual_flags.gd','UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeNpcGhostPresentation.cpp'],'installed_owner_review_deferred','Separate original create bit; actor-local original materials and atomic outfit fallback. 534 installed native,21 coordinator replay,16 capture checks. Not a world-model import.')
        result['next_package']='CLIENT-NPC-EFFECT-BODIES'
    if (workspace/'NpcEffectsLab/installed.json').exists() and json.loads((workspace/'NpcEffectsLab/installed.json').read_text()).get('installed',False):
        row('Original effect-only NPC bodies',['npcs/npc.gd','nif_particles.gd','nif_scene.gd'],['UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeNpcEffects.inl'],'installed_two_exported_models_owner_review_deferred','Wisp966 and Flies2020: original geometry/particles/textures, billboard/float/scale/range, bounded independent budgets, physical draw bounds for selection/names.595 installed native checks and32 captures.44 prepared resources are not44 fully accepted creatures; other warnings and Catacombs population remain separate.')
        result['next_package']='CLIENT-ORIGINAL-CONTROLS-AUDIT'
    if (workspace/'OriginalControlsLab/installed.json').exists() and json.loads((workspace/'OriginalControlsLab/installed.json').read_text()).get('installed',False):
        row('Original weapon and sprint shortcuts',['ui/game_ui.gd','net/server.gd','zone_viewer.gd'],['Godot/weapon_sprint_state.gd','UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeKeyConfiguration.cpp'],'installed_owner_review_deferred','Four editable actions; actual original UseSlot10/12/13 and DOL /sprint. Current item/generation gates, server acknowledgement, preserved saved bindings.58state,346gateway/regression,451installed native,14ordinary-server checks. No full preset activation.')
        result['next_package']='CLIENT-KEYBOARD-TURNING-AUDIT'
        for feature in rows:
            if feature['feature']=='Full keyboard/settings interface':feature.update(status='partial_editable_73_supported_controls',notes='73 supported actions; full presets, keyboard turning and remaining actions are separate.')
    if (workspace/'KeyboardTurningLab/installed.json').exists() and json.loads((workspace/'KeyboardTurningLab/installed.json').read_text()).get('installed',False):
        row('Original modern keyboard turning',['player.gd'],['UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeKeyboardTurning.h','UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeSubsystem.cpp'],'installed_owner_review_deferred','Editable Left/Right arrows, original180 degree/second turn, RMB strafe, LMB independent camera. Existing movement heading packets and seated/dead/menu/riding gates.632 candidate and installed native checks; no new server/database contract. Full classic mode/presets remain separate.')
        result['next_package']='CLIENT-GROUP-TARGET-SHORTCUT-AUDIT'
        for feature in rows:
            if feature['feature']=='Full keyboard/settings interface':feature.update(status='partial_editable_75_supported_controls',notes='75 supported actions; full presets and remaining actions are separate.')
    if (workspace/'GroupTargetKeysLab/installed.json').exists() and json.loads((workspace/'GroupTargetKeysLab/installed.json').read_text()).get('installed',False):
        row('Group targeting shortcuts and original self-first rows',['ui/player_data.gd','ui/game_ui.gd','zone_viewer.gd'],['UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeGroupTargeting.h','UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeClassicUI.cpp'],'installed_owner_review_deferred','Seven editable keypad shortcuts reuse original group_target with current OID/token. Shared self-first display order, unknown/dead slots preserved, no adjacent-target substitution.475 installed native and43 party-state checks; no new server action or database rule.')
        result['next_package']='CLIENT-GROUND-OBJECTS-AUDIT'
        for feature in rows:
            if feature['feature']=='Full keyboard/settings interface':feature.update(status='partial_editable_82_supported_controls',notes='82 supported actions; full presets and remaining actions are separate.')
    if (workspace/'GroundObjectRuntimeLab/installed.json').exists() and json.loads((workspace/'GroundObjectRuntimeLab/installed.json').read_text()).get('installed',False):
        row('Original ground objects and pickup',['net/server_world.gd','net/DaocClient.cs','weapon_models.gd'],['Godot/ground_object_state.gd','UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeGroundObjects.cpp'],'installed_rigid_models_owner_review_pending','Separate128-object budget; current token/generation, original Target then PickUp/Interact, no optimistic grant/delete.68state,361gateway/regression,12ordinary-server,437installed native checks and2captures.918actual native geometry assets cover1021rigid IDs;39animated and669missing IDs remain explicit fallback gaps.')
        result['next_package']='CLIENT-REMAINING-ORIGINAL-SELECTION-CONTROLS'
        for feature in rows:
            if feature['feature']=='Full keyboard/settings interface':feature.update(status='partial_editable_84_supported_controls',notes='84 supported actions; full presets and remaining actions are separate.')
    if (workspace/'ChatReplyLab/installed.json').exists() and json.loads((workspace/'ChatReplyLab/installed.json').read_text()).get('installed',False):
        row('Original private chat reply',['ui/game_ui.gd','net/server.gd'],['Godot/chat_state.gd','Godot/live_gateway.gd','UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeChat.cpp'],'installed_ordinary_english_owner_review_pending','Editable Ctrl+R pins explicit /send; /r and /reply use original incoming private sender.49state,434native,11ordinary-server checks; logout clears state. Existing chat UI and transport, no new server/database rules. GM/localized templates remain separate.')
        result['next_package']='CLIENT-REMAINING-ORIGINAL-INTERFACE-CONTROLS'
        for feature in rows:
            if feature['feature']=='Full keyboard/settings interface':feature.update(status='partial_editable_85_supported_controls',notes='85 supported actions; full presets and remaining actions are separate.')
    if (workspace/'InterfaceVisibilityLab/installed.json').exists() and json.loads((workspace/'InterfaceVisibilityLab/installed.json').read_text()).get('installed',False):
        row('Original interface visibility',['ui/game_ui.gd'],['UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeViewport.cpp','UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeInterfaceSettings.cpp'],'installed_owner_review_pending','Editable Alt+Z hides nineteen existing game roots without closing/recreating windows or changing saved positions. Hidden roots cannot block world pointer/camera. Options remain reachable; chat and character return restore transient visibility. No new server action or database/art resources.')
        result['next_package']='CLIENT-REMAINING-ORIGINAL-CONTROLS-AUDIT'
        for feature in rows:
            if feature['feature']=='Full keyboard/settings interface':feature.update(status='partial_editable_86_supported_controls',notes='86 supported actions; full presets and remaining actions are separate.')
    if (workspace/'ItemShortcutsLab/installed.json').exists() and json.loads((workspace/'ItemShortcutsLab/installed.json').read_text()).get('installed',False):
        row('Original item use and sale shortcuts',['ui/game_ui.gd','ui/player_data.gd'],['UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeItemShortcuts.h','UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeClassicUI.cpp'],'installed_owner_review_pending','U equips carried equipment or uses canonical item charges; editable Sell uses original merchant_sell with item/catalogue tokens. Sell starts unbound to preserve backward movement.507native,113state,24ordinary-server checks. Seven guarded files and31 delivery simulations; original server decides permissions and outcomes.')
        result['next_package']='CLIENT-REMAINING-ORIGINAL-CONTROLS-AUDIT'
        for feature in rows:
            if feature['feature']=='Full keyboard/settings interface':feature.update(status='partial_editable_88_supported_controls',notes='88 supported actions; full presets and remaining actions are separate.')
    if (workspace/'RealmWarKeysLab/installed.json').exists() and json.loads((workspace/'RealmWarKeysLab/installed.json').read_text()).get('installed',False):
        row('Original realm war shortcut',['ui/game_ui.gd'],['UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeClassicUI.cpp'],'installed_owner_review_pending','Editable Shift+M toggles existing original realm war window and original page/close requests; ordinary M remains zone map.530controls plus22window checks pass against installed client;28 simulations protect six files. No RvR-world/encounter optimization claim.')
        result['next_package']='CLIENT-CONTROLS-DISPATCH-CLOSURE'
        for feature in rows:
            if feature['feature']=='Full keyboard/settings interface':feature.update(status='partial_editable_89_supported_controls',notes='89 supported actions, fixed original equivalents and catalogue-only entries audited separately; full presets and remaining actions are not complete.')
    # Recent deliveries have independent, exact receipt validators. Do not infer
    # installation from a lab directory or an unchecked summary flag.
    for module,lab,feature,bridge,notes in [
        ('trainer_affordability_receipts','TrainerAffordabilityLab','Original trainer affordability',['Godot/trainer_state.gd'],'Original level and specialization-point cost gates; no local grants or changed server rules.'),
        ('shortcut_pages_receipts','CrossClassSwitchLab','Per-character quickbar pages',['Godot/classic_ui_state.gd'],'Fresh characters reset all three pages; existing characters restore their own saved pages and shortcuts.'),
        ('empty_inventory_receipts','CharacterInventorySwitchLab','Empty inventory initialization',['Godot/inventory_state.gd'],'Original initial MoneyUpdate establishes readiness when no item packet exists; money remains account/realm scoped. Money updates do not acknowledge item transactions.'),
        ('remote_model_size_receipts','RemoteModelRoundtripLab','Remote model-change size semantics',['Godot/decoded_world_adapter.gd'],'Original zero size retains existing size; explicit NPC sizing and equipment retention pass.105 state/regression checks repeated against installed source. Real two-player/native transformation acceptance remains separate.'),
    ]:
        import importlib
        verified=importlib.import_module(module).verify(workspace)
        receipt=verified[0] if isinstance(verified,tuple) else verified
        if receipt:
            path=workspace/lab/'installed.json';inputs[str(path)]=digest(path)
            for evidence,sha in receipt['evidence'].items():inputs[evidence]=sha
            row(feature,[],bridge,'installed_owner_review_pending',notes)
    # Server/native follow-ups add bounded evidence, not another installation or
    # a blanket claim that all classes, geometry or rendering are accepted.
    for lab,minimum,feature,bridge,notes in [
        ('EmptyInventoryTradeLab',15,'Empty inventory merchant roundtrip',['Godot/inventory_state.gd'],'Ordinary Magician buy/sell, exact saved money and original reinforced-armor refusal; no owner inventory needs to be emptied.'),
        ('NativeSightHarnessLab',28,'Grounded native sight harness',['magic_sight_relay.py'],'Real UE collision and ten correlated sight replies with original deadline. NullRHI geometry only; rendered performance and visual acceptance remain open.'),
        ('SpellMovementRoundtripLab',30,'Ordinary spell movement roundtrip',['Godot/live_gateway.gd'],'Original moving/interrupted heal costs no power; stationary recovery, healing, buff and saved progress pass. Instant/instrument/MoveCast exceptions are not generalized away.'),
    ]:
        path=workspace/lab/'verified.json'
        if not path.exists():continue
        summary=json.loads(path.read_text(encoding='utf-8-sig'))
        assert summary['passed'] and summary['checks']>=minimum,lab
        proof=Path(summary['proof']).resolve()
        assert proof.is_relative_to((workspace/lab).resolve()),lab
        evidence=json.loads(proof.read_text(encoding='utf-8-sig'))
        assert evidence['passed'] and len(evidence['checks'])>=minimum and all(evidence['checks'].values()),lab
        assert evidence['database_restored'] and evidence['normal_shutdown'] and evidence['normal_runtime_unchanged'],lab
        inputs[str(path)]=digest(path);inputs[str(proof)]=digest(proof)
        row(feature,[],bridge,'bounded_automated_evidence_owner_review_pending' if lab!='NativeSightHarnessLab' else 'geometry_harness_verified_not_render_acceptance',notes)
        result['next_package']='CLIENT-REMOTE-MODEL-ROUNDTRIP-AUDIT: inspect original model-change, equipment retention and native restoration before expanding multiplayer transformation claims'
    path=workspace/'RemoteModelRoundtripLab/roundtrip_verified.json'
    if path.exists():
        summary=json.loads(path.read_text());assert summary['passed']
        for key in ['real_proof','native_proof']:
            proof=Path(summary[key]).resolve();assert proof.is_relative_to((workspace/'RemoteModelRoundtripLab').resolve())
            evidence=json.loads(proof.read_text(encoding='utf-8-sig'));assert evidence['passed']
            inputs[str(proof)]=digest(proof)
            if key=='real_proof':
                assert len(evidence['checks'])>=25 and all(evidence['checks'].values())
                assert evidence['database_restored'] and evidence['normal_shutdown'] and evidence['normal_runtime_unchanged']
            else:
                assert evidence['checks']>=34 and not evidence['normal_runtime_modified']
                assert not evidence['rendered_acceptance'] and not evidence['weapon_attachment_acceptance']
        inputs[str(path)]=digest(path)
        row('Ordinary remote Bainshee model roundtrip',[],['ProtocolQA/verify_remote_player_real.py','ProtocolQA/verify_remote_model_native.py'],'server_roundtrip_and_native_actor_replay_verified','25 ordinary two-player checks;34 installed UE actor replay checks. Packet equipment retention is verified; per-frame native weapon/armour attachments and rendered quality remain separate.')
        result['next_package']='CLIENT-REMOTE-EQUIPMENT-MORPH-ACCEPTANCE: reproduce native per-frame attachment behavior through transformation and return before changing its policy'
    from remote_model_equipment_receipts import verify as verify_remote_equipment
    equipment,_=verify_remote_equipment(workspace)
    if equipment:
        path=workspace/'RemoteModelEquipmentLab/installed.json';inputs[str(path)]=digest(path)
        for evidence,sha in equipment['evidence'].items():inputs[evidence]=sha
        row('Native remote form weapon attachments',[],['UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeEquipment.cpp'],'installed_owner_review_pending','Known non-race player forms hide weapons and restore race attachments; NPC weapons remain. Three Bainshee native controls, ordinary Celt trace,95 equipment regressions. Rendered visual quality and every class form remain separate.')
        result['next_package']='CLIENT-PLAYER-TRADE-CONTRACT-AUDIT: compare original client assets and missing transport with DOL player-trade permissions, update/accept/cancel and inventory ownership before implementation'
    out=workspace/'Reports/client_coverage';out.mkdir(parents=True,exist_ok=True);(out/'coverage.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    assert all(digest(Path(p))==sha for p,sha in inputs.items());return dict(passed=True,original_ui_sources=len(surfaces),bridge_actions=len(actions),metadata_fields=len(metadata),next_package=result['next_package'],report=str(out/'coverage.json'))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['workspace','install']:p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();print(json.dumps(audit(a.workspace.resolve(),a.install.resolve())))
