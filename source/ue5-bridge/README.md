# Godot → Unreal Engine visual bridge

Source snapshot of the Connacht/Ardee integration, 2 November 2026. This is a development prototype within the OfflineDAoC fork, not a new official OfflineDAoC release. It inherits the repository's GPL-3.0 license; see ../../LICENSE and ../../THIRD_PARTY.md.

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

- Original server-driven combat, death/release, selection/interactions and classic UI state, with viewport resizing and English game text.
- Weapon/staff/shield and NPC equipment, original attachment references, seated-camera facing lock and training-dummy support.
- 39 flexible weapon definitions with original clips and independent action clocks; 132 original dye IDs; original shield emblem composition; 94 original permanent weapon effects.
- Bounded original spell meshes/particles and weapon-local effects; permanent effect limits of 8/16/24 by quality, local player priority and cleanup on unequip/despawn/session end.
- Pet visual/command integration, with original protocol authority.

Converted assets and generated catalogues needed for those definitions are deliberately excluded. The snapshot is not a claim of complete DAoC parity: individual face/armour appearance, every rare NIF controller, every class, every region and packaged/cooked distribution remain incomplete.

## Validation provenance

Before export, the local installed client passed 236 spell/permanent-weapon-effect checks, 1,395 equipment/dye/emblem/flexible-weapon checks and 294 general UI/inventory/combat/posture checks. These groups overlap. Godot transport checks passed. An isolated original-server test confirmed player/NPC equipment IDs, tints, an NPC emblem and permanent effects; its packets were replayed successfully by the installed Unreal client, including a small rendered scene. The disposable fixture was restored and normal shutdown confirmed. Private reports and captures are not published.

Source-package validation is recorded separately in `SOURCE-VALIDATION.md`. Native asset-dependent suites need regenerated local catalogues/fixtures; a clean source checkout alone does not provide them. Ardee FPS are not certified by the empty-scene render or headless tests. Earlier measurements were contended by other editor processes.

## Upstream and maintenance

The original author has put OfflineDAoC on hold. Source changes after 0.37c exist upstream at `12992146a16dc888f91ec611d18d9d891d3e11e1`; they have been reviewed but not merged wholesale into this snapshot. They include navigation-memory fixes, Godot loading fixes, appearance and gameplay changes. Whole-file replacement can remove this fork's art hooks and introduce dependencies; port and test by feature.

Never commit played databases, accounts, credentials, bot rosters, traces/logs, backups, generated art, imported Unreal assets, engine files or binaries. Preserve existing gameplay rules and distinguish automated acceptance from real in-game verification.
