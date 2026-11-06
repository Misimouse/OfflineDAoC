# Local target tracking delivery

Original Godot `player.gd`, `chat_window.gd`, `zone_viewer.gd` and default key bindings are the reference. `/face`, `/follow`, `/stick` remain client-local commands. They never invoke server companion/bot controls or teleport the player.

- F or `/face`: turn toward the selected living target without moving.
- Shift+F or `/follow`: start within 25 m and stop at the original 3 m horizontal gap.
- Shift+V or `/stick`: start within 25 m, stop at 1.4 m and break beyond 37.5 m.
- Manual W/A/S/D, both mouse buttons or run lock cancel tracking. Death, sitting, input focus loss, chat/options, logout, corrections and target disappearance also clear it. A stale acknowledgement cannot restart a previous request.
- Existing server run speed, collision sweeps and water movement remain authoritative for local movement. This is direct tracking, without pathfinding around obstacles.

The marked disposable server route exercises original target selection, no-target/self rejection, stationary facing, a real closed door, switching to an outdoor target, both stopping gaps and actual target removal. Gap tests use open ground: opening a swinging leaf while pushing against it can move the capsule against the jamb; this delivery does not claim automatic obstacle avoidance. The fixture database is restored afterwards. No owner save, world population or WORK map is edited.

Separate gates cover 37 Godot state checks, 35 native tracking rule checks, 265 prior audio/UI/selection checks, and 58 synthetic installation-chain checks. Installation requires matching current source/build/evidence hashes, closed normal ports and a rollback backup. Native regressions are repeated against the installed output. Automated checks do not replace the owner's visual/gameplay acceptance.

Owner checks: select a nearby creature, use each command/key, change selected creature then start again, walk manually to cancel, try self/no target/far target, stand against a closed door, sit/open chat and return to character selection. Tracking should remain stopped until explicitly requested again.
