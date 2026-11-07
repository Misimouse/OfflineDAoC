extends SceneTree
class FakeClient extends Node:
    var calls:Array=[]
    func MoveItem(a:int,b:int,n:int)->void:calls.append([a,b,n])
var failures:Array=[]
var checks:=0
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func _initialize()->void:
    var state=load("res://inventory_state.gd").new()
    var interaction=load("res://interaction_state.gd").new()
    var client:=FakeClient.new()
    var rows:Array=[{"slot":25,"count":1,"name":"Cloth robe","model":378,"item_type":25,"object_type":32},{"slot":40,"count":1,"name":"Plate vest","model":810,"item_type":25,"object_type":36}]
    state.sync(rows,{"copper":50},{},"standard",10,100,0);state.observe("inventory")
    var original:Dictionary=state.snapshot().duplicate(true)
    var command:Dictionary={"action":"inventory_equip","slot":40,"item_token":state.items[40].token,"inventory_revision":state.state_revision}
    check(state.execute(command,client,interaction,{},Vector3.ZERO,1),"class permission is decided by the original server")
    check(client.calls==[[40,25,1]] and not state.pending.is_empty(),"request uses original move packet and awaits confirmation")
    state.observe("message",{"text":"NPC says, You have no skill in wearing this armor type!"})
    check(not state.pending.is_empty(),"NPC speech cannot acknowledge an equipment request")
    state.observe("message",{"text":"You begin casting a spell!"})
    check(not state.pending.is_empty(),"unrelated server messages do not acknowledge equipment")
    const DENIAL:="You have no skill in wearing this armor type!"
    state.observe("message",{"text":DENIAL})
    check(state.pending.is_empty() and state.feedback==DENIAL and state.rejected==1,"original armour refusal immediately finishes the request")
    check(state.snapshot().items==original.items and state.money==original.money and state.state_revision==original.state_revision,"rejection never changes server-owned items coins or tokens")
    check(state.execute(command,client,interaction,{},Vector3.ZERO,2),"inventory can be used again after refusal")
    state.observe("message",{"text":"You have no skill in using this weapon type!"})
    check(state.pending.is_empty() and state.rejected==2,"original weapon skill refusal also finishes equipment request")
    state.observe("message",{"text":DENIAL})
    check(state.rejected==2,"late refusal without an outstanding move does not alter request state")
    state.pending={"action":"merchant_buy","until_ms":100,"inventory_events":1}
    state.observe("message",{"text":DENIAL})
    check(not state.pending.is_empty(),"class refusal cannot cancel an unrelated purchase")
    state.pending={"action":"inventory_move","until_ms":100,"inventory_events":1,"equipment_request":false}
    state.observe("message",{"text":DENIAL})
    check(not state.pending.is_empty(),"class refusal cannot cancel a backpack-only move")
    state.reset();state.sync(rows,{"copper":50},{},"standard",10,100,0);state.observe("inventory")
    for text in ["You cannot equip an item from another realm!","Your class cannot use this item!"]:
        command.inventory_revision=state.state_revision;command.item_token=state.items[40].token
        check(state.execute(command,client,interaction,{},Vector3.ZERO,3),"original class/realm request remains server-authoritative")
        state.observe("message",{"text":"NPC says, "+text})
        check(not state.pending.is_empty(),"quoted refusal is not the transaction result")
        state.observe("message",{"text":text})
        check(state.pending.is_empty() and state.feedback==text,"exact original class/realm refusal releases pending equip")
        check(state.items[40].token==command.item_token and state.money.copper==50,"realm/class refusal preserves authoritative items and money")
        var rejected_before:int=state.rejected
        state.observe("message",{"text":text})
        check(state.rejected==rejected_before,"late class/realm reply cannot reject a finished request")
    state.pending={"action":"inventory_move","until_ms":100,"inventory_events":1,"equipment_request":false,"item_application":true}
    state.observe("message",{"text":"Your class cannot use this item!"})
    check(not state.pending.is_empty(),"equip-only reply cannot cancel a poison application")
    state.pending={"action":"inventory_give","until_ms":100,"inventory_events":1,"equipment_request":false}
    state.observe("message",{"text":"You cannot equip an item from another realm!"})
    check(not state.pending.is_empty(),"equip-only reply cannot cancel an NPC handover")
    client.free()
    var file:=FileAccess.open("res://../Reports/inventory_rejection/godot_tests.json",FileAccess.WRITE)
    file.store_string(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures},"  "));file.close()
    print("Inventory denial checks: ",checks," failures: ",failures);quit(0 if failures.is_empty() else 1)
