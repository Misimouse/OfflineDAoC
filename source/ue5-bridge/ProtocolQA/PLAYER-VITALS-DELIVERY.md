# Positive absolute player health

The original DOL server rounds `Health * 100 / MaxHealth` down when it sends a percentage. A living character with 1 / 336 HP therefore has `health_pct = 0`. The original Status packet also sends the actual HP and maximum HP. Original Godot uses those points; the bridge previously treated the rounded percentage as death.

This bounded delivery preserves original Status points, publishes an explicit authoritative living state and uses it for native movement, attack/sit/release controls, corpse animation, local audio and bridge action gates. An ambiguous combat percentage cannot announce a local death or revive a confirmed corpse. Actual Death and Status still control death; original Revive preserves positive Status received immediately before it. No local damage, healing, resurrection, items, skills or permissions are created.

The original integer percentage remains available to its wire Position packet and existing percentage bars. NPC percentages retain their existing protocol behavior; this does not claim that unknown remote absolute HP can be reconstructed.

## Evidence

A marked disposable DOL database reproduced the installed bug before modification: Health=1, MaxHealth=336, percentage=0, false dead actor and zero movement speed. With the candidate, ten real checks verify positive actual HP, living local state and speed, blocked living release, server-confirmed sit/stand and attack mode, original potion healing and original remaining charge plus saved charge count. Both database and private server libraries are restored. The played database is untouched.

State checks: 32. Compatibility: 18 original suites, 413 counted assertions plus the original spell-audio assertion suite (which has no numeric counter). A few legacy test fixtures now initialize the dependencies and region required by the current gateway; production behavior was not weakened to accommodate old fixtures.

Native acceptance: 23 checks using the captured real one-HP snapshot, original character mesh and actual idle/run/death clips. Checks include native request gates, false-release controls, non-restarting corpse animation, one-HP revival and legacy percent-only fixtures. The native package also passes thirteen regression packages including interface scale, window recovery, inventory handover, hover, guild, emblem, display, controls, movement, landing, tracking, original water data and seven audio/UI cases. Synthetic receipt guards: 255.

Installation backs up thirteen exact targets: seven native files and six Godot bridge files. Server libraries, game rules, maps, art and played saves are not replaced. Source, build, before/after protocol proof and predecessor receipts are hash guarded. Bounded rollback is supported.

Installed native acceptance passed the same 23 checks. Owner gameplay review is pending. Normal launcher remains `INICIAR-ARDEE-GM.cmd` after the normal OfflineDAoC server is ready. Suggested review: normal combat, death, /release and healing; the exact one-HP rounding edge is covered automatically and does not require changing a played character to reproduce.
