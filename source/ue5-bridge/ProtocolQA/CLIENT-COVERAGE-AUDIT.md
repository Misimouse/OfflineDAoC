# Client coverage review, 7 November

The original local Godot client has 27 UI source files. The current bridge transport advertises 66 gameplay actions and 23 snapshot metadata fields. These counts describe code surfaces, not a completion percentage or full end-to-end acceptance.

Run `audit_client_coverage.py --workspace ... --install ...` to reproduce the source inventory, feature evidence and input hashes in `Reports/client_coverage/coverage.json`.

Recent scoped movement/audio deliveries have separate installed proofs and owner checklists. Character creation, equipment, quickbars, merchants, trainers, journal, vault, party and Realm Exchange have explicit source paths through the bridge, but source presence alone does not certify all class/item/world combinations. Appearance acceptance remains separate. Realm Exchange is the marketplace, not proof of player-to-player trading.

Confirmed gaps or partial surfaces:

- Original local `/face`, `/follow`, `/stick` now have a native controller, original stopping ranges, state cancellation and real-server evidence. Owner accepted face/follow/stick and cancellation on 7 November; direct movement does not include obstacle pathfinding.
- Bounded live stable transport is now installed: original Riding0xC8, actual posed/instance-scaled saddle, original ride_horse animation, server-owned movement, Space and /dismount, original hoof audio, grounded recovery and unavailable-route purchase gating. The completed Carsten-to-Druim-Ligen itinerary stays within Connacht; five routes outside the loaded world remain unavailable. This does not close unrestricted cross-zone stable travel, personal mounts, boats or multiple seats. Owner accepted the reported Carsten ticket journey on 7 November. See LIVE-RIDING-DELIVERY.md.

- Esc provides sound and 66 supported editable controls across movement, targeting, combat, existing windows and quickbars (two slots, capture, persistence, sensitivity/inversion). See KEY-CONFIGURATION-DELIVERY.md and INTERFACE-KEYS-DELIVERY.md. Full original presets, character-specific maps, unsupported original actions and other settings pages remain separate gaps.
- Guild/alliance roster is installed with the original social packet, Shift+G and server permissions. The emblem editor is the active private candidate with original picker/packet/cost evidence. Realm-war/siege and player-to-player trade remain distinct gaps requiring their own world/server contracts.
- Quest interface modernization and expansion world-population import remain deferred according to the owner's instructions.

Basic display settings are now delivered separately: resolution, window mode and original frame caps, confirmed persistence, rollback and launcher-override restart checks. UE borderless uses desktop size. Owner monitor review remains pending. See DISPLAY-SETTINGS-DELIVERY.md. Full render-quality tuning remains separate.

The active bounded package is CLIENT-EMBLEM: original guild emblem editor, server permissions and payment confirmation. See EMBLEM-WINDOW-DELIVERY.md. Item handover to an emblemeer is separate from choosing a guild emblem. World population import remains deferred.
