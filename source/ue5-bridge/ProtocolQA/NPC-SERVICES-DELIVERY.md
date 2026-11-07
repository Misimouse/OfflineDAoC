# Original blacksmith repair checks

The installed item-handover path also works with the original DOL Blacksmith. No additional runtime or server change was necessary. The original server permits a worn weapon to be handed to this service; the same request to the emblemeer remains rejected until the item is in the backpack.

A marked disposable server/database passed eleven checks for original confirmation, cancellation, worn and backpack repair, exact payment, condition/durability changes, stale-repeat protection, rejection of perfect/unsupported/stacked items, unchanged previous target and persistence after normal shutdown. A separate zero-wallet run passed five checks, including the original refusal and unchanged saved condition/durability. Test clubs with half condition cost 75 copper according to the existing template formula; this is a fixture result, not a universal repair price. Original durability loss is retained.

These checks use ordinary account privileges. Fixtures, wallets and copied private server libraries are restored afterwards, and the normal installed files are hash-checked unchanged. No test money, worn objects, smiths or guilds are inserted into the played database. The test reuses the guild-capable isolated account scaffold; guild membership is not a blacksmith requirement.

Owner review: use the normal launchers and a real damaged repairable item. Drag it from its equipped slot or backpack onto a nearby smith, cancel once, and check that nothing changes. Accept only if you intend to pay the original quoted price. Confirm that condition improves and durability changes according to the original game rules. An undamaged or unsupported item must not be charged. If no suitable damaged item is available, this owner check can remain pending.

This closes the bounded blacksmith transaction check, not all NPC services, quest deliveries, dyes, poison application or player trading.
