# Original Stealth integration

The bounded original Stealth integration is installed. Owner gameplay review is deferred; this does not claim complete client parity, all stealth detection mechanics, or complete RvR validation.

The original Abilities window and quickbars expose Stealth only when the server supplies a trained specialization. Activation sends the original type-zero UseSkill packet with validated current identity, position and heading. Hover/details show the actual specialization rank without requesting an unrelated ability index. The server retains cooldowns, rejection rules, speed and Sprint restrictions. No skill or hidden state is granted locally.

The existing raw Packet signal observes local PlayerModelTypeChange: type 3/flags 8 and type 2/flags 0 confirm hidden/visible presentation. Wireframe types 0/1, malformed packets and previous character identities are ignored. Region/logout clear the state. The C# network binary and original Godot server script are unchanged.

Generic ObjectDelete also removes living players hidden by the original server. Target, native actor, mount relation and cached combat pose are cleared; original PlayerCreate restores visibility. Unrelated ground-object removal preserves other living entities.

Unreal applies separate translucent material variants only to the local avatar after equipment updates. Shared mesh assets, original materials, inventory previews and other actors are unchanged. Current skin/dye parameters, original cutouts and static material switches are retained. Repeated updates reuse their overrides; equipment replacement restores the latest outfit; reveal, unknown state and cleanup release overrides and restore the exact original material references. Unmapped materials retain their original appearance.

The lazy runtime catalogue covers 2,974 material assets from an audit of 1,983 catalogued meshes. The immutable library is generated from original material graphs and instance chains with prepare_stealth_materials_unreal.py. audit_stealth_material_coverage_unreal.py discovers coverage; prepare_stealth_runtime_catalogue.py produces the compact lookup file. Converted game assets and private capture evidence are not published in Git.

Validation:
- 18 checks with two ordinary players on an isolated original server, including original UI/quickbar activation, actual rank details, stale identity, toggle limit, speed, observer removal/reappearance, target cleanup and Sprint refusal while hidden.
- 719 state checks across 27 compatibility packages, including 31 focused Stealth checks and the existing model-transformation checks.
- 177 native entity-consumer checks using verified original living/standing status.
- 927 native material checks, including tint preservation, repeated updates, garbage collection, equipment replacement and exact restoration.
- Rendered before/hidden/revealed/background acceptance through the production local-state controller: 14 native checks and three pixel checks. The verified candidate restores the original image with zero mean RGB error. Capture warm-up frames are required after material replacement; a single initial capture can otherwise falsely report an invisible avatar.
- All 16 predecessor native regression packages passed: windows, interface scale, hover, item handover, emblems, guild, display, controls, movement, jumping, tracking, water data, audio/UI, vitals, compass and clock.
- 335 predecessor receipt guards, 58 Stealth receipt guards and an in-memory simulation of the complete installed receipt chain. Installation replaces exactly 15 named files with backups and rollback. No played database or server rule changes.

Installation verification uses verify_stealth_render_native.py --installed. Owner visual acceptance remains separate from automated acceptance. All diagnostic-only material libraries are excluded from installation.
