extends SceneTree
var checks := 0
var failures: Array = []
class Client extends RefCounted:
    var calls: Array = []
    func MoveItem(source: int,target: int,count: int) -> void:calls.append([source,target,count])
    func PlayerTrade(action: int,slots: PackedInt32Array,money: PackedInt32Array) -> bool:calls.append([action,Array(slots),Array(money)]);return true
func check(ok: bool,label: String) -> void:
    checks+=1
    if not ok:failures.append(label)
func _init() -> void:
    var control=load("res://player_trade_controller.gd").new()
    var client:=Client.new()
    var inventory=load("res://inventory_state.gd").new()
    inventory.inventory_events=1;inventory.fingerprint="fixture";inventory.state_revision=7
    inventory.items={40:{"slot":40,"name":"Cloak","model":57,"token":"held"}}
    var row:={"kind":"player","name":"Friend","model_id":310,"session_id":2,"position_m":[1,0,0],"state":"idle"}
    var entities:={"player:30":row}
    var request:={"action":"player_trade_begin","slot":40,"item_token":"held","inventory_revision":7,"entity_id":"player:30","target_name":"Friend","target_model":310,"target_session":2}
    var window:={"open":true,"title":"Trading with Friend","own_slots":[40,0,0,0,0,0,0,0,0,0],"own_money":[0,0,0,0,0],"partner_items":[{"slot":0,"name":"2 Cloaks","model":57}]}
    for invalid in [{"slot":10},{"slot":80},{"slot":40.5},{"item_token":"old"},{"inventory_revision":6},{"entity_id":"npc:30"},{"entity_id":"player:local"},{"entity_id":"player:030"},{"entity_id":"player:65535"},{"target_session":1},{"target_session":2.5},{"target_model":318},{"target_name":"Old"}]:
        var bad:Dictionary=request.duplicate(true);bad.merge(invalid,true)
        check(not control.begin(bad,client,inventory,entities,Vector3.ZERO,true,100) and client.calls.is_empty(),"invalid opening identity: "+str(invalid.keys()))
    check(not control.begin(request,client,inventory,entities,Vector3.ZERO,false,100),"dead player cannot open")
    row.position_m=[7,0,0]
    check(not control.begin(request,client,inventory,entities,Vector3.ZERO,true,100),"distant target cannot open")
    row.position_m=[1,0,0];inventory.pending={"kind":"move"}
    check(not control.begin(request,client,inventory,entities,Vector3.ZERO,true,100),"competing inventory operation cannot open")
    inventory.pending.clear();var before:Dictionary=inventory.items.duplicate(true)
    check(control.request(request,client,inventory,entities,Vector3.ZERO,true,100) and client.calls==[[40,1030,1]],"original MoveItem targets actual player OID")
    check(control.blocks_inventory() and not control.state.visible and control.snapshot().get("opening",false),"opening waits for actual server window and blocks competing inventory")
    check(inventory.items==before,"opening does not change ownership")
    check(not control.begin(request,client,inventory,entities,Vector3.ZERO,true,101) and client.calls.size()==1,"duplicate opening blocked")
    control.observe("player_trade",window,entities,Vector3.ZERO,true)
    check(control.state.visible and control.opening.is_empty() and control.blocks_inventory(),"server opens exact pending partner")
    var snapshot:Dictionary=control.snapshot(func(model:int)->int:return 912 if model==57 else -1)
    check(snapshot.offer.partner_items[0].icon==912 and snapshot.offer.partner_items[0].name=="2 Cloaks","existing model icon lookup preserves server stack name")
    check(not control.state.offer.partner_items[0].has("icon"),"icon presentation leaves authoritative record unchanged")
    control.observe("player_trade",{"open":false},entities,Vector3.ZERO,true)
    check(not control.blocks_inventory(),"server close unlocks inventory without claiming completion")
    check(control.begin(request,client,inventory,entities,Vector3.ZERO,true,200),"next ordinary trade can open")
    control.observe("inventory",{},entities,Vector3.ZERO,true);control.flush_cancel(client)
    check(not control.blocks_inventory() and client.calls.back()==[0,[],[]],"original refusal refresh clears hidden trade allocation")
    var count:=client.calls.size();control.flush_cancel(client)
    check(client.calls.size()==count,"hidden allocation cancellation sent once")
    control.begin(request,client,inventory,entities,Vector3.ZERO,true,300);control.maintain(entities,Vector3.ZERO,true,12300)
    check(not control.blocks_inventory() and control.state.cancel_required,"opening timeout cannot claim accepted offer")
    check(not control.begin(request,client,inventory,entities,Vector3.ZERO,true,12301),"new opening waits until old cancel is flushed")
    control.flush_cancel(client);control.begin(request,client,inventory,entities,Vector3.ZERO,true,12400)
    row.session_id=3;control.maintain(entities,Vector3.ZERO,true,12401);control.flush_cancel(client)
    check(not control.blocks_inventory() and client.calls.back()==[0,[],[]],"reused target OID cancels pending opening")
    row.session_id=2
    control.begin(request,client,inventory,entities,Vector3.ZERO,true,12500)
    var other:Dictionary=window.duplicate(true);other.title="Trading with Other"
    entities["player:31"]={"kind":"player","name":"Other","session_id":4,"position_m":[1,0,0]}
    control.observe("player_trade",other,entities,Vector3.ZERO,true)
    check(not control.state.visible and control.state.cancel_required,"unrelated authoritative offer cannot replace pending target")
    control.flush_cancel(client)
    for event in ["you","region_changed","quit","disconnect"]:
        control.begin(request,client,inventory,entities,Vector3.ZERO,true,13000)
        control.observe(event,{},entities,Vector3.ZERO,true);count=client.calls.size();control.flush_cancel(client)
        check(not control.blocks_inventory() and client.calls.size()==count,"lifecycle cannot send old cancel into new session: "+event)
    var report:={"passed":failures.is_empty(),"checks":checks,"failures":failures,"installed":false,"real_server":false}
    print(JSON.stringify(report));quit(0 if failures.is_empty() else 1)
