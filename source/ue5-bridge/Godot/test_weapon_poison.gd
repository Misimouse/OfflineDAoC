extends SceneTree
class Client extends Node:
    var calls:Array=[]
    func MoveItem(a:int,b:int,n:int)->void:calls.append([a,b,n])
var checks:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func _initialize()->void:
    var state=load("res://inventory_state.gd").new()
    var inter=load("res://interaction_state.gd").new()
    var client:=Client.new()
    var rows:Array=[{"slot":40,"name":"Original poison","object_type":46,"item_type":40,"count":3},{"slot":10,"name":"Sword","object_type":21,"item_type":10,"count":1},{"slot":11,"name":"Shield","object_type":42,"item_type":11,"count":1},{"slot":12,"name":"Staff","object_type":8,"item_type":12,"count":1},{"slot":13,"name":"Bow","object_type":15,"item_type":13,"count":1},{"slot":25,"name":"Armor","object_type":32,"item_type":25,"count":1}]
    state.observe("inventory");state.sync(rows,{"gold":1},{},"standard",1,100,0)
    var command:Dictionary={"action":"inventory_move","slot":40,"to_slot":10,"item_token":state.items[40].token,"inventory_revision":state.state_revision}
    for slot in [10,11,12,13]:
        command.to_slot=slot
        check(state.execute(command,client,inter,{},Vector3.ZERO,1),"original occupied weapon slot request %d"%slot)
        check(client.calls.back()==[40,slot,3],"original MoveItem stack arguments %d"%slot)
        check(state.items[40].count==3 and state.money.gold==1,"no local poison or coin consumption %d"%slot)
        state.observe("inventory");state.sync(rows,{"gold":1},{},"standard",1,100,2)
        check(state.pending.is_empty(),"unchanged server refusal unlocks item application %d"%slot)
    command.to_slot=25
    check(not state.execute(command,client,inter,{},Vector3.ZERO,3),"poison cannot be equipped as armor")
    command.to_slot=10;command.action="inventory_equip"
    check(not state.execute(command,client,inter,{},Vector3.ZERO,3),"double click does not invent poison equipment")
    command.action="inventory_move";command.item_token="stale"
    check(not state.execute(command,client,inter,{},Vector3.ZERO,3),"stale vial identity rejected")
    command.item_token=state.items[40].token;command.inventory_revision=-1
    check(not state.execute(command,client,inter,{},Vector3.ZERO,3),"stale target/inventory revision rejected")
    command.inventory_revision=state.state_revision;inter.dialogs=[{"id":1}]
    check(not state.execute(command,client,inter,{},Vector3.ZERO,3),"confirmation cannot be bypassed")
    inter.dialogs=[]
    check(state.execute(command,client,inter,{},Vector3.ZERO,4),"application awaits authoritative result")
    check(not state.execute(command,client,inter,{},Vector3.ZERO,5),"duplicate blocked")
    check(not bool(state.pending.equipment_request),"poison request is not an equip transaction")
    state.observe("inventory");rows[0].count=2;state.sync(rows,{"gold":1},{},"standard",1,100,6)
    check(state.items[40].count==2 and state.pending.is_empty(),"one vial consumed only after server update")
    command.inventory_revision=state.state_revision;command.item_token=state.items[40].token
    rows.remove_at(1);state.observe("inventory");state.sync(rows,{"gold":1},{},"standard",1,100,7)
    command.inventory_revision=state.state_revision
    check(not state.execute(command,client,inter,{},Vector3.ZERO,8),"empty worn slot cannot swallow vial")
    state.reset()
    check(state.items.is_empty() and state.pending.is_empty(),"logout clears application state")
    print(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures}))
    client.free();quit(0 if failures.is_empty() else 1)
