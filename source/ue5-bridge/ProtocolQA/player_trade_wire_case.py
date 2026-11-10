"""Ordinary original-server trade outcomes through an explicitly QA-only transport hook."""
import json

def prepare(db,characters,leader):
    def insert(table,row):
        keys=list(row);db.execute('INSERT INTO '+table+' ('+','.join('"'+k+'"' for k in keys)+') VALUES ('+','.join('?' for _ in keys)+')',[row[k] for k in keys])
    template=dict(db.execute("SELECT * FROM ItemTemplate WHERE Id_nb='cloak'").fetchone())
    original=dict(db.execute('SELECT * FROM Inventory WHERE OwnerID=? LIMIT 1',(leader['DOLCharacters_ID'],)).fetchone())
    for character in characters:
        funded=db.execute('UPDATE AccountXMoney SET Gold=1,Copper=0,Silver=0,Platinum=0,Mithril=0 WHERE AccountId=? AND Realm=3',(character['AccountName'],));assert funded.rowcount==1
        db.execute('DELETE FROM Inventory WHERE OwnerID=? AND SlotPosition BETWEEN 40 AND 79',(character['DOLCharacters_ID'],))
    by_name={c['Name']:c for c in characters}
    for suffix,name,owner,slot,tradable in [('a','Codex Trade A','Codexdruid',40,1),('b','Codex Trade B','Codexfriend',40,1),('bound','Codex Bound Trade','Codexfriend',41,0)]:
        template_id='codex-private-player-trade-'+suffix
        item=dict(template);item.update(ItemTemplate_ID=template_id,Id_nb=template_id,Name=name,IsTradable=tradable,IsDropable=1);insert('ItemTemplate',item)
        row=dict(original);row.update(Inventory_ID=template_id,OwnerID=by_name[owner]['DOLCharacters_ID'],SlotPosition=slot,ITemplate_Id=template_id,UTemplate_Id='',Count=1,Emblem=0,Color=0,IsCrafted=0,IsROG=0,Condition=item['Condition'],Durability=item['Durability']);insert('Inventory',row)

