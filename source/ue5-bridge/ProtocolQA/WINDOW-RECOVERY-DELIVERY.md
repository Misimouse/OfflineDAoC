# Existing window recovery

This bounded client package connects the original Options / Windows behavior to six existing native windows: character panel, combat chat, mini group, local zone map, quest journal and guild roster. Lit buttons indicate open windows. Reopening uses the retained position. The guild button uses the existing server query; it does not invent roster contents or change guild permissions.

Reset Window Layout restores the existing native window positions, chat sizes, quickbar orientations and default local visibility. It also brings the pet, concentration, vault and trainer positions back within the viewport without creating a pet, opening a keeper service, granting skills or starting a transaction. Inventory, quickbar assignments, chat filters, key bindings and interface scale remain unchanged. Layout saving uses the existing character-specific layout file.

The original Godot window inventory contains twenty surfaces. This package connects the six existing closable windows above; always-visible/server-driven windows retain their existing behavior. Compass, time, information, war map and raid surfaces are outside this delivery. The existing local map remains distinct from the realm war map. This is not a claim of full Options parity.

## Acceptance

`audit_window_recovery.py` records the original window list, implementation mapping and source hashes. `verify_window_recovery_native.py` runs an offscreen native client with an isolated character layout and settings. It clicks the actual Slate button delegates, checks retained locations and restored defaults, preserves custom chat filters, checks the original guild query, rejects unknown window IDs, reconstructs the UI from its saved layout, verifies unchanged key/scale files and captures the actual Windows page.

`verify_window_recovery_regressions.py` verifies this candidate against interface scale, hover descriptions, item handover, emblem, guild, display, controls, movement, landing, tracking, water and the seven audio/UI cases. `install_window_recovery.py` requires matching build evidence and receipt guards, backs up exactly seven native targets and supports bounded rollback. It does not write Godot gameplay files, server libraries or the played database.

Owner review after installation: open Esc / Windows; close and reopen Character Panel, Combat Chat, Group, Map and Quest Journal. Move a few windows, reopen them, then use Reset Window Layout and check their positions. Confirm that the quickbar actions and chat filters remain as before. Guild contents still depend on the server response. Automated acceptance and owner gameplay approval are recorded separately.

Installed on 2026-11-08 after 53 candidate checks, all 13 regression packages (including 436 scale and 265 audio/UI checks), and 217 synthetic receipt guards passed. The installed client passed the same 53 recovery checks. Exactly seven native files were replaced with backups. Owner gameplay review remains pending.
