# Client coverage review, 6 November

The original local Godot client has 27 UI source files. The current bridge transport advertises 57 gameplay actions and 21 snapshot metadata fields. These counts describe code surfaces, not a completion percentage or full end-to-end acceptance.

Run `audit_client_coverage.py --workspace ... --install ...` to reproduce the source inventory, feature evidence and input hashes in `Reports/client_coverage/coverage.json`.

Recent scoped movement/audio deliveries have separate installed proofs and owner checklists. Character creation, equipment, quickbars, merchants, trainers, journal, vault, party and Realm Exchange have explicit source paths through the bridge, but source presence alone does not certify all class/item/world combinations. Appearance acceptance remains separate. Realm Exchange is the marketplace, not proof of player-to-player trading.

Confirmed gaps or partial surfaces:

- Original local `/face`, `/follow`, `/stick` now have a native controller, original stopping ranges, state cancellation and real-server evidence. Owner accepted face/follow/stick and cancellation on 7 November; direct movement does not include obstacle pathfinding.
- Bounded live stable transport is now installed: original Riding0xC8, actual posed/instance-scaled saddle, original ride_horse animation, server-owned movement, Space and /dismount, original hoof audio, grounded recovery and unavailable-route purchase gating. The completed Carsten-to-Druim-Ligen itinerary stays within Connacht; five routes outside the loaded world remain unavailable. This does not close unrestricted cross-zone stable travel, personal mounts, boats or multiple seats. Owner accepted the reported Carsten ticket journey on 7 November. See LIVE-RIDING-DELIVERY.md.

- Esc provides sound and a bounded editable movement/tracking controls page (two slots, capture, persistence, sensitivity/inversion). See KEY-CONFIGURATION-DELIVERY.md. Original full presets, remaining interface/quickbar key editing and other settings pages remain separate coverage gaps.
- Guild/emblem and realm-war/siege windows have original sources but no explicit bridge window contract in the current snapshot metadata. Review packets, permissions, original UI and relevant world support together.
- Quest interface modernization and expansion world-population import remain deferred according to the owner's instructions.

The next bounded package continues CLIENT-CONTROLS with existing interface and quickbar bindings. Preserve current defaults, original dispatch, shared settings and safe text/UI focus. Do not expand into unrelated guild/RvR/world systems while closing this block.
