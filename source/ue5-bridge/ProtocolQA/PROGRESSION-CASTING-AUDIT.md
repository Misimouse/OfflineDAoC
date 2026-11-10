# Casting after earned-point training

`DAOC_PROGRESSION_TRAINING=cast` extends the disposable progression scenario.
It passes 25 checks, including the preceding XP and trainer checks. The second
ordinary account is an injured level-20 healing witness positioned next to the
Naturalist; its fixture XP is the existing server's level-20 threshold.

The heal placed on quickbar3 before level-up and training starts a server-confirmed
2100ms cast, releases, increases the recipient's health (169 to176 in the recorded
sample) and consumes power (20 to19). The original server message explicitly names
Codexfriend and the heal. A repeat through the same shortcut completes after the
ordinary recovery interval. This baseline spell has no remaining named reuse
timer; this is not a test of every spell-specific cooldown.

The newly received level-2 Nurture spell `Minor Bark Skin` can be assigned to a
different quickbar slot and cast. Its effect5011 is then present in the original
server's effect list. Level2 /64 XP and Regrowth2 remain saved at logout.

The first headless attempt correctly failed the original server's sight check.
The succeeding run routes correlated sight questions to a read-only offscreen
Unreal client using the project/map in `playable_project.json`; no all-true reply
is synthesized. `NativeSightRelay` accepts optional project, map and output
directory parameters while preserving its previous defaults. Both clients, the
server and native viewer exit normally; private data/libraries are restored and
the normal runtime hashes remain unchanged. No deployment was needed.

## Limits and follow-up

This positive close-target case proves native sight query transport, not complete
wall/terrain collision coverage. The read-only test captures show incomplete
ground presentation and the native pawn changes height during the scenario.
Those captures are not accepted as map-rendering or ground-collision evidence.
Record this as a harness-scene follow-up; it does not establish a regression in
the normal played client. Do not alter WORK's map to make a protocol test pass.

Likewise, captured cast/release frames and server effect IDs are not owner visual
or audio acceptance. Private evidence is under `ProgressionCastingLab`; the owner
checklist remains `CAMBIOS-PARA-PROBAR-PROGRESION.txt`.

The scenario also exposed that a specialization below the character's level is
still marked trainable when its next cost exceeds remaining points. Original
Godot/DOL and the bridge request/colour paths are being checked in the next
bounded trainer-affordability package, rather than changing spell rules here.

The grounded harness follow-up is now separately verified with real UE physics
and headless geometry,28 ordinary-server checks and18 startup-failure checks.
See NATIVE-SIGHT-HARNESS-AUDIT.md. The old rendered captures remain unaccepted.
