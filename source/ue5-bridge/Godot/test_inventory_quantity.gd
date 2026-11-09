extends SceneTree
class Client extends Node:
    var calls:Array=[]
    func MoveItem(a:int,b:int,count:int)->void:calls.append([a,b,count])
var checks:=0
var failures:Array=[]
var folder:String
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func fresh(storage:Dictionary={}):
    var inv=load(folder.path_join("inventory_state.gd")).new()
    inv.observe("inventory")
    inv.sync([{ "slot":40,"name":"Stack","count":10,"item_type":0,"object_type":46 },{"slot":42,"name":"Occupied","count":2},{"slot":10,"name":"Sword","count":1,"item_type":10,"object_type":1},{"slot":110,"name":"Stored","count":10}],{}, {},"standard",1,20,100,storage)
    return inv
func command(inv,source:int=40,dest:int=41)->Dictionary:
    return {"action":"inventory_move","slot":source,"to_slot":dest,"item_token":inv.items[source].token,"inventory_revision":inv.state_revision,"vault_token":inv.vault.get("token","")}
func _initialize()->void:run.call_deferred()
func run()->void:
    folder=get_script().resource_path.get_base_dir()
    var client:=Client.new()
    var interaction=load(folder.path_join("interaction_state.gd")).new()
    var inv=fresh();var cmd:=command(inv);cmd.count=3
    var before:Dictionary=inv.items.duplicate(true)
    check(inv.execute(cmd,client,interaction,{},Vector3.ZERO,110) and client.calls.back()==[40,41,3],"partial quantity uses original MoveItem count")
    check(inv.items==before and not inv.items.has(41),"no predicted split or local count change")
    var sent:=client.calls.size()
    check(not inv.execute(cmd,client,interaction,{},Vector3.ZERO,111) and client.calls.size()==sent,"pending operation cannot duplicate a split")
    for amount in [0,-1,11,65536,1.5,"3",true,NAN,INF]:
        inv=fresh();cmd=command(inv);cmd.count=amount;sent=client.calls.size()
        check(not inv.execute(cmd,client,interaction,{},Vector3.ZERO,120) and client.calls.size()==sent,"reject invalid quantity %s"%str(amount))
    for dest in [10,42]:
        inv=fresh();cmd=command(inv,40,dest);cmd.count=3;sent=client.calls.size()
        check(not inv.execute(cmd,client,interaction,{},Vector3.ZERO,120) and client.calls.size()==sent,"partial count cannot poison, equip or merge into slot %d"%dest)
    inv=fresh();cmd=command(inv);cmd.item_token="stale";cmd.count=3
    check(not inv.execute(cmd,client,interaction,{},Vector3.ZERO,120),"stale item token rejected")
    inv=fresh();cmd=command(inv);cmd.inventory_revision-=1;cmd.count=3
    check(not inv.execute(cmd,client,interaction,{},Vector3.ZERO,120),"stale inventory revision rejected")
    inv=fresh();cmd=command(inv)
    check(inv.execute(cmd,client,interaction,{},Vector3.ZERO,120) and client.calls.back()==[40,41,10],"ordinary drag still moves whole stack")
    inv=fresh();cmd=command(inv);cmd.count=10
    check(inv.execute(cmd,client,interaction,{},Vector3.ZERO,120) and client.calls.back()==[40,41,10],"explicit full quantity remains supported")
    var storage:={"valid":true,"first":110,"count":40,"token":"current-vault"}
    for slots in [[40,111],[110,41],[110,111]]:
        inv=fresh(storage);cmd=command(inv,slots[0],slots[1]);cmd.count=4
        check(inv.execute(cmd,client,interaction,{},Vector3.ZERO,120) and client.calls.back()==[slots[0],slots[1],4],"partial quantity supports current vault %s"%str(slots))
    inv=fresh(storage);cmd=command(inv,110,41);cmd.count=4;cmd.vault_token="old-vault"
    check(not inv.execute(cmd,client,interaction,{},Vector3.ZERO,120),"reopened vault invalidates pending choice")
    inv=fresh();cmd=command(inv,40,111);cmd.count=4
    check(not inv.execute(cmd,client,interaction,{},Vector3.ZERO,120),"closed vault cannot receive a split")
    inv=fresh();cmd=command(inv);cmd.count=3;interaction.dialogs=[{"id":"confirmation"}]
    check(not inv.execute(cmd,client,interaction,{},Vector3.ZERO,120),"pending server confirmation blocks split")
    var report:={"passed":failures.is_empty(),"checks":checks,"failures":failures,"real_server":false}
    print(JSON.stringify(report));client.free();quit(0 if failures.is_empty() else 1)
