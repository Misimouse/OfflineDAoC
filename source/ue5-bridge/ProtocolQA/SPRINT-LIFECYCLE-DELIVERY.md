# Original Sprint lifecycle verification

The existing Sprint ability was exercised from the original server skill catalogue using
ordinary disposable players and the installed bridge. No new runtime code or gameplay
rule was required. Eleven real-protocol checks cover the stale skill guard, low-endurance
rejection, server effect and speed acknowledgement, moving endurance consumption,
automatic exhaustion, restored normal speed, reactivation, manual toggle and idle timeout.

The measured server speed limit changed from 5.96875 to 7.7355 metres/second in this
private configuration. This is an observed result, not a hard-coded new movement setting.
Endurance fell during movement; exhaustion removed Sprint and restored the original speed.
Remaining stationary also lets the original Sprint effect end on its idle timer.

The private database, server libraries and bridge configurations were restored after normal
logout and shutdown. The player's progression, money, inventory and WORK map are untouched.
Measurements and private protocol snapshots remain outside Git. This does not verify all
speed buffs, mounts, relic modifiers, exhaustion perks or the physical traversal of every
map. Native movement and existing interface acceptance remain separate evidence.

Owner review is deferred. When convenient, use Sprint from Abilities or a quickbar, move
while watching endurance, let it run out, recover and activate again, then toggle it off.
Keep the normal movement keys and camera behaviour established by earlier packages.
