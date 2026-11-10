# Earned points and trainer roundtrip

Run `verify_progression_real.py` with `DAOC_PROGRESSION_TRAINING=on` in the existing
private QA workspace. `off` retains the preceding bounded progression scenario.
Both modes reject unexpected mode names and restore the marked disposable DB,
private libraries and temporary configuration after normal logout/shutdown.

The extended scenario passes 17 checks, including the preceding melee XP/level
checks. A level-1 Naturalist starts with49 XP and no specialization points, kills
the passive disposable NPC through ordinary melee, and reaches level2 /64 XP
with2 points. The original `NaturalistTrainer` window then lists Regrowth1 at
cost2. The original training request produces Regrowth2 and0 remaining points;
both the trainer and character sheet receive the confirmed values. An obsolete
training token cannot spend the points again. The heal assigned before level-up
still resolves to the current same-name spell and accepts its original use
request. Normal logout saves `Nurture|1;Regrowth|2`, level2 and64 XP.

An initial training attempt exposed an unrelated fixture condition: the reused
disposable character had old free-level dates. Original `GameTrainer.Interact`
legitimately awarded the available free level, producing level3 and5 points.
That failed expectation remains in private evidence. The test now initializes
the disposable character's free-level timestamps as newly started; the original
server free-level rules are unchanged. No played character or DB is modified.

This is protocol/state verification, not rendered trainer/quickbar acceptance.
The retained heal check proves bridge request acceptance, not healing magnitude,
spell animation, audio or the complete resource/reuse lifecycle after training.
These remain a distinct casting roundtrip. All class/rank and expansion-content
coverage is still bounded by the earlier audits; this Naturalist case does not
claim that every class is complete. No runtime deployment was required.

Private proof: `ProgressionTrainingLab/verified.json`. Owner review is appended
to the existing `CAMBIOS-PARA-PROBAR-PROGRESION.txt` and cumulative review index.
