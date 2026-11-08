# Original resting regeneration verification

Two ordinary disposable players were measured through the installed bridge, without
editing client or server regeneration rules. Both started with low positive health,
power and endurance in the marked private database. One stood still; the other sat
through the original server-confirmed posture request.

Observed median health and power intervals were approximately 6.01 seconds standing
and 2.98 seconds seated. Endurance recovered one point per tick standing and four
seated. Measurements exclude the capped final endurance gain. Standing again preserves
recovered resources. Positive health remains alive even when its percentage rounds to zero.

Verification: 14 real-protocol checks, two endurance measurement checks, and 58 client
state checks. The focused state checks confirm that neither elapsed time nor a local
posture request grants resources: only original server status packets update the UI.
Existing player combat/posture checks remain green. The private database, configurations
and libraries are restored after normal logout and server shutdown; played progress,
equipment and the WORK map are unchanged. No new runtime installation was needed.

Scope: these are out-of-combat resting measurements. They do not verify every regeneration
buff, disease/bleed effect, class modifier, moving endurance rule or in-combat interval.
Original source references are pinned in the private proof, and measurements are retained
outside Git. Owner review is deferred: when convenient, compare standing still with
sitting after ordinary health/power/endurance expenditure using a test character.
