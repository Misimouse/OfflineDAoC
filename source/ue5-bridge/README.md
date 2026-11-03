# Godot → Unreal Engine visual bridge

Source snapshot of the Connacht/Ardee integration, 3 November 2026. This is a development prototype within the OfflineDAoC fork, not a new official OfflineDAoC release. It inherits the repository's GPL-3.0 license; see ../../LICENSE and ../../THIRD_PARTY.md.

The original OfflineDAoC server and Godot network client retain gameplay authority. Godot runs headlessly and sends bounded, versioned snapshots over loopback TCP. The Unreal runtime plugin renders entities, equipment and effects and returns validated player commands to the original protocol.

## Contents

- `Godot/`: gateway, entity adapter, gameplay/UI state and Godot checks. `live_gateway.gd` forwards real NPC equipment events, including tint, emblem and permanent effect IDs.
- `UnrealPlugin/DAoCVisualBridge/Source/`: runtime C++ plugin, classic UI, camera/input, selection, movement/collision handling, equipment, animations and original effect rendering. Native acceptance entry points are included.
- `Launcher/`: normal-login/logout orchestrator; credentials are obtained in memory from the installation's own launcher provider and are not printed or copied to this folder.
- `Client/` and `GMCombatTest/NativeHost/`: project descriptors and source-host configuration. No imported assets or binaries.
- `ServerOverlay/`: three source differences against fork commit `049c92819ba7cfd13e1662d2e31fe0f21c619511`. Review and apply deliberately to `source/server`; this directory does not deploy a server.
- Root Python tools: export/import, installation, diagnostics and acceptance tools. They require locally generated assets/catalogues or fixtures as appropriate. Historical finalizers and installers are developer tools, not an automatic upgrade path.
- `ProtocolQA/`: isolated protocol test tools. Their runtime, credentials, databases, traces and run directories are intentionally absent.

## Local setup

Windows, Godot .NET 4.7.2, .NET 10 SDK and Unreal Engine 5.8 were used for this snapshot. Set:

```powershell
$env:DAOC_INSTALL = 'C:/Games/OfflineDAoC/playable-v0.37c-classic'
$env:DAOC_UE_ENGINE = 'C:/Program Files/Epic Games/UE_5.8/Engine'
$env:DAOC_ART_PROJECT = 'C:/Projects/DAoC-Enhanced-Unreal'
python prepare_source_workspace.py
python -m unittest -v test_protocol.py
dotnet build Launcher/BridgeLauncher.csproj -c Release
```

The local workspace helper copies only plugin source/descriptor into the two hosts and creates output directories. It does not start a game/server, copy credentials, link art folders or install binaries. Launch the normal server yourself before `START-BRIDGE.cmd`. `--character=<name>` selects a character; no personal character name is built into this snapshot.

Full game execution requires your own local game installation, converted content, private Unreal map and generated `models*.json`, `equipment_catalog*.json`, `collision_catalog.json` and source-task metadata. These are not shipped in Git. Configure `bridge_config.json` and the project/map for that workspace. The supplied Ardee destination identifies the laboratory map and does not include it. `Client/DAoCBridgeClient.uproject` also refers to the privately installed Nwiro plugin; the minimal native host requires only this bridge plugin.

Do not run all installer or live-test scripts blindly. An installer may target a local client and must be reviewed, backed up and used only with that client closed. Protocol QA requires a disposable database bearing `CodexQaIsolationMarker`; do not point it at a played database. Source helper paths come from `bridge_paths.py` and the environment. Old diagnostic snippets retained inside finalizers use generic example paths and may need local adaptation.

## Implemented snapshot

- Hibernia character selection and creation use the original server roster and race/class/name rules. Creation checks global name availability with the original name-check packet before submitting a character; stale/duplicate replies and timeouts cannot submit it twice. New characters start with default appearance and class-based starting attributes. The launcher normally opens this menu; `--character=<name>` retains direct entry and `--character-menu` explicitly requests selection. Game access still targets the Connacht laboratory. Apply the accompanying realm-queue update and `character_list_pending()` helper in `source/new-client/godot/game/net/server.gd` when porting this menu; preserve any unrelated local changes to that script.

