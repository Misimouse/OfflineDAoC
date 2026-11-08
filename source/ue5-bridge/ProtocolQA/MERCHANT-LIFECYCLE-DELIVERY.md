# Original ordinary-player merchant transactions

This package verifies existing runtime behavior without replacing normal client or server files.

The marked private database has no normal merchants. A private reference contains Evan's original NPC, three original catalogue rows and their original item templates, copied read-only from the installed world. The disposable Druid receives one gold in the existing account/realm wallet solely for the test. A second ordinary account retains zero money. All marked database contents are restored afterwards, including these original world-row additions and test money.

Thirteen real checks cover original names/prices/icons, insufficient funds, rejecting unsupported multi-pack quantities, stale catalogues, a server-confirmed purchase of one nadurtha vest, an exact deduction of 262 copper, refusal of stale item identities, actual sale/removal and the original configured 50% resale payment of 131 copper, refusal to sell the removed item again, refusal to buy through a closed catalogue, and the balance saved by normal logout. The test also respects the server's original merchant range. The normal wallet and played database are never modified.

Fifty-eight existing state checks cover inventory operations and authoritative refusals. Twenty-seven installed native transaction checks cover exact original buy/sell/move/equipment command identities, pending-operation guards, stale selection and session cleanup. This last native suite exercises the existing inventory transaction surface; it is not a claim that every merchant presentation variant was tested. Original classic merchant pointer/scroll behavior also remains covered by the compass delivery's regression evidence.

Owner review: buy one inexpensive item from a nearby ordinary merchant, compare money and inventory, then sell that disposable item. A stale selection or closed shop should not buy/sell anything. Owner gameplay acceptance remains pending. Special currencies, crafting supply variations and the Realm Exchange are separate systems.
