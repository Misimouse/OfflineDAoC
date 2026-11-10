# Original player-trade contract

The reproducible audit resolves client 1.127 inheritance to `PacketLib1109.SendTradeWindow` and `PacketLib1124.WriteItemData`. Incoming TradeWindow is0xEA; ModifyTrade is0xEB. The existing Send method writes0xEB directly into the low-byte header, as GSPacketIn reads it; no additional xor is applied. The enum's historical0x43 comment must not be used as another encoding step. The legacy 1.68 hand-written partner item layout is not suitable for this client.

Godot has no0xEA decoder or player-trade window dispatch in this snapshot. Its Realm Exchange window is a different marketplace service. The original `trade.png` resources exist at original and x4plus resolutions and should supply the eventual UI, together with the existing English text and item icons.

Opening uses original MoveItem to target OID+1000. DOL owns realm/ordinary permissions, range, backpack item ownership, tradability and partner busy checks. ModifyTrade cancels, updates ten item slots/five money denominations or accepts; offer updates reset both acceptances. A forty-zero-byte window packet closes the trade. It cannot alone prove successful item/money exchange. This window payload has no acceptance bits, so the client must not fabricate server acceptance from its own button click.

The next bounded transport candidate retains modern item records for the existing decoder and rejects truncated payloads. It remains inactive until the complete ordinary two-player update/accept/cancel, stale identity, refusal and persistence checks plus original UI integration pass. No server rules, played data or native UI are changed by this audit.

Inactive codec candidate now passes146 compiled checks. `DaocTradeCodec.cs` validates modern incoming records, optional embedded spell descriptions, denomination order, exact close packets, lengths, counts and duplicate slots. It builds exact original update/accept/cancel payloads and refuses non-backpack outgoing slots or invalid money. It does not dispatch incoming0xEA in the normal client, change inventory, grant money or provide a temporary window. The candidate provides the original request sender and maps validated records through the existing ReadItem decoder. The existing `ReadItem` remains the eventual item-field decoder; raw validated records are retained for it. Ordinary protocol outcomes and the complete UI are the next acceptance gates.


## Ordinary two-player transport acceptance

The private wire candidate passes all15 real-protocol checks, in addition to146 compiled codec checks. Two ordinary accounts exchange one item each and100/50 copper, change an offer after acceptance, cancel, repeat a stale acceptance, attempt an unaffordable offer, and attempt an untradable bound item. Original DOL rejects the bound item before displaying a window; this is preserved. Logout and database queries confirm ownership and realm-account balances9950/10050. No optimistic inventory or money update is used.

The private harness inserts0xEA dispatch only into a staged backend and routes test requests directly to the original MoveItem/ModifyTrade methods. Production gateway identity guards and native UI are explicitly outside this proof. Normal client/backend/source, played data and WORK remain unchanged. Both clients and the isolated server exit normally; the marked database, libraries and navigation are restored. Private evidence: PlayerTradeLab/RealProtocol/20261110-190417/verified.json. No private evidence, account or database is published.

Next package: an inactive trade state adapter with session/offer identity and stale-action guards, followed by the original trade window and complete gateway acceptance. Do not advertise this transport candidate as an installed player-trade feature.
