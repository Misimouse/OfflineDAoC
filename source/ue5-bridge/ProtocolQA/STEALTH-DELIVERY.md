# Original Stealth integration — candidate checkpoint

Status: mechanical integration verified in isolation, not installed in the normal game.
The owner's review remains deferred. This is not a claim that Stealth or the whole migration is finished.

The existing Abilities window and quickbars expose Stealth only when the original server supplies a trained Stealth specialization. Activation sends the original type-zero UseSkill packet with validated current identity, position and heading. Server cooldowns, rejection rules and speed remain authoritative. No skill or hidden state is granted locally.

Generic ObjectDelete also removes living players hidden by the original server. Their target, native actor, mount relation and cached combat pose are cleared; original PlayerCreate restores visibility. An unrelated ground-object removal preserves other living entities.

Validation of the candidate:
- 14 checks with two ordinary players on an isolated original server: UI/quickbar activation, stale identity, two-second toggle limit, hide/reveal, original speed, observer disappearance/reappearance, hidden target cleanup, and Sprint rejection while hidden.
- 703 state checks across 27 compatibility packages, including 27 focused Stealth checks.
- 177 checks through the installed Unreal entity consumer, replaying candidate entity snapshots with a verified living/standing player status. This is an offline native actor test, not a rendered Stealth acceptance test.
- Private database, layout, configuration and server binaries restored; normal runtime unchanged.

Still pending before full acceptance:
- The local hidden avatar's translucent rendering, including hair, armour, weapons and return to its exact original materials. Opaque/masked materials cannot be made transparent simply by setting an unsupported scalar. Preserve the separate character work and shared original assets.
- Stealth-specific hover information beyond existing server effect details.
- Guarded installation and owner visual review when available.

A previous native replay failed its local heading checks because the old entity-only fixture omitted player_status. The runner now supplies the verified original living/standing status; production dead/seated rotation protections and all heading assertions remain intact.
