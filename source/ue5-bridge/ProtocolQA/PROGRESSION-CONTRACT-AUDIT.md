# Experience, level and skill refresh

This package verifies the existing progression connection. It does not award
experience locally or implement new class rules, expansion data or a replacement UI.

## Contract traced in source

- The original `DaocClient.cs` decodes CharacterPointsUpdate (`0x91`) with
  `level_permill`, specialization points, exact experience and next-level XP.
- Original `server.gd` stores the points and character packets separately. It
  publishes completed skill batches through `skills_changed`; spell lines are
  replaced when the final `done` packet arrives.
- `Godot/live_gateway.gd` connects this signal to `capture_lists`. Separate skill
  and spell loading flags prevent execution while either batch is incomplete.
- `Godot/classic_ui_state.gd` copies current server `info` and `points` into its
  snapshot. A level update alone does not manufacture spells. Current same-name
  abilities refresh their saved identity; changed/removed entries cannot execute
  through an old quickbar binding.
- Native `DAoCBridgeClassicUI.cpp` reads level, XP and training points from that
  snapshot. `DAoCBridgePlayerStatus.cpp` reads `level_permill` for the original XP
  jewels and partial jewel bar.
- Current server `GamePlayer.GainExperience`, `Level` and `OnLevelUp` retain
  authority over thresholds, level changes, points and dependent skill refresh.
  This is the current OfflineDAoC server path; it is not a claim that its content
  database contains every Catacombs class, quest or NPC from the pinned DOL data.

## Verification boundaries

`verify_progression_ui.py` runs 24 checks against the real bridge UI state in a
fresh headless project. The input is a controlled server snapshot fixture. It
covers authoritative values, independently incomplete lists, rank additions and
removals, refreshed ability icons/tokens, stale drag denial, and saved shortcuts.
The fixture's experience numbers are examples, not a new XP table.

`verify_progression_real.py` separately uses two ordinary disposable accounts,
a marked private database and the existing isolated server candidate. One player
starts at level 1 with 49 XP; the other remains idle. A disposable level-1
`GameNPC` uses DOL's existing `BlankBrain`, allowing normal melee damage, death
and server XP processing without retaliatory combat obscuring this measurement.
The scenario checks level/points/catalogue refresh and logout persistence. It is
not a test of encounter balance, world spawning, rendered XP animation or every
class's spell progression. No GM level/XP command is used.

Early retaliatory NPC fixture attempts killed the disposable character before
level-up; their failed reports remain private. The first also required stopping
its private headless client after logout timed out. Cleanup now releases a dead
test character before logout. These attempts are not successful progression
evidence and do not justify changing live combat rules.

Private proof and owner review live under `ProgressionLab` and
`CAMBIOS-PARA-PROBAR-PROGRESION.txt`. Runtime files, played databases and WORK's
map/art are not part of this package. Passing automated checks remains separate
from the owner's rendered gameplay acceptance.

## Completed bounded result

The UI suite passes 24 checks. The separate ordinary-server scenario passes 10
checks, with normal client/server shutdown and restoration of the marked private
database and server libraries. Level changes from 1 to 2, XP from 49 to 64,
`xp_next` from 50 to 250, `level_permill` from 980 to 70 and specialization points
from 0 to 2. The captured catalogue adds level-2 Nurture `Minor Bark Skin` without
reconnecting; the idle peer remains level 1 with 49 XP. Logout saves level 2 and
64 XP before restoration. No runtime change or deployment was needed.

This closes this bounded contract/roundtrip audit, not all class progression.
The earned-point training follow-up now passes 17 extended ordinary-server
checks; see PROGRESSION-TRAINING-AUDIT.md. Simulated shortcut refresh is covered
here; actual spell result/resources/reuse after training remain separate.