- Shared input: idle right-drag orbit, two-button forward movement, wheel zoom and F11 first-person view. Death and seated facing remain locked.
- Original zone point-light positions, colours and radii travel independently of NPCs and buildings. Unreal creates bounded, shadowless transient lights; brightness is an engine approximation, and day/night scaling remains pending. The current gateway is still restricted to zone 207.
- Merchant windows block world selection across their scrollbar. NPC conversations use one head bubble with keyword replies. Door fixtures survive streamed actor renaming through spatial matching, and private colliders follow level load/unload. Door geometry/catalogue generation is still required when adding another region.

- Original server-driven combat, death/release, selection/interactions and classic UI state, with viewport resizing and English game text.
- Realm Exchange browse/search, original item icons, purchase confirmation, listing chests, price changes, withdrawal and sale-proceeds collection. Its window reuses the original granite artwork and fonts. Item and money changes come from the original server; stale window/item identities and pending operations are checked before forwarding commands. Owner prices retain the original client's remembered-price behavior, including an unknown value when no local quote is available. This does not add exchange brokers to an art map or change world data.
- Original cloaks and raised hoods for the ten Hibernian race/sex figures, including dye, guild patterns/logos, hidden-cloak flags and hair coverage. Remote equipment retains the original hood/visibility flags. The independent inventory figure frames its body and equipment bounds so large figures fit and small figures remain readable.
- Weapon/staff/shield and NPC equipment, original attachment references, seated-camera facing lock and training-dummy support.
- 39 flexible weapon definitions with original clips and independent action clocks; 132 original dye IDs; original shield emblem composition; 94 original permanent weapon effects.
- Bounded original spell meshes/particles and weapon-local effects; permanent effect limits of 8/16/24 by quality, local player priority and cleanup on unequip/despawn/session end.
- Pet visual/command integration, with original protocol authority.

Run `prepare_merchant_ui.py` alongside the existing classic UI asset preparation to include the merchant skin. The merchant uses the same item icon sheets as the inventory.

The current bridge also includes an independent, frozen inventory figure with rotation controls, explicit equip/unequip actions and the original merchant window layout, icon lookup and coin fields. Original-server tests cover equipment moves, purchasing, selling and the horse-ticket icon. Modular armour, cloaks and helmets support the ten Hibernian figures already exported for Connacht, with original textures, mesh variants and animation skeletons; individual character face/hair customization remains separate work. Two texture names are absent in the source content.

To generate the optional modular armour library, run `Godot/export_modular_armor.gd` with the local Godot project and output path, then `prepare_modular_armor.py` and `import_modular_armor_unreal.py` in the private Unreal host. Inspect and test the generated candidate catalogues before activating them. Imported assets stay out of Git.

For cloak-capable figures, use `Godot/export_cloaked_figures.gd --output=<workspace>/SourceCosmetics --races=cel_m,cel_f,elf_m,elf_f,fir_m,fir_f,lur_m,lur_f,syl_m,syl_f`, passing those arguments after Godot's `--`. It requires the existing original armour/emblem texture libraries. Run `import_cloaked_figures_unreal.py` from that workspace in the private Unreal host. It creates separate assets and writes `models_cloaks_candidate.json` and `equipment_catalog_cloaks_candidate.json`; it does not activate them. The exporter preserves custom vertex-channel encodings needed for emblem UVs, and the new material builder checks every graph connection.

Converted assets and generated catalogues needed for those definitions are deliberately excluded. The snapshot is not a claim of complete DAoC parity: complete face/armour appearance, every rare NIF controller, every class, every region and packaged/cooked distribution remain incomplete.

## Validation provenance

Before export, the local installed client passed 236 spell/permanent-weapon-effect checks, 1,395 equipment/dye/emblem/flexible-weapon checks and 294 general UI/inventory/combat/posture checks. These groups overlap. Godot transport checks passed. An isolated original-server test confirmed player/NPC equipment IDs, tints, an NPC emblem and permanent effects; its packets were replayed successfully by the installed Unreal client, including a small rendered scene. The disposable fixture was restored and normal shutdown confirmed. Private reports and captures are not published.

