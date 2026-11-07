# Prompt completion of original equipment refusals

An original other-realm equipment refusal was reproduced against the installed backend: the item stayed safely in the backpack, but the bridge kept the request pending until its twelve-second timeout. The inventory state now recognizes the exact original realm and class refusal messages, alongside the existing armor/weapon skill refusals. It finishes only an outstanding equipment request and displays the original English response.

Quoted NPC speech, unrelated messages, late duplicates, purchases, backpack-only moves, poison applications and NPC handovers cannot be acknowledged by these equip-only responses. The change never alters inventory revision, item identity, coins, server permissions, class skills or realm rules.

Evidence: 130 compatibility checks (inventory 35, refusals 23, NPC handover 36, gateway nine and poison 27), six real DOL checks for each of the original class and realm refusals, and 150 synthetic receipt-chain checks. The real checks also unequip and re-equip an allowed original Hibernian cloth vest immediately after rejection and inspect saved slots after normal shutdown. All marked disposable database fixtures and copied private server libraries are restored.

The installer changes only inventory_state.gd, with the verified poison-delivery predecessor and an exact backup. No native binary, server library, map or played database changes.

Owner review: try equipping a piece your character cannot use because of realm or its explicit class restriction. The original refusal should appear immediately, with the item still in the backpack. Then equip a valid piece without waiting for a timeout. No test equipment is added to the played account; this can remain pending if no unsuitable piece is available.
