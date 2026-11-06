# Local surface swimming and wading

The native player uses the original zone207 water mask and heights to enter surface swimming, float, play the original swim animation and return to grounded movement. The Godot bridge sends the original swimming and ground flags through Position/Heading. Wet steps and swim strokes use the already exported original contact timings and sounds, with the existing Master/Effects controls.

Scope: local surface swimming/wading only. Diving, currents, NPC water steering and landing fall damage are separate blocks. UE swept movement supplies collision; its internal flying mode is never advertised as flight to the server. Horizontal input release stops swimming motion. Deep-water classification checks the player's feet, so the actual Elf Bridge deck remains grounded.

## Evidence

- Original Godot image decoder compared all 65,536 water-mask cells with the exported field.
- 65,559 native data and boundary checks; 21 movement-flag cases.
- 265 native regression checks: spell/combat/server/door/footstep audio, volume options and body selection.
- Disposable real protocol session: wade, swim, stop while floating, return to land, then land on the actual bridge deck. Original wet/stroke PCM is consumed by UE.
- Separate disposable door session: closed door blocks, acknowledged open allows crossing, then return. Both sessions shut down normally and restore their marked test database.
- The approved river layer is loaded once: 483 visible components, including 14 log components, 4 algae films and 221 aquatic components. The newer shared Ground_Cover_v02 terrain material is preserved. Its difference from the older river-bed binding remains a visual integration item; this block does not overwrite WORK's terrain.

Historical failed runs are retained: stationary swim drift fixed before delivery; bridge witness originally spawned at mesh pivot rather than above its deck; the additional environment check identified the newer shared terrain material.

## Delivery and rollback

`install_water_movement.py` gates the source/build/resource hashes and all acceptance evidence. It replaces 14 explicit files, backs up each existing target and records a predecessor receipt chained to server-sound delivery. It changes no owner database or map asset. Normal server/game ports must be closed before applying. Use its `--rollback --apply` mode to restore those exact predecessor files.

## Owner checks

Enter the river from a bank: shallow water should wade, deeper water should swim. Stop, turn, swim back out, then cross the bridge. Check wet steps and strokes, including Master/Effects and mute. Repeat a door crossing and ordinary ground movement. Confirm death/release and leaving/re-entering a character still behave normally. Automated checks do not replace this listening and gameplay review.
