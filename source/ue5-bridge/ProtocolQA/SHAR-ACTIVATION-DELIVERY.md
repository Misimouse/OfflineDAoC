# Shar activation in the normal client

Shar (race 18) is now enabled for male and female Mentalist, Blademaster,
Hero/Heroine, Champion, Ranger and Vampiir. Other existing race/class choices
are preserved. Bainshee restrictions and male-only Hibernian Minotaur remain
unchanged; Mauler/custom classes are not enabled by this delivery.

The original Shar figures 1075/1087, customization, equipment and three DOL
startup records had already been delivered centrally. This activation changes
one `disabled_races` server property and its generated rules catalog only.
It does not replace spells, world population, missions, starts or saved binds.
Original base-class/level-five progression is retained.

## Completed verification

- Exact proposed normal policy: ten ordinary Shar creation/reentry cases,
  six Vampiir cases (including the established Celt/Lurikeen paths) and ten
  Shar GM recovery cases. Complete original starting spell lists, appearance
  and normal saved reentry pass; each disposable DB/server is restored.
- GM recovery preserves the original spawn/bind before entry and asks the
  server for transfer to the Connacht test map. It does not fabricate world
  entry or rewrite a production start location.
- Installed native models and UI: male/female creation and customization,
  four screenshots and 300 checks. Captures inspected by Codex; owner visual
  acceptance remains pending.
- Normal menu after activation: six existing characters, 95 choices, no owner
  world entry and normal server shutdown.
- Three synthetic SQLite transaction checks cover preservation of existing
  saves/world rows, rollback after a rules-copy failure and rejection of stale
  eligibility. Seventeen receipt checks include the explicit Shar successor.
- The guarded installer backs up the database/catalog, verifies all existing
  rows in 125 tables around its transaction, and is idempotent afterward.

The normal playable UE map is still Connacht. Original starts in other zones
do not establish rendering or ordinary-player travel coverage there. Recovery
was accepted using GM permission; full other-region gameplay remains deferred.

Private proof lives under `Reports/central_shar_activation`, with the plan and
receipt in `ExpansionRaceLab/CentralDelivery/SharActivation`. No played data,
credentials, original game assets or test logs are committed.

Owner checks: create a male and female Shar, inspect available/disabled classes,
customize and save appearance, enter Ardee with the GM account, inspect starter
equipment and the base class's spell list, then `/quit` and reenter. Check that
existing characters remain present. A level-one base class is not expected to
receive its advanced level-five profession's entire spell list.