def run(a,b,wait,settle,result,checked,output):
    def trade(peer):return peer.snapshot.get('qa_player_trade',{})
    def inventory(peer):return peer.snapshot.get('inventory',{})
    def rows(peer,name):return [i for i in inventory(peer).get('items',[]) if i.get('name')==name]
    def money(peer):return sum(inventory(peer).get('money',{}).get(k,0)*v for k,v in [('copper',1),('silver',100),('gold',10000),('platinum',10000000),('mithril',10000000000)])
    def send(peer,**request):peer.send('chat',text='/qa-player-trade '+json.dumps(request,separators=(',',':')))
    def revision(peer):return trade(peer).get('qa_revision',0)
    def update(peer,slots,coins):
        before=revision(peer);send(peer,action=1,slots=slots,money=coins)
        wait(lambda:revision(peer)>before,'Original trade update reply',15)
    def opened():return trade(a).get('open') and trade(b).get('open')
    def closed():return trade(a).get('open') is False and trade(b).get('open') is False
    def open_with(source,target,name):
        target_name='Codexfriend' if target is b else 'Codexdruid'
        local=next(r for r in source.snapshot['entities'] if r['id']=='player:local')
        source.send('move',position_m=local['position_m'],forward_xz=[0,1],speed_mps=0.0,swimming=False,on_ground=True,vertical_speed_mps=0)
        wait(lambda:any(r.get('name')==target_name and r.get('kind')=='player' for r in source.snapshot['entities']),'Actual ordinary target player',15)
        target_row=next(r for r in source.snapshot['entities'] if r.get('name')==target_name and r.get('kind')=='player')
        send(source,op='open',slot=rows(source,name)[0]['slot'],oid=int(target_row['id'].split(':')[1]))
        wait(opened,'Original item handover opens both trade windows',15)
    def cancel(peer):
        before=revision(peer);send(peer,action=0)
        wait(lambda:revision(peer)>before and closed(),'Original cancel closes both windows',15)
    wait(lambda:all(inventory(p).get('ready') for p in [a,b]),'Both original inventories initialized')
    assert rows(a,'Codex Trade A') and rows(b,'Codex Trade B') and rows(b,'Codex Bound Trade')
    assert money(a)==money(b)==10000
    result['checks']['original_private_money_and_items']=True
    # Both original initial movement packets make their current OIDs discoverable.
    for peer in [a,b]:
        local=next(r for r in peer.snapshot['entities'] if r['id']=='player:local')
        peer.send('move',position_m=local['position_m'],forward_xz=[0,1],speed_mps=0.0,swimming=False,on_ground=True,vertical_speed_mps=0)
    settle(.6)
    open_with(a,b,'Codex Trade A')
    assert 40 in trade(a)['own_slots'] and any(i['name']=='Codex Trade A' for i in trade(b)['partner_items'])
    result['checks']['modern_window_and_existing_item_decoder']=all(k in trade(b)['partner_items'][0] for k in ['model','name','condition','quality','object_type'])
    cancel(b)
    result['checks']['cancel_preserves_ownership_and_money']=bool(rows(a,'Codex Trade A') and rows(b,'Codex Trade B') and money(a)==money(b)==10000)
    open_with(a,b,'Codex Trade A');update(a,[40],[0,0,0,1,0]);update(b,[40],[0,0,0,0,25])
    wait(lambda:any(i.get('name')=='Codex Trade B' for i in trade(a).get('partner_items',[])),'Actual partner offer arrives')
    result['checks']['both_offers_and_denomination_order']=trade(a)['own_money']==[0,0,0,1,0] and trade(a)['partner_money']==[0,0,0,0,25]
    send(a,action=2);settle(.5);update(b,[40],[0,0,0,0,50]);send(b,action=2);settle(.8)
    result['checks']['changed_offer_resets_original_acceptances']=bool(opened() and rows(a,'Codex Trade A') and rows(b,'Codex Trade B') and money(a)==money(b)==10000)
    send(a,action=2);wait(closed,'Original two-party acceptance closes transaction',20)
    wait(lambda:rows(a,'Codex Trade B') and rows(b,'Codex Trade A') and not rows(a,'Codex Trade A') and not rows(b,'Codex Trade B'),'Server transfers actual ownership',20)
    wait(lambda:money(a)==9950 and money(b)==10050,'Original authoritative money updates',15)
    result['checks']['original_two_sided_item_exchange']=True
    result['checks']['original_two_sided_money_exchange']=True
    send(a,action=2);send(b,action=2);settle(.6)
    result['checks']['stale_accept_after_close_no_duplicate']=len(rows(a,'Codex Trade B'))==len(rows(b,'Codex Trade A'))==1 and money(a)==9950 and money(b)==10050
    open_with(a,b,'Codex Trade B');update(a,[rows(a,'Codex Trade B')[0]['slot']],[0,0,2,0,0])
    send(a,action=2);send(b,action=2)
    wait(lambda:any("don't have enough money" in e.get('text','') for p in [a,b] for e in p.snapshot.get('chat',{}).get('entries',[])),'Original insufficient-funds refusal',15)
    result['checks']['insufficient_funds_no_partial_transfer']=bool(rows(a,'Codex Trade B') and rows(b,'Codex Trade A') and money(a)==9950 and money(b)==10050)
    cancel(a)
    target_row=next(r for r in b.snapshot['entities'] if r.get('name')=='Codexdruid' and r.get('kind')=='player')
    send(b,op='open',slot=41,oid=int(target_row['id'].split(':')[1]))
    wait(lambda:any("You can't trade this item!" in e.get('text','') for e in b.snapshot.get('chat',{}).get('entries',[])),'Original untradable-item refusal',15)
    result['checks']['ordinary_untradable_item_not_offered']=bool(closed() and rows(b,'Codex Bound Trade')[0]['slot']==41 and money(a)==9950 and money(b)==10050)
    cancel(b)
    (output/'active_trade_snapshots.json').write_text(json.dumps(dict(a=a.snapshot,b=b.snapshot),indent=2))
    for peer in [a,b]:
        peer.send('chat',text='/quit');wait(lambda:not peer.snapshot.get('in_game',True) and peer.snapshot.get('character_lobby',{}).get('ready'),'Original saved return from trade session',90)
    with checked() as db:
        characters={r['Name']:dict(r) for r in db.execute("SELECT * FROM DOLCharacters WHERE Name IN ('Codexdruid','Codexfriend')")}
        owners={r['ITemplate_Id']:r['OwnerID'] for r in db.execute("SELECT OwnerID,ITemplate_Id FROM Inventory WHERE ITemplate_Id LIKE 'codex-private-player-trade-%'")}
        result['checks']['saved_ownership_after_logout']=owners['codex-private-player-trade-b']==characters['Codexdruid']['DOLCharacters_ID'] and owners['codex-private-player-trade-a']==characters['Codexfriend']['DOLCharacters_ID'] and owners['codex-private-player-trade-bound']==characters['Codexfriend']['DOLCharacters_ID']
        saved=[]
        for name in ['Codexdruid','Codexfriend']:
            coins=db.execute('SELECT Copper,Silver,Gold,Platinum,Mithril FROM AccountXMoney WHERE Realm=3 AND AccountId=?',(characters[name]['AccountName'],)).fetchone();saved.append(sum(v*m for v,m in zip(coins,[1,100,10000,10000000,10000000000])))
        result['checks']['saved_original_account_realm_money']=saved==[9950,10050]