The 3 November input/lighting correction passed 313 UI/inventory/combat/posture/equipment checks, 72 native window/input checks, 23 Godot transport checks and 21 world-message checks. A read-only replay of the actual streamed Connacht map found both Ardee door groups and all 28 source point lights; matching interior captures were compared with those lights disabled/enabled. These are automated/replay checks, not a claim of complete play validation. Character trail reduction still needs a real movement review.

Source-package validation is recorded separately in `SOURCE-VALIDATION.md`. Native asset-dependent suites need regenerated local catalogues/fixtures; a clean source checkout alone does not provide them. Ardee FPS are not certified by the empty-scene render or headless tests. Earlier measurements were contended by other editor processes.

The character-menu addition was checked separately: 16 lobby rules, 7 original-server realm-queue regressions, 13 native menu checks, a rendered TCP snapshot replay, six disposable-server creation/entry checks and 142 ten-figure armour checks (144 with the Sylvan female preview). The 313 general regressions and 72 window/input checks also passed. The realm queue now accepts an authoritative reply even when a locked account returns a different realm; creation stays disabled until initial roster requests finish.

The Realm Exchange addition passed 46 Godot state checks, 24 transport checks, 34 rendered native UI checks, 314 general regressions and 72 window/input checks. A separate disposable original-server test used two characters to list an item, set its price, find and purchase it, verify the exact item/coin transfer, collect the seller's proceeds and withdraw an unsold item (eight checks). The isolated database was restored after normal shutdown. These checks do not replace manual play validation. The shared action-icon widget now initializes optional brush and slot arguments explicitly; inventory/container revisions are synchronized before publishing newly opened exchange state.

`ProtocolQA/prepare_lobby_project.py` prepares the isolated headless gameplay project used by the exchange test. It accepts an installation with the realm-queue patch already present, copies gameplay scripts, and shares content/import caches for reading. Run it only after preparing a marker-protected disposable QA runtime; do not open that shared-cache project in the Godot editor. `ProtocolQA/verify_exchange_real.py` requires that project and never targets a played database.

The cloak integration passed 262 native checks across ten figures and 266 checks with rendered preview/framing validation, including raised hoods on firbolg and lurikeen figures. Render tests also reject material-compilation failures; their extra lights exist only in the temporary acceptance scene. Nine separate original-server checks verified player equip/unequip, `/hood`, `/cloak off`, `/cloak on`, and NPC cloak/emblem/visibility data, followed by normal shutdown and restoration of the disposable database. The 314 general, 72 window/input, 34 market and 26 transport checks passed with the candidate figures. Manual play validation remains separate.

The shield-emblem shader repair passed 1,118 equipment/emblem checks with D3D11 on both the candidate and installed client, with no material-compilation errors. The earlier parameter-only checks passed even with a broken Clamp input, so `ProtocolQA/verify_shield_material.py` also checks the full engine log. `shield_emblem_material.py` now checks every graph connection and preserves the original surface UV0, logo UV1 and pattern UV3. To repair an existing private workspace, copy that helper and `repair_shield_material_unreal.py` beside its catalogues and run the latter in its isolated Unreal host. It creates `M_OriginalShieldEmblem_v02` and an inactive `equipment_catalog_shield_candidate.json`; activate only after validation and a catalogue backup. Original textures, the old material and maps remain untouched.

Original helmets cover 540 assemblies across the ten Hibernian figures: ordinary race-specific attachments, circlets with original hair, helmet hair morphs, and full-head replacements. A visible raised hood or hidden-helmet flag removes the helmet assembly and restores the appropriate face/hair. Unsupported models retain the original face. The inventory preview copies the accessory onto its own frozen figure. Export with `Godot/export_helmet_figures.gd --output=<workspace>/SourceHelmets --races=cel_m,cel_f,elf_m,elf_f,fir_m,fir_f,lur_m,lur_f,syl_m,syl_f` after Godot's `--`; optional `--models=` limits a diagnostic sample. Run `ProtocolQA/verify_helmet_exports.py <workspace>/SourceHelmets`, then `import_helmet_figures_unreal.py` beside the private catalogues. Import creates separate `Helmets_v01` assets and inactive `equipment_catalog_helmets_candidate.json`. Each helmet skeleton is checked against its original figure before activation. This currently uses the same default per-race appearance as the body library; complete individual face/hair customization remains pending.

