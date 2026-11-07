extends SceneTree
class Client extends Node:
    var calls:Array=[]
    func MoveItem(a:int,b:int,n:int)->void:calls.append([a,b,n])
var checks:=0
var failures:Array=[]
func check(value:bool,label:String)->void:
    checks+=1
    if not value:failures.append(label)
func _initialize()->void:
    var state=load("res://inventory_state.gd").new()
    var interaction=load("res://interaction_state.gd").new()
    var client:=Client.new()
    var rows:Array=[{"slot":40,"name":"QA Cloak","count":3,"model":57,"item_type":26},{"slot":11,"name":"QA Shield","count":1,"model":60,"item_type":11,"object_type":42}]
    var coins:Dictionary={"gold":100}
    var npc:Dictionary={"id":"npc:7","kind":"npc","name":"Emblemer","model_id":1984,"health":1,"position_m":[1,0,0]}
    var entities:Dictionary={"npc:7":npc,"npc:8":{"id":"npc:8","kind":"npc","name":"Previous target","model_id":5,"health":1,"position_m":[1,0,0]}}
    state.sync(rows,coins,{},"standard",0,100,0)
    var command:Dictionary={"action":"inventory_give","slot":40,"item_token":state.items[40].token,"inventory_revision":state.state_revision,"entity_id":"npc:7","target_name":"Emblemer","target_model":1984}
    check(not state.execute(command,client,interaction,entities,Vector3.ZERO,1),"wait for original inventory availability")
    state.observe("inventory");interaction.selected_id="npc:8"
    var original:Dictionary=state.snapshot().duplicate(true)
    check(state.execute(command,client,interaction,entities,Vector3.ZERO,2),"current NPC under pointer accepts a handover request")
    check(client.calls==[[40,1007,3]],"original move packet uses the dropped-on NPC, not the previous selection")
    check(state.snapshot().items==original.items and state.money==original.money,"request changes no item or coins optimistically")
    check(not state.execute(command,client,interaction,entities,Vector3.ZERO,3) and client.calls.size()==1,"duplicate request blocked until original inventory response")
    state.observe("inventory");state.sync(rows,coins,{},"standard",0,100,4)
    check(state.pending.is_empty() and state.feedback.contains("NPC's response"),"unchanged original slot response releases request without claiming acceptance")
    check(state.state_revision==original.state_revision and state.money==original.money,"unchanged response preserves identities and balance")
    for field in ["item_token","inventory_revision","target_name","target_model","entity_id"]:
        var bad:Dictionary=command.duplicate();bad[field]="stale" if field in ["item_token","target_name","entity_id"] else -1
        var before:=client.calls.size()
        check(not state.execute(bad,client,interaction,entities,Vector3.ZERO,5) and client.calls.size()==before,"reject stale "+field)
    for id in ["player:7","player:local","npc:0","npc:64536","npc:07","npc:7.0","npc:abc",""]:
        var bad:Dictionary=command.duplicate();bad.entity_id=id
        check(not state.execute(bad,client,interaction,entities,Vector3.ZERO,6),"reject non-NPC or non-encodable target "+id)
    check(not state.execute(command,client,interaction,{},Vector3.ZERO,7),"removed NPC cannot receive an item")
    npc.kind="player";check(not state.execute(command,client,interaction,entities,Vector3.ZERO,8),"reused object ID cannot start unsupported player trade");npc.kind="npc"
    npc.health=0;check(not state.execute(command,client,interaction,entities,Vector3.ZERO,9),"dead NPC rejected");npc.health=1
    npc.targetable=false;check(not state.execute(command,client,interaction,entities,Vector3.ZERO,10),"untargetable ambient object rejected");npc.erase("targetable")
    npc.position_m=[3.21,0,0];check(not state.execute(command,client,interaction,entities,Vector3.ZERO,11),"original 128-unit give range respected")
    npc.position_m=[];check(not state.execute(command,client,interaction,entities,Vector3.ZERO,12),"unknown target position rejected")
    npc.position_m=[1,0,0];interaction.dialogs=[{"id":1}]
    check(not state.execute(command,client,interaction,entities,Vector3.ZERO,13),"pending original confirmation cannot be bypassed");interaction.dialogs=[]
    state.items[110]={"slot":110,"token":"vault","count":1}
    var vault:Dictionary=command.duplicate();vault.slot=110;vault.item_token="vault"
    check(not state.execute(vault,client,interaction,entities,Vector3.ZERO,14),"vault item cannot be given directly");state.items.erase(110)
    check(not state.execute(command,null,interaction,entities,Vector3.ZERO,15),"lost server connection rejected")
    var worn:Dictionary=command.duplicate();worn.slot=11;worn.item_token=state.items[11].token
    check(state.execute(worn,client,interaction,entities,Vector3.ZERO,16) and client.calls.back()==[11,1007,1],"equipped service eligibility remains an original server decision")
    state.observe("inventory");state.sync(rows,coins,{},"standard",0,100,17)
    npc.position_m=[3.2,0,0];check(state.execute(command,client,interaction,entities,Vector3.ZERO,18),"floating-point boundary retains original give range")
    state.sync(rows,coins,{},"standard",0,100,13000)
    check(state.pending.is_empty() and state.feedback.contains("No confirmation"),"missing response times out without an automatic retry")
    npc.position_m=[1,0,0];check(state.execute(command,client,interaction,entities,Vector3.ZERO,13001),"can request again after explicit timeout")
    rows[0].emblem=131071;coins.gold=95;state.observe("inventory");state.sync(rows,coins,{},"standard",0,100,13002)
    check(state.items[40].emblem==131071 and state.money.gold==95 and state.pending.is_empty(),"only original server item and coin updates apply the emblem and cost")
    check(not state.execute(command,client,interaction,entities,Vector3.ZERO,13003),"old item identity cannot hand over a changed item")
    state.reset();check(state.pending.is_empty() and state.items.is_empty(),"logout clears held-item context and pending request")
    client.free();print(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures}));quit(0 if failures.is_empty() else 1)
