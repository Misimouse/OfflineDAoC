extends SceneTree
class FakeClient extends Node:
    var calls:Array=[]
    func MoveItem(a:int,b:int,n:int)->void:calls.append(["move",a,b,n])
    func Target(oid,flags):calls.append(["target",oid,flags])
    func BuyItem(x:int,y:int,s:int,n:int,m:int)->void:calls.append(["buy",x,y,s,n,m])
    func SellItem(x:int,y:int,s:int)->void:calls.append(["sell",x,y,s])
var failures:Array=[]
var checks:=0
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func _initialize()->void:
    var state=load("res://inventory_state.gd").new()
    var inter=load("res://interaction_state.gd").new()
    var client:=FakeClient.new()
    var rows:Array=[{"slot":40,"count":2,"name":"Sword","model":1,"item_type":11,"object_type":1},{"slot":11,"count":1,"name":"Shield","model":2,"item_type":11,"object_type":42},{"slot":200,"name":"Not my backpack"}]
    var coins:Dictionary={"gold":2,"silver":3,"copper":4,"platinum":1,"mithril":1}
    var pos:=Vector3(1400,130,1250)
    var entities:Dictionary={"npc:7":{"id":"npc:7","kind":"npc","name":"Trader","position_m":[1401,130,1250],"health":1}}
    state.sync(rows,coins,{},"standard",10,100,0)
    check(not state.execute({"action":"merchant_buy"},client,inter,entities,pos,0),"commands wait for real inventory availability")
    state.observe("inventory")
    check(state.items.size()==2,"only personal equipment and backpack exposed")
    check(state.total_copper()==10010020304,"DAoC denomination conversion")
    var revision:int=state.state_revision;var token:String=state.items[40].token
    state.sync(rows,coins,{},"standard",10,100,1)
    check(state.state_revision==revision,"identical snapshots keep item handles valid")
    var cmd:Dictionary={"action":"inventory_equip","slot":40,"inventory_revision":revision,"item_token":token}
    check(state.execute(cmd,client,inter,entities,pos,10),"equip request")
    check(client.calls.back()==["move",40,10,2],"equipment uses original MoveItem protocol and free suitable hand")
    check(state.items.has(40) and not state.items.has(10),"no optimistic inventory mutation")
    check(not state.execute(cmd,client,inter,entities,pos,11),"duplicate blocked awaiting server")
    state.observe("inventory");rows[0].slot=10;state.sync(rows,coins,{},"standard",10,100,20)
    check(state.pending.is_empty() and state.items.has(10) and not state.items.has(40),"real server update confirms state")
    check(not state.execute(cmd,client,inter,entities,pos,21),"old revision cannot move replacement item")
    cmd={"action":"inventory_unequip","slot":10,"inventory_revision":state.state_revision,"item_token":state.items[10].token}
    check(state.execute(cmd,client,inter,entities,pos,22),"unequip request")
    check(client.calls.back()==["move",10,40,2],"unequip finds first free backpack slot")
    state.sync(rows,coins,{},"standard",10,100,13000)
    check(state.pending.is_empty() and state.feedback.contains("No confirmation"),"timeout reports uncertainty without retry")
    var before:=client.calls.size()
    check(not state.execute({"action":"inventory_move","slot":10,"to_slot":11,"item_token":"wrong","inventory_revision":state.state_revision},client,inter,entities,pos,13001),"wrong item token rejected")
    check(not state.execute({"action":"inventory_move","slot":10,"to_slot":999,"item_token":state.items[10].token,"inventory_revision":state.state_revision},client,inter,entities,pos,13001),"no world drop or destroy route")
    check(not state.execute({"action":"inventory_move","slot":11,"to_slot":10,"item_token":state.items[11].token,"inventory_revision":state.state_revision},client,inter,entities,pos,13001),"shield cannot occupy right hand")
    check(client.calls.size()==before,"invalid item commands never reach network client")
    check(not state.execute({"action":"inventory_move","slot":10.5,"to_slot":40,"item_token":state.items[10].token,"inventory_revision":state.state_revision},client,inter,entities,pos,13001),"fractional source cannot silently select another slot")
    check(not state.execute({"action":"inventory_move","slot":10,"to_slot":"40","item_token":state.items[10].token,"inventory_revision":state.state_revision},client,inter,entities,pos,13001),"string destination is not a game slot")
    inter.selected_id="npc:7";inter.conversation_id="npc:7"
    inter.consume("merchant",{"page":2,"window":0,"items":[{"index":3,"name":"Cloak","price":100}]},entities,1)
    var buy:Dictionary={"action":"merchant_buy","page":2,"index":3,"count":1,"merchant_id":"npc:7","merchant_revision":inter.merchant.catalog_revision,"inventory_revision":state.state_revision}
    check(state.execute(buy,client,inter,entities,pos,14000),"buy offered item")
    check(client.calls[-2]==["target",7,0xE000],"buy restores the actual merchant target before the transaction")
    check(client.calls.back()==["buy",1400*40+35*8192,1250*40+51*8192,63,1,0],"buy uses region position, page*30+index and currency menu")
    check(state.money=={"mithril":1,"platinum":1,"gold":2,"silver":3,"copper":4},"no invented coin deduction")
    state.sync(rows,coins,{},"standard",10,100,27000)
    buy.index=4;check(not state.execute(buy,client,inter,entities,pos,27001),"unoffered merchant item rejected")
    buy.index=3;buy.count=2;check(not state.execute(buy,client,inter,entities,pos,27001),"no hidden multi-buy")
    buy.count=1
    check(not state.execute(buy,client,inter,entities,pos+Vector3(20,0,0),27001),"merchant distance checked at action time")
    inter.consume("merchant",{"page":2,"window":0,"items":[{"index":3,"name":"Changed","price":200}]},entities,2)
    check(not state.execute(buy,client,inter,entities,pos,27001),"catalog version prevents stale price purchase")
    buy.merchant_revision=inter.merchant.catalog_revision
    state.sync(rows,{}, {},"standard",10,100,27002);buy.inventory_revision=state.state_revision
    check(not state.execute(buy,client,inter,entities,pos,27003),"insufficient funds guarded")
    state.sync(rows,coins,{},"standard",10,100,27004);buy.inventory_revision=state.state_revision
    inter.merchant.window=1
    check(not state.execute(buy,client,inter,entities,pos,27005),"special currencies and services require own integration")
    inter.merchant.window=0;inter.dialogs=[{"id":1}]
    check(not state.execute(buy,client,inter,entities,pos,27005),"pending confirmation not bypassed")
    inter.dialogs=[];rows[0].slot=40;state.sync(rows,coins,{},"standard",10,100,27006)
    var sell:Dictionary={"action":"merchant_sell","slot":40,"item_token":state.items[40].token,"inventory_revision":state.state_revision,"merchant_id":"npc:7","merchant_revision":inter.merchant.catalog_revision}
    check(state.execute(sell,client,inter,entities,pos,27007),"sell backpack item through open merchant")
    check(client.calls[-2]==["target",7,0xE000],"sale restores the actual merchant target before the transaction")
    check(client.calls.back()==["sell",1400*40+35*8192,1250*40+51*8192,40],"sell original server command")
    check(state.items.has(40),"sale awaits actual inventory packet")
    var fixture:=FileAccess.open("res://../Reports/inventory/fixture.json",FileAccess.WRITE)
    fixture.store_string(JSON.stringify({"inventory":state.snapshot(),"interaction":inter.snapshot(entities,pos)},"  "));fixture.close()
    state.reset();check(state.items.is_empty() and state.money.is_empty() and state.pending.is_empty(),"session reset clears account state")
    var f:=FileAccess.open("res://../Reports/inventory/godot_tests.json",FileAccess.WRITE)
    f.store_string(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures},"  "));f.close()
    print("Inventory checks: ",checks," failures: ",failures)
    client.free();quit(0 if failures.is_empty() else 1)
