# Original run/walk locks and modern backpedal

NumLock toggles forward run lock. ScrollLock toggles walking; Shift remains available. W/S presses or both mouse buttons cancel run lock; manual input continues normally. Losing world input focus, opening text/options input, sitting, death and logout cancel automatic movement. Closing the window does not resume it. Walking follows the original 35% multiplier; backwards follows the existing modern movement mode's 65% multiplier, including diagonals. Existing WASD direction and accepted right-mouse camera behaviour are retained.

The backward pose uses each playable model's original `walk_back` clip. Playback follows Godot's original `strides_units.back` and `clip_seconds.walk_back` formula with its 0.3..3 clamp. Shar and Minotaur have different stride data; a single shared human stride is not used. Existing foot-contact audio follows that actual animation time. Unknown transformed models retain their default cadence.

This delivers the default RPG preset's two movement-lock keys. It does not introduce a replacement keyboard-settings interface, switch to classic keyboard turning, add follow/stick/climbing, or change existing mouse bindings.

## Evidence and installation

- `audit_movement_keys.py` pins original keyboard presets, player behaviour, all 13 race sidecars, accepted foot-contact profiles and the previous jump receipt.
- 53 native checks cover locks, blocked input, cancellation, walking/backward ordering, all 13 loaded original backward clips/durations and model-specific playback rates.
- A disposable real server session measures actual automatic run, walk and backward velocity, backward pose and final stop. Expected speeds for the fixture are 4.775, 1.67125 and 3.10375 m/s.
- 265 existing audio/options/selection regressions run against the candidate. River/buoyancy/bridge and acknowledged door-crossing routes also gate installation.
- `install_movement_keys.py` replaces eight explicit files, including its original-stride catalog, with predecessor/hash checks, backup and rollback. It modifies no owner database or map asset. Historical delivery proofs are preserved.

## Owner checks

Press NumLock to run without holding W; press it again to stop. Confirm W/S and both mouse buttons cancel that automatic mode. Press ScrollLock to walk and again to run; also test Shift. Use S and diagonal backwards movement: the character should backpedal with the correct original pose. Repeat with a Shar or Minotaur when available. Open chat/options, sit or lose focus during automatic movement: it must stop and stay stopped. Repeat jump, door crossing, river entry/exit and the bridge. Listen to the steps while moving backwards.