Helmet validation passed 2,462 native checks and 2,468 with rendered preview validation, including open helmets, circlets and full-head replacements. Seven disposable original-server checks verified NPC helmet data, equip/unequip and `/helm` visibility. Eight separate checks used a normal-privilege Magician: cloth equipped, leather and plate produced the original server rejection and remained in the backpack without replacing cloth. Both isolated databases were restored after normal shutdown. Equipment permissions stay server-authoritative: ordinary class/realm rules and the original GM equipment exception are preserved. The GM combat-test toggle is not a general privilege downgrade. The 314 general regressions, 72 window/input and 34 exchange checks also passed. `ProtocolQA/verify_helmets_native.py` accepts explicit bridge/editor paths and can repeat candidate or installed native/render checks. Automated validation does not replace manual play review.

Original armour/weapon skill refusals now finish the outstanding equipment request immediately and display the original English reason. The bridge changes no item, coin or item token on a refusal. Exact server replies apply only to equipment moves; NPC speech, unrelated messages, purchases and backpack-only moves cannot acknowledge them. Validation covers 11 refusal-state checks, 35 inventory, 25 vault, 46 exchange and 26 transport checks, gateway parsing, and ten disposable-server checks including immediate leather/plate refusal for a normal-privilege Magician. Server equipment rules and the GM exception remain unchanged.

## Original appearance preparation (inactive)

Character creation still uses the default appearance. The separate preparation tools retain original per-race heads and all non-null hairstyle meshes, including sparse glTF morph targets, instead of merging away their face/hair deformation data. They do not change the active body or equipment catalogues, creation UI, server rules, or maps.

Export `Godot/export_appearance_parts.gd` with `--output=<workspace>/SourceAppearance --races=cel_m,cel_f,elf_m,elf_f,fir_m,fir_f,lur_m,lur_f,syl_m,syl_f` after Godot's `--`. Run `ProtocolQA/verify_appearance_exports.py <workspace>/SourceAppearance --report=<workspace>/Reports/appearance/export_verification.json`. The validator checks glTF headers, morph data (including sparse accessors), UVs, skinning, indices and original PNG dimensions.

Set `DAOC_BRIDGE_WORKSPACE` to the private bridge workspace containing `models.json`, `equipment_catalog_v01.json` and `SourceAppearance`. Run `import_appearance_parts_unreal.py` with Unreal Python, then `prepare_appearance_materials_unreal.py`. The importer checks each original bone's reference position/rotation against its active body. Textures and morph-capable material masters are isolated under `Appearance_v01`; `appearance_catalog_candidate.json` remains inactive. `appearance_material_unreal.py` preserves original face/eye/tattoo multiplication, hair cutout and starter-clothing skin masks.

Local preparation verified ten figures, 62 parts, 393 morph targets, 23,262 vertices and 286 textures. Five unsaved editor captures checked example face/hair/eye/tattoo/tint and morph combinations; this is a resource proof, not complete customization or an installed creator feature. Connecting validated choices to creation, persistence, animated accessories, helmets/hoods and the inventory miniature remains pending. Keep the existing default-appearance behavior until that integration passes its own tests.

## Upstream and maintenance

The original author has put OfflineDAoC on hold. Source changes after 0.37c exist upstream at `12992146a16dc888f91ec611d18d9d891d3e11e1`; they have been reviewed but not merged wholesale into this snapshot. They include navigation-memory fixes, Godot loading fixes, appearance and gameplay changes. Whole-file replacement can remove this fork's art hooks and introduce dependencies; port and test by feature.

Never commit played databases, accounts, credentials, bot rosters, traces/logs, backups, generated art, imported Unreal assets, engine files or binaries. Preserve existing gameplay rules and distinguish automated acceptance from real in-game verification.
