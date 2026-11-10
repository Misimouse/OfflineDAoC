"""Ordinary installed-client cancellation and competing-transaction outcomes."""
import json
from pathlib import Path
from prepare_combined_expansion_data import digest

def run(a,b,wait,settle,result,checked,output):
    result['source_inputs'][str(Path(__file__).resolve())]=digest(Path(__file__).resolve())
    def inv(p):return p.snapshot.get('inventory',{})
    def trade(p):return p.snapshot.get('player_trade',{})
    def item(p):return next(i for i in inv(p).get('items',[]) if i.get('name')==('Codex Trade A' if p is a else 'Codex Trade B'))
    def position(p):return next(r['position_m'] for r in p.snapshot['entities'] if r['id']=='player:local')
    def move(p,point):p.send('move',position_m=point,forward_xz=[0,1],speed_mps=0.0,swimming=False,on_ground=True,vertical_speed_mps=0)
    def unchanged():return item(a)['slot']==40 and item(b)['slot']==40 and all(inv(p).get('money',{}).get('gold')==1 for p in [a,b])
    def open_trade():
        row=next(r for r in a.snapshot['entities'] if r.get('kind')=='player' and r.get('name')=='Codexfriend')
        source=item(a)
        a.send('player_trade_begin',slot=source['slot'],item_token=source['token'],inventory_revision=inv(a)['state_revision'],entity_id=row['id'],target_name=row['name'],target_model=row['model_id'],target_session=row['session_id'])
        wait(lambda:trade(a).get('visible') and trade(b).get('visible'),'Original server opens lifecycle trade')
        return trade(a)['token']
    wait(lambda:all(inv(p).get('ready') for p in [a,b]),'Installed lifecycle inventories ready')
    for p in [a,b]:move(p,position(p))
    wait(lambda:all(any(r.get('name')==name and r.get('kind')=='player' and r.get('session_id',0)>0 for r in peer.snapshot['entities']) for peer,name in [(a,'Codexfriend'),(b,'Codexdruid')]),'Both ordinary identities discoverable')
    settle(.6)
    first=open_trade();source=dict(item(a));before=json.loads(json.dumps(inv(a)))
    for action,values in [
        ('inventory_move',dict(slot=40,to_slot=42,item_token=source['token'],inventory_revision=before['state_revision'])),
        ('inventory_equip',dict(slot=40,item_token=source['token'],inventory_revision=before['state_revision'])),
        ('merchant_sell',dict(slot=40,item_token=source['token'],inventory_revision=before['state_revision']))]:
        a.send(action,**values);settle(.4)
        assert trade(a).get('visible') and unchanged() and not inv(a).get('pending')
        assert 'Finish the player trade first.' in inv(a).get('feedback','')
        result['checks']['open_trade_blocks_'+action]=True
    a.send('player_trade_accept',trade_token=first);wait(lambda:trade(a).get('pending'),'Acceptance waits for other player')
    a.send('player_trade_cancel',trade_token=trade(a)['token']);wait(lambda:not trade(a).get('visible') and not trade(b).get('visible'),'Cancel remains available after acceptance')
    result['checks']['cancel_after_accept_preserves_inventory']=unchanged()
    previous=open_trade();origin=list(position(b))
    for offset in [4.0,8.0]:
        point=list(origin);point[0]+=offset;move(b,point);settle(.4)
    wait(lambda:not trade(a).get('visible') and not trade(b).get('visible'),'Partner distance closes original trade')
    result['checks']['partner_distance_cancels_without_transfer']=unchanged()
    a.send('player_trade_accept',trade_token=previous);settle(.4)
    result['checks']['old_accept_after_distance_cannot_transfer']=unchanged() and not trade(a).get('visible')
    for offset in [4.0,0.0]:
        point=list(origin);point[0]+=offset;move(b,point);settle(.4)
    wait(lambda:any(r.get('name')=='Codexfriend' and abs(r['position_m'][0]-origin[0])<.2 for r in a.snapshot['entities']),'Partner returns to original nearby position')
    current=open_trade();result['checks']['reopening_has_fresh_offer_token']=current not in [first,previous]
    a.send('player_trade_accept',trade_token=previous);settle(.4)
    result['checks']['previous_offer_cannot_accept_reopened_trade']=not trade(a).get('pending') and unchanged()
    b.send('chat',text='/quit')
    wait(lambda:not b.snapshot.get('in_game',True) and b.snapshot.get('character_lobby',{}).get('ready'),'Ordinary partner saved logout',90)
    wait(lambda:not trade(a).get('visible') and not trade(a).get('opening',False),'Partner logout clears trade')
    result['checks']['partner_logout_unlocks_remaining_player']=item(a)['slot']==40 and not inv(a).get('pending')
    source=dict(item(a));a.send('inventory_move',slot=40,to_slot=42,item_token=source['token'],inventory_revision=inv(a)['state_revision'])
    wait(lambda:item(a)['slot']==42 and not inv(a).get('pending'),'Inventory recovers after partner logout')
    result['checks']['inventory_operation_recovers_after_trade']=True
    a.send('chat',text='/quit');wait(lambda:not a.snapshot.get('in_game',True) and a.snapshot.get('character_lobby',{}).get('ready'),'Remaining ordinary player saves normally',90)
    with checked() as db:
        characters={r['Name']:dict(r) for r in db.execute("SELECT * FROM DOLCharacters WHERE Name IN ('Codexdruid','Codexfriend')")}
        rows=[dict(r) for r in db.execute("SELECT OwnerID,SlotPosition,ITemplate_Id FROM Inventory WHERE ITemplate_Id IN ('codex-private-player-trade-a','codex-private-player-trade-b')")]
        result['checks']['cancelled_goods_saved_without_transfer_or_duplicate']=len(rows)==2 and any(r['OwnerID']==characters['Codexdruid']['DOLCharacters_ID'] and r['SlotPosition']==42 and r['ITemplate_Id']=='codex-private-player-trade-a' for r in rows) and any(r['OwnerID']==characters['Codexfriend']['DOLCharacters_ID'] and r['SlotPosition']==40 and r['ITemplate_Id']=='codex-private-player-trade-b' for r in rows)
    (output/'lifecycle_outcomes.json').write_text(json.dumps(result['checks'],indent=2))
