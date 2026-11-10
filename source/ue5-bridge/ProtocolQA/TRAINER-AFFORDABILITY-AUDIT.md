# Trainer specialization point budgets

After spending the two earned points, Nurture1 was still marked `can_train=true`
because it was below character level2, despite its next rank costing2 points
and the remaining balance being0. The native original trainer panel already uses
`can_train` for row colour and TRAIN-button availability; its input was incomplete.

`trainer_state.gd` now requires both the original character/rank limit and a
positive next cost no greater than current server specialization points. A fresh
unaffordable row cannot send a training packet. Subsequent server point updates
recompute eligibility and the existing row token. No points or skills are awarded
or subtracted locally; DOL retains final authority. Existing realm-ability checks
and UI layouts are unchanged. Original Godot's specialization list did not itself
grey unaffordable rows; this correction uses the bridge's existing native disabled
state rather than claiming an original Godot colour rule that was not present.

The new regression reproduces the missing checks against the pre-fix source.
After correction,18 budget checks,28 existing trainer checks and43 existing
classic-UI checks pass (89 total). A separate19-check ordinary-server scenario
earns points through melee, trains Regrowth2, and verifies that Nurture remains
unavailable at0 points and that a current unaffordable request is refused without
changing rank/points. Its private DB and libraries are restored on normal exit.

Delivery replaces only `Godot/trainer_state.gd` in the normal bridge workspace.
The known pre-fix bytes match the failed regression's private copy; exact hashes,
proofs and18 altered-plan simulations protect the one-file install. The installer
requires closed normal server/client ports, retains a verified backup and provides
a guarded rollback. `central_activation_receipts.py` verifies the independent
trainer receipt while retaining the native predecessor chain. No native binary,
server rule, played database, map or WORK asset is replaced.

Private proof: `TrainerAffordabilityLab`. Rendered row colour/button acceptance
remains on the cumulative owner checklist. Source/protocol tests do not replace
that review. Selected-row highlighting retains the existing native gold colour.

The installed copy separately passes the same19 ordinary-server checks. The
rollback preview and central receipt verification pass; the normal native binary
and played database remain unchanged. These19 checks overlap the candidate
scenario and are not19 additional gameplay features.
