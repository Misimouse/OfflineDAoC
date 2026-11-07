# Original inventory-to-NPC handover

Dragging a carried inventory item onto a visible nearby NPC now uses the original MoveItem packet, with destination 1000 + that NPC's server object ID and the actual stack count. It does not depend on the previous selected target. The bridge checks the current item token, inventory revision, NPC identity/model, life state, visibility and original 3.2-metre give range. The server remains authoritative for acceptance, equipment eligibility, confirmation, payment and inventory updates.

Handled UI drops, cancelled drags, right-button drops, stale items, blocked inventory transactions, empty ground and intervening world collision do not send a handover. There is no ground-drop fallback or player-to-player trading in this package. Equipped-item delivery is passed to the original server, preserving its Blacksmith exception and rejection for other services. An unchanged server inventory refresh releases the pending request without claiming that the NPC accepted it.

## Evidence

ItemHandoverLab contains 36 state checks, nine gateway checks, the existing 35 inventory and 11 denial regressions, and 19 native checks using actual Slate drag operations and viewport picking. A marked disposable DOL database verifies the original emblemeer transaction: equipped-cloak rejection, backpack delivery, the original five-gold confirmation, cancellation, cloak and shield application/payment, stale-repeat rejection and persistence after normal shutdown. Separate level, rank and insufficient-money cases each preserve the item and wallet. All private database fixtures and server libraries are restored afterwards.

The final native build also passed emblem 29, guild 33, display 47, controls 257, movement 53, jump nine, tracking 35, water-data 65,559 and audio/UI 265 checks. The receipt verifier passed 128 synthetic checks, including predecessor, binary, backend, inventory-source and unrelated-file tampering. The installer replaces exactly ten client files, with two new source files, exact backups and bounded rollback. It changes no server rule, played database, map or WORK artwork. Automated evidence is separate from owner gameplay approval.

## Owner review

Use the normal OfflineDAoC server launcher and INICIAR-ARDEE-GM.cmd. With a character eligible for guild emblems, drag a backpack cloak or shield onto an original emblemeer from close range. Check the original confirmation, cancel once, and accept only if you intend the original five-gold payment. Equip the result to inspect the applied emblem. Try dropping over empty ground and from outside the give range: no item should be removed or dropped. A character lacking level, rank or money must receive the original server refusal. Test accounts and money are never added to the played database.

Other NPC services reuse the original transaction, but service-specific owner checks remain separate; this package does not claim every quest hand-in, repair, dye or player trade has been validated.
