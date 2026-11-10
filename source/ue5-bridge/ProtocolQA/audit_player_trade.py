"""Resolve original 1.127 player-trade contracts before adding bridge behavior."""
import argparse,json,re
from pathlib import Path
from prepare_combined_expansion_data import digest

def audit(workspace,install):
    repo=Path(__file__).resolve().parents[3];source=repo/'source';server=source/'server/GameServer';packets=server/'packets/Server'
    inputs={}
    def text(path):
        inputs[str(path)]=digest(path);return path.read_text(encoding='utf-8-sig')
    def implementation(method):
        name='PacketLib1127';chain=[]
        while True:
            path=packets/(name+'.cs');value=text(path);chain.append(name)
            if re.search(r'\b(?:override|virtual)\s+void\s+'+method+r'\s*\(',value):return name,chain
            match=re.search(r'class\s+'+name+r'\s*:\s*(PacketLib\d+)',value);assert match,(method,name)
            name=match[1]
    window,window_chain=implementation('SendTradeWindow');item,item_chain=implementation('WriteItemData')
    assert window=='PacketLib1109' and item=='PacketLib1124'
    codes=text(packets/'IPacketLib.cs');assert re.search(r'TradeWindow\s*=\s*0xEA',codes) and re.search(r'ModifyTrade\s*=\s*0xEB',codes)
    modern=text(packets/'PacketLib1109.cs');legacy=text(packets/'PacketLib168.cs')
    assert 'WriteItemData(pak, item)' in modern and 'pak.Fill(0x00, 40)' in legacy
    modify=text(server/'packets/Client/168/PlayerModifyTradeHandler.cs')
    assert all(token in modify for token in ['isok == 0','isok == 1','isok == 2','i < 10','i < 5','trade.CloseTrade()','trade.TradeUpdate()','trade.AcceptTrade()'])
    move=text(server/'packets/Client/168/PlayerMoveItemRequestHandler.cs')
    assert all(token in move for token in ['toClientSlot - 1000','GIVE_ITEM_DISTANCE','IsAllowedToTrade','ReceiveTradeItem','tradeTarget == client.Player'])
    trade=text(server/'gameutils/PlayerTradeWindow.cs');player=text(server/'gameobjects/GamePlayer.cs')
    assert 'm_tradeAccept = false' in trade and 'm_partnerWindow.m_tradeAccept = false' in trade
    assert 'IsTradable == false' in player and 'TradeWindow != null && source != TradeWindow.Partner' in player
    network=text(source/'new-client/godot/game/net/DaocClient.cs')
    game_ui=text(source/'new-client/godot/game/ui/game_ui.gd');exchange=text(source/'new-client/godot/game/ui/exchange_window.gd')
    assert 'Realm Exchange' in exchange and 'market' in exchange
    assets=[install/'new-client/godot/content/ui/classic'/variant/'trade.png' for variant in ['original','x4plus']]
    for path in assets:inputs[str(path)]=digest(path)
    result=dict(passed=True,scope='Contract audit only; no player trading implementation or acceptance',source_inputs=inputs,
        server_window_implementation=window,server_window_inheritance=window_chain,item_encoding_implementation=item,item_encoding_inheritance=item_chain,
        incoming_code='0xEA',outgoing_code='0xEB',outgoing_wire_header='0xEB in existing Send low-byte header; no additional xor',offer_slots=10,money_denominations=5,close_payload_zero_bytes=40,
        decoder_present=bool(re.search(r'case\s+0xEA\s*:',network)),original_trade_ui_asset_available=True,
        existing_exchange_is_player_trade=False,normal_runtime_modified=False,server_started=False,database_modified=False,
        requirements=['Use 1.127 dynamic WriteItemData, not the 1.68 partner item layout.',
            'Original MoveItem to OID+1000 opens trade; retain ordinary permissions, backpack ownership and give range.',
            'ModifyTrade actions cancel/update/accept; offer updates clear both acceptances.',
            'Forty zero bytes close the window; close alone does not prove a completed exchange.',
            'No explicit acceptance bits occur in this window payload; do not invent authoritative acceptance fields.',
            'Keep item and money outcomes server-owned; confirm inventory and original account/realm money updates.',
            'Use original trade asset, English text and existing item icons; Realm Exchange is a different service.',
            'Prove two ordinary accounts, cancel, changed offer, untradable items, insufficient funds, ownership/save and stale requests before activating.'])
    assert not result['decoder_present'],'Decoder has changed: audit the implementation rather than reporting the old gap.'
    assert all(digest(Path(p))==h for p,h in inputs.items())
    root=workspace/'PlayerTradeLab/Contract';root.mkdir(parents=True,exist_ok=True);path=root/'verified.json';path.write_text(json.dumps(result,indent=2))
    return dict(passed=True,decoder_present=False,window_implementation=window,item_encoding=item,report=str(path))
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ['workspace','install']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();print(json.dumps(audit(a.workspace.resolve(),a.install.resolve())))
