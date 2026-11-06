# Client coverage review, 6 November

The original local Godot client has 27 UI source files. The current bridge transport advertises 56 gameplay actions and 20 snapshot metadata fields. These counts describe code surfaces, not a completion percentage or full end-to-end acceptance.

Run `audit_client_coverage.py --workspace ... --install ...` to reproduce the source inventory, feature evidence and input hashes in `Reports/client_coverage/coverage.json`.

Recent scoped movement/audio deliveries have separate installed proofs and owner checklists. Character creation, equipment, quickbars, merchants, trainers, journal, vault, party and Realm Exchange have explicit source paths through the bridge, but source presence alone does not certify all class/item/world combinations. Appearance acceptance remains separate. Realm Exchange is the marketplace, not proof of player-to-player trading.

Confirmed gaps or partial surfaces:

- Original local `/face`, `/follow`, `/stick` now have a native controller, original stopping ranges, state cancellation and real-server evidence. Owner acceptance remains pending; direct movement does not include obstacle pathfinding.
- Stable route ticket purchasing is distinct from mounting, dismounting and region transitions. Live sessions use original Riding 0xC8 packets and server-controlled steed movement (`server_world.gd`/`zone_viewer.gd`). HorseRoutes is the separate offline controller and must not replace live server authority. This is the next bounded review; establish supported route/world bounds before delivery.
- Esc currently provides the sound page. Original editable keyboard presets and remaining settings pages require their own package; restored default movement keys do not close keyboard settings.
- Guild/emblem and realm-war/siege windows have original sources but no explicit bridge window contract in the current snapshot metadata. Review packets, permissions, original UI and relevant world support together.
- Quest interface modernization and expansion world-population import remain deferred according to the owner's instructions.

The next live-riding package must decode the existing packet, preserve the original saddle/ride pose, disable ordinary walking while mounted and request original dismount on jump or `/dismount`. Mounted position/speed/route and anti-aggro remain server-owned. Exercise receipt/lost-steed/logout/death and map-boundary behaviour in isolation before normal installation. Do not claim full stable travel until routes and world transitions are covered.
