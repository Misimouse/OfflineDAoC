extends SceneTree
class FakeClient extends Node:
    var calls:Array=[]
    func Target(oid,flags):calls.append(["target",oid,flags])
    func BuyItem(x,y,s,n,m):calls.append(["buy",x,y,s,n,m])
var failures:Array=[]
var checks:=0
func check(value:bool,label:String)->void:
    checks+=1
    if not value:failures.append(label)
func _initialize()->void:
    var s=load("res://inventory_state.gd").new()
    var inter=load("res://interaction_state.gd").new()
    var c:=FakeClient.new()
    var pos:=Vector3.ZERO
    var entities:Dictionary={"npc:7":{"id":"npc:7","kind":"npc","name":"Trader","position_m":[1,0,0],"health":1}}
    inter.selected_id="npc:7";inter.conversation_id="npc:7"
    inter.consume("merchant",{"page":0,"window":0,"items":[{"index":0,"name":"Free test item","price":0}]},entities,1)
    s.sync([],{}, {},"standard",0,100,0)
    var buy:Dictionary={"action":"merchant_buy","page":0,"index":0,"count":1,"merchant_id":"npc:7","merchant_revision":inter.merchant.catalog_revision,"inventory_revision":s.state_revision}
    check(not s.snapshot().ready,"an empty local cache is not server confirmation")
    check(not s.execute(buy,c,inter,entities,pos,1),"cannot purchase before initialization")
    s.observe("status",{});check(not s.snapshot().ready,"unrelated events do not initialize inventory")
    s.observe("money",{"copper":-1});check(not s.snapshot().ready,"invalid money message is not initialization")
    s.observe("money",{"copper":0,"silver":0,"gold":0,"platinum":0,"mithril":0})
    check(not s.snapshot().ready,"initial money waits for a consistent rows/coins sync")
    s.sync([],{}, {},"standard",0,100,1)
    buy.inventory_revision=s.state_revision
    check(s.snapshot().ready,"ordered world-init money confirms empty inventory")
    check(s.inventory_events==0,"money is not counted as an item transaction")
    check(s.execute(buy,c,inter,entities,pos,2),"empty initialized inventory can request purchase")
    check(c.calls.size()==2 and c.calls.back()[0]=="buy","canonical target and buy requests used")
    check(s.items.is_empty() and not s.pending.is_empty(),"purchase creates no local item")
    s.observe("money",{"copper":1,"silver":0,"gold":0,"platinum":0,"mithril":0});s.sync([],{}, {},"standard",1,100,3)
    check(not s.pending.is_empty(),"money update cannot confirm purchase")
    s.observe("inventory");s.sync([{"slot":40,"name":"Free test item","count":1,"model":1}],{}, {},"standard",1,100,4)
    check(s.pending.is_empty() and s.items.has(40),"actual item packet confirms purchase")
    s.reset();s.sync([],{}, {},"standard",0,100,5)
    check(not s.snapshot().ready,"next character waits for its own initialization")
    s.observe("inventory");check(s.snapshot().ready,"an actual empty inventory packet also initializes")
    print(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures}))
    c.free();quit(0 if failures.is_empty() else 1)
