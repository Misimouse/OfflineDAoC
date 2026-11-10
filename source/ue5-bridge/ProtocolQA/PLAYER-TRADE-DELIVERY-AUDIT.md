# Original player trade delivery

The original trade window is now connected to the normal client. Dropping a
backpack item on an actual nearby player opens the original server trade.
Offer changes, money, acceptance and cancellation use the original protocol;
the client never predicts ownership or invents partner acceptance. Partner
records retain their original backpack slots and render in offer sequence.

The connected UE test uses real viewport picking and real native buttons,
forwarding commands unchanged to two ordinary disposable accounts. Its14 checks
verify cancellation, partner item presentation, acceptance, authoritative item
and money transfer, normal shutdown and persisted ownership/balances. The
separate17-check production-gateway test also covers changed offers resetting
acceptance, stale requests, insufficient funds and untradable-item refusal.
Private data, navigation and server libraries are restored after each run.

The guarded delivery replaces exactly22 client/source files, including the
single incoming0xEA dispatch and the previously tested codec. It copies the
existing original trade atlas without editing it. The17 manifest checks reject
altered sources, targets, fingerprints and evidence. Every replaced file has a
recoverable backup; a historical network-reference failure exercised automatic
rollback before the corrected delivery passed the complete predecessor chain.
No played database, server rules, map or WORK asset is changed.

The installed UI is checked separately from candidate evidence. Native controls,
partner sparse-slot layout, existing marketplace and original NPC/player
handover retain their own proof reports. Owner two-player gameplay review is
pending; automated evidence is not a claim that every trade situation, server
service or multiplayer feature is complete.

Next bounded package: personal/account vault persistence and transaction
lifecycle compatibility. Reuse original UI and DOL permissions; record unrelated
findings without diverting this package.
