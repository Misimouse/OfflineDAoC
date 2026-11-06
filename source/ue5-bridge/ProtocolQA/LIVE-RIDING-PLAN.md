# Live mounted transport package

Reference: current original DaocClient Riding 0xC8 decode / Dismount request, live ServerWorld saddle logic, zone_viewer mounted position/state 0x18, and DOL GameStableMaster/GameTaxi. The separate offline HorseRoutes controller is not the authority for a connected game.

Read-only `audit_live_riding.py` inspected public merchant/path rows using SQLite mode=ro plus query_only. Six paths are offered by three stablemasters inside Connacht. Only `HR_TirNaNog_DruimLigen` stays fully within zone 207 (21/21 points). Freagus in Ardee offers two paths that leave it. Offline routes.json has region=0 for every row; those values cannot be treated as the live region ID. Segment/terrain/visual acceptance is still required even for an in-bounds point list.

Close this package in order:

1. Isolated Godot mount-state contract: strict Riding packet, local/remote ownership, out-of-order steed spawn, removal, death/logout/region reset, dismount request awaiting real acknowledgement, stale/duplicate handling. No synthetic route movement or ticket consumption.
2. Native saddle attachment and original ride_horse animation. Use the actual posed/instance-scaled saddle and keep camera orbit; mounted player cannot walk independently. Preserve authoritative mounted speed/heading/state in original position packets. Jump and /dismount send original request, do not fake successful unmount.
3. Private real server itinerary: original stable ticket buy, consume once, real mount ACK, original horse route movement, jump/request/ACK, return to grounded collision and no orphaned camera. Verify ground height, animations and mount sound. Keep owner DB and WORK untouched.
4. Boundaries are a delivery gate: the server must never continue charging/moving the player into unloaded zones. Resolve explicit supported travel handling before enabling unrestricted Ardee route purchase; do not silently alter original tickets/path rows or claim complete cross-zone travel.
5. Current prior installed blocks must pass unchanged after candidate installation, with exact-file backup/rollback and cumulative owner checklist. No full stable travel claim until all phases are proven.

Current normal runtime remains the tested target-tracking delivery. Riding work is private until these gates are met.

Preparation evidence now covers 60 isolated packet/state checks and 44 native asset/saddle checks. All 13 original ride_horse animations load. The saddle reference point is recovered from the exact GLB imported into Unreal; 117 bone positions agree after axis conversion within 0.000052 cm. The native seat resolver follows the posed spine and the actual component transform, tested with scale/rotation/translation, galloping motion and a second independent mount. These are private prerequisites, not a delivered ride controller.

Reproduction order: `prepare_live_riding_data.py --source-only` extracts the deterministic catalog from the original GLB; build with `build_spell_audio_native.py --live-riding-candidate`; run `verify_live_riding_assets.py`; then run `prepare_live_riding_data.py` without source-only to verify native bones/current build and seal private resource evidence. No normal runtime installation is performed by these steps.
