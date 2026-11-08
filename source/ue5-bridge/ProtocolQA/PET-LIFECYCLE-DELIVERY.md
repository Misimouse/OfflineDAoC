# Existing owned-pet lifecycle

This verification package tests the already integrated original pet window, DOL summon and PetCommand protocol. No runtime code, maps, models or played data are replaced.

Seventeen real checks use ordinary disposable accounts. The original Call Greater Nature Spirit spell creates its actual server-owned creature; its name, model and object identity come from world packets. The original seven orders are present. Passive, aggressive, defensive, stay and follow receive original server acknowledgements. Another account cannot command the pet. An existing quickbar sends a pet order. Release clears ownership only after the server closes the window. An absent-pet shortcut and an old pet identity after resummoning are rejected. A generic saved pet shortcut refreshes to the newly confirmed owned pet and works again. The second pet is also released normally.

28 original state checks additionally cover invalid targets, dead owners, rate limiting, unconfirmed mode changes, unknown geometry/health and region reset. 80 installed native checks include original pet buttons, release confirmation, original command identity, quickbar dragging and effect icons. The real test respects the original 150 ms duplicate-order protection; it does not weaken the debounce to make automated clicks pass.

The private database, configuration and server libraries are restored after normal shutdown. The played database is untouched. This bounded package does not certify pet combat against actual obstacles, follow pathfinding, cross-zone behavior or every summon in every class. Those require their own geometry and content witnesses.

Owner review: summon a pet, use passive/stay/follow, place an order on the quickbar, release it, then summon another and retry the generic shortcut. Existing pet artwork and server-owned identity remain in use. Automated acceptance is separate from owner approval.

Next package: original compass UI and its relationship to character heading, using existing game artwork and layout behavior.
