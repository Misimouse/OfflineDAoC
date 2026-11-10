# Original player-trade contract

The reproducible audit resolves client 1.127 inheritance to `PacketLib1109.SendTradeWindow` and `PacketLib1124.WriteItemData`. Incoming TradeWindow is0xEA; ModifyTrade is0xEB (wire code0x43 after the original xor). The legacy 1.68 hand-written partner item layout is not suitable for this client.

Godot has no0xEA decoder or player-trade window dispatch in this snapshot. Its Realm Exchange window is a different marketplace service. The original `trade.png` resources exist at original and x4plus resolutions and should supply the eventual UI, together with the existing English text and item icons.

Opening uses original MoveItem to target OID+1000. DOL owns realm/ordinary permissions, range, backpack item ownership, tradability and partner busy checks. ModifyTrade cancels, updates ten item slots/five money denominations or accepts; offer updates reset both acceptances. A forty-zero-byte window packet closes the trade. It cannot alone prove successful item/money exchange. This window payload has no acceptance bits, so the client must not fabricate server acceptance from its own button click.

The next bounded transport candidate retains modern item records for the existing decoder and rejects truncated payloads. It remains inactive until the complete ordinary two-player update/accept/cancel, stale identity, refusal and persistence checks plus original UI integration pass. No server rules, played data or native UI are changed by this audit.

Inactive codec candidate now passes146 compiled checks. `DaocTradeCodec.cs` validates modern incoming records, optional embedded spell descriptions, denomination order, exact close packets, lengths, counts and duplicate slots. It builds exact original update/accept/cancel payloads and refuses non-backpack outgoing slots or invalid money. It does not dispatch incoming0xEA, send requests, change inventory, grant money or provide a temporary window. The existing `ReadItem` remains the eventual item-field decoder; raw validated records are retained for it. Ordinary protocol outcomes and the complete UI are the next acceptance gates.
