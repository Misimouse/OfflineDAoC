# Client coverage review, 6 November

The original local Godot client has 27 UI source files. The current bridge transport advertises 54 gameplay actions and 19 snapshot metadata fields. These counts describe code surfaces, not a completion percentage or full end-to-end acceptance.

Run `audit_client_coverage.py --workspace ... --install ...` to reproduce the source inventory, feature evidence and input hashes in `Reports/client_coverage/coverage.json`.

Recent scoped movement/audio deliveries have separate installed proofs and owner checklists. Character creation, equipment, quickbars, merchants, trainers, journal, vault, party and Realm Exchange have explicit source paths through the bridge, but source presence alone does not certify all class/item/world combinations. Appearance acceptance remains separate. Realm Exchange is the marketplace, not proof of player-to-player trading.

Confirmed gaps or partial surfaces:

- Original `/face`, `/follow`, `/stick` are local player commands. Godot emits `track_requested`; the bridge currently forwards their text to the server and has no native target-tracking controller. This is the next bounded package.
- Stable route ticket purchasing is distinct from mounting, client-side route traversal, dismounting and region transitions. The original HorseRoutes controller is not connected to the bridge. Plan supported world bounds before migrating this.
- Esc currently provides the sound page. Original editable keyboard presets and remaining settings pages require their own package; restored default movement keys do not close keyboard settings.
- Guild/emblem and realm-war/siege windows have original sources but no explicit bridge window contract in the current snapshot metadata. Review packets, permissions, original UI and relevant world support together.
- Quest interface modernization and expansion world-population import remain deferred according to the owner's instructions.

The next target-tracking package must reuse the original selected-target rules, start/stop distances and local feedback; never substitute server bot-follow commands. Normal collision must continue to constrain motion, and manual input/death/logout must cancel tracking. Test no target, self, dead/despawned/far targets, moving targets, real obstacles and session reset before installation.
