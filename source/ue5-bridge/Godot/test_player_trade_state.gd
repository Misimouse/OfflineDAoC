extends SceneTree
var checks := 0
var failures: Array = []
class Client extends RefCounted:
    var calls: Array = []
    var allowed := true
    func PlayerTrade(action: int, slots: PackedInt32Array, money: PackedInt32Array) -> bool:
        calls.append([action, Array(slots), Array(money)])
        return allowed
func check(ok: bool, label: String) -> void:
    checks += 1
    if not ok: failures.append(label)
func _init() -> void:
    var state = load("res://player_trade_state.gd").new()
    var client := Client.new()
    var row := {"kind":"player", "name":"Friend", "session_id":2, "position_m":[1,0,0], "state":"idle"}
    var entities := {"player:30":row}
    var window := {"kind":"player_trade", "open":true, "title":"Trading with Friend", "own_slots":[40,0,0,0,0,0,0,0,0,0], "own_money":[0,0,0,1,0], "partner_items":[{"slot":0,"name":"Cloak","model":57}]}
    check(not state.request({"action":"player_trade_accept"},client,entities,Vector3.ZERO,true),"local command cannot open trade")
    state.observe("player_trade",window,entities,Vector3.ZERO,true)
    check(state.visible and state.partner_id=="player:30" and state.partner_session==2,"authoritative window binds actual player session")
    var first: String = state.token
    var original: Dictionary = state.offer.duplicate(true)
    var request := {"action":"player_trade_accept", "trade_token":first}
    check(state.request(request,client,entities,Vector3.ZERO,true) and client.calls.back()==[2,[],[]],"accept uses original action without local offer fabrication")
    check(state.pending and state.offer==original and not state.snapshot().has("accepted"),"local acceptance cannot claim server outcome")
    check(not state.request(request,client,entities,Vector3.ZERO,true) and client.calls.size()==1,"duplicate click blocked while waiting")
    state.observe("player_trade",window,entities,Vector3.ZERO,true)
    check(not state.pending and state.token!=first,"even identical server update revokes prior acceptance token")
    check(not state.request(request,client,entities,Vector3.ZERO,true),"stale acceptance cannot accept new offer")
    request.trade_token=state.token
    client.allowed=false
    check(not state.request(request,client,entities,Vector3.ZERO,true) and not state.pending,"failed send does not lock window")
    client.allowed=true
    var view: Dictionary=state.snapshot();view.offer.title="Altered"
    check(state.offer.title==window.title,"snapshot does not expose mutable offer")
    request.action="player_trade_cancel"
    check(state.request(request,client,entities,Vector3.ZERO,true) and client.calls.back()==[0,[],[]],"cancel sends original cancel action")
    state.observe("player_trade",{"open":false},entities,Vector3.ZERO,true)
    check(not state.visible and state.token=="" and not state.pending and not state.take_cancel(),"server close clears state without announcing success")
    for event in ["you","region_changed","quit","disconnect"]:
        state.observe("player_trade",window,entities,Vector3.ZERO,true)
        state.observe(event,{},entities,Vector3.ZERO,true)
        check(not state.visible and not state.take_cancel(),"lifecycle clears old-session requests: "+event)
    state.observe("player_trade",window,entities,Vector3.ZERO,true)
    row.session_id=3;state.maintain(entities,Vector3.ZERO,true)
    check(not state.visible and state.take_cancel() and not state.take_cancel(),"reused OID with new session invalidates and requests one cancel")
    row.session_id=2
    state.observe("player_trade",window,entities,Vector3.ZERO,true);row.position_m=[7,0,0];state.maintain(entities,Vector3.ZERO,true)
    check(not state.visible and state.take_cancel(),"leaving range invalidates")
    row.position_m=[1,0,0]
    state.observe("player_trade",window,entities,Vector3.ZERO,true);state.maintain({},Vector3.ZERO,true)
    check(not state.visible and state.take_cancel(),"removed partner invalidates")
    state.observe("player_trade",window,entities,Vector3.ZERO,true);state.maintain(entities,Vector3.ZERO,false)
    check(not state.visible and state.take_cancel(),"local death invalidates")
    entities["player:31"]=row.duplicate(true)
    state.observe("player_trade",window,entities,Vector3.ZERO,true)
    check(not state.visible and state.take_cancel(),"ambiguous partner name cannot authorize")
    entities.erase("player:31")
    for invalid in [{"kind":"npc"},{"position_m":[]},{"position_m":[NAN,0,0]},{"session_id":0},{"state":"dead"}]:
        var bad: Dictionary=row.duplicate(true);bad.merge(invalid,true)
        state.observe("player_trade",window,{"player:30":bad},Vector3.ZERO,true)
        check(not state.visible and state.take_cancel(),"invalid partner rejected: "+str(invalid.keys()))
    state.observe("player_trade",window,entities,Vector3.ZERO,true)
    var other: Dictionary=window.duplicate(true);other.title="Trading with Other"
    entities["player:31"]={"kind":"player","name":"Other","session_id":4,"position_m":[1,0,0]}
    state.observe("player_trade",other,entities,Vector3.ZERO,true)
    check(not state.visible and state.take_cancel(),"partner replacement cannot reuse open trade")
    state.reset();entities.erase("player:31");state.observe("player_trade",window,entities,Vector3.ZERO,true)
    var inventory=load("res://inventory_state.gd").new()
    inventory.inventory_events=1;inventory.fingerprint="fixture";inventory.state_revision=7
    inventory.items={40:{"slot":40,"name":"Cloak","model":57,"token":"item-a"}}
    var before: Dictionary=inventory.items.duplicate(true)
    var update := {"trade_token":state.token,"inventory_revision":7,"slots":[40],"money":[0,0,0,1,0],"item_tokens":{"40":"item-a"}}
    check(state.update_offer(update,client,inventory,entities,Vector3.ZERO,true) and client.calls.back()==[1,[40],[0,0,0,1,0]],"validated offer sends original slots and denomination order")
    check(inventory.items==before and state.offer==window and state.pending,"offer edit never predicts inventory or server offer")
    check(not state.update_offer(update,client,inventory,entities,Vector3.ZERO,true),"duplicate update blocked")
    state.observe("player_trade",window,entities,Vector3.ZERO,true);update.trade_token=state.token
    for invalid in [{"inventory_revision":6},{"slots":[10]},{"slots":[80]},{"slots":[40,40]},{"slots":[40.5]},{"slots":[40],"item_tokens":{"40":"stale"}},{"money":[0,0,0,1]},{"money":[0,0,0,-1,0]},{"money":[0,0,0,65536,0]},{"money":[0,0,0,1.5,0]}]:
        var bad: Dictionary=update.duplicate(true);bad.merge(invalid,true)
        var count := client.calls.size()
        check(not state.update_offer(bad,client,inventory,entities,Vector3.ZERO,true) and client.calls.size()==count,"invalid outgoing offer blocked: "+str(invalid.keys()))
    inventory.pending={"kind":"move"}
    check(not state.update_offer(update,client,inventory,entities,Vector3.ZERO,true),"inventory operation and trade update cannot race")
    inventory.pending.clear()
    update.slots=[];update.item_tokens={};update.money=[0,0,0,0,0]
    check(state.update_offer(update,client,inventory,entities,Vector3.ZERO,true) and client.calls.back()==[1,[],[0,0,0,0,0]],"removing all offered items sends authoritative update")
    request={"action":"player_trade_cancel","trade_token":state.token}
    check(state.request(request,client,entities,Vector3.ZERO,true),"cancel remains available while an update or refusal waits")
    check(not state.request(request,client,entities,Vector3.ZERO,true),"duplicate cancel blocked until server reply")
    var report := {"passed":failures.is_empty(),"checks":checks,"failures":failures,"installed":false,"real_server":false}
    print(JSON.stringify(report));quit(0 if failures.is_empty() else 1)
