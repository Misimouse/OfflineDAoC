# Empty inventory initialization and character equipment isolation

The original DOL WorldInit sends equipped/backpack items before sending its money update.
PacketLib168.SendInventoryItemsUpdate skips empty collections, so a character
with no items receives no inventory event. The bridge previously used that event
alone for readiness, leaving an otherwise fully entered empty character blocked.

The bridge now accepts the original, valid money message as initial
inventory readiness. Item-event counters remain separate: a money update cannot
acknowledge a purchase, move, sale or coating. Actual server item updates still
confirm transactions; reset requires the next character's own initialization.
The first money event invalidates the cached fingerprint until a consistent
rows/coins sync finishes, keeping readiness consistent with the current server balance. No inventory
contents, coins or equipment eligibility are granted locally.

References: source/server/GameServer/packets/Client/168/WorldInitRequestHandler.cs,
source/server/GameServer/packets/Server/PacketLib168.cs and the original
DaocClient.cs MoneyUpdate decode. No server change is required.

The isolated verifier covers123 checks: the original35 inventory checks,14
empty-state checks,24 quantity,23 equipment-denial and27 poison checks, including pre-init refusal, empty purchase dispatch, absence of optimistic
items, transaction acknowledgement and reset. A separate ordinary-server mode
extends cross-class switching with empty-character readiness, cleared dialogs and
trainer state, refused previous-character equipment handles, restored original
items and server-authoritative account/realm money, plus server-confirmed unequip/reequip after returning.

Private evidence: CharacterInventorySwitchLab. Failed pre-change evidence is
retained separately. Candidate and installed reports are distinct. Owner gameplay
review, rendered armor appearance and all class/armor combinations remain separate.

Money is shared per account/realm by this server (GamePlayer.HandleMoney and
AccountXMoney). The real test compares that authoritative balance; it does not
assume a newly created character must start with zero coins.
