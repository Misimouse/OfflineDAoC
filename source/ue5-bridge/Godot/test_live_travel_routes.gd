extends SceneTree
var checks:=0
class Client:
    extends Node
    var calls:Array=[]
    func Target(oid:int,flags:int)->void:calls.append(["target",oid,flags])
    func BuyItem(x:int,y:int,slot:int,count:int,mode:int)->void:calls.append(["buy",x,y,slot,count,mode])
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:push_error(label);quit(1);assert(false,label)
func _initialize()->void:
    var module:Script=load("res://live_travel_routes.gd")
    check(module!=null and module.can_instantiate(),"route module parses")
    var gate:RefCounted=module.new()
    var data:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://travel_routes.json"))
    check(gate.configure(data),"public reference definitions load")
    var available:=0
    for row in data.routes:
        var stable:={"name":row.stable,"position_m":row.stable_position_m,"model_id":row.stable_model}
        var item:Dictionary={}
        for key in ["name","model","price","object_type","index"]:item[key]=row[key]
        var result:Dictionary=gate.decision(stable,row.page,item)
        check(result.managed and result.available==row.available,"each original route has its explicit coverage decision")
        if row.available:
            available+=1
            for key in ["name","model","price","object_type","index"]:
                var changed:=item.duplicate(true)
                changed[key]="Changed ticket" if key=="name" else int(changed[key])+1
                check(not gate.decision(stable,row.page,changed).available,"changed route identity cannot buy: "+key)
            var moved:=stable.duplicate(true);moved.position_m[0]+=10
            check(not gate.decision(moved,row.page,item).available,"same name in another location is not a verified stable")
            var changed:=stable.duplicate(true);changed.model_id+=1
            check(not gate.decision(changed,row.page,item).available,"stable model mismatch rejected")
            check(not gate.decision(stable,9,item).available,"another merchant page rejected")
            var shop:={"merchant":{"entity_id":"npc:5","pages":{str(row.page):[item]}}}
            var annotated:Dictionary=gate.annotate(shop,{"npc:5":stable})
            check(annotated.merchant.pages[str(row.page)][0].travel_available,"original merchant UI receives availability")
            check(not shop.merchant.pages[str(row.page)][0].has("travel_available"),"annotation never mutates original server catalogue")
    check(available==1,"only completed in-bounds itinerary enabled")
    var unknown:={"name":"Other Merchant","position_m":[0,0,0],"model_id":1}
    check(not gate.decision(unknown,0,{"model":499,"object_type":0}).available,"unknown route ticket unavailable")
    check(gate.decision(unknown,0,{"model":500,"object_type":2}).available,"ordinary merchants unaffected")
    var inventory:RefCounted=load("res://inventory_state.gd").new()
    var inter:RefCounted=load("res://interaction_state.gd").new();var client:=Client.new()
    inventory.purchase_filter=gate.decision;inventory.sync([],{"gold":5},{},"standard",0,100,0);inventory.observe("inventory")
    var blocked:Dictionary={};var supported:Dictionary={}
    for row in data.routes:
        if row.stable=="Carsten":
            if row.available:supported=row
            else:blocked=row
    var stable:={"id":"npc:5","kind":"npc","health":1,"name":supported.stable,"position_m":supported.stable_position_m,"model_id":supported.stable_model}
    var items:=[blocked.duplicate(true),supported.duplicate(true)]
    inter.selected_id="npc:5";inter.conversation_id="npc:5";inter.merchant={"entity_id":"npc:5","catalog_revision":7,"window":0,"pages":{str(int(supported.page)):items}}
    var command:={"action":"merchant_buy","merchant_id":"npc:5","merchant_revision":7,"inventory_revision":inventory.state_revision,"page":blocked.page,"index":blocked.index,"count":1}
    var pos:=Vector3(supported.stable_position_m[0],supported.stable_position_m[1],supported.stable_position_m[2])
    check(not inventory.execute(command,client,inter,{"npc:5":stable},pos,1),"unsupported purchase rejected through real inventory controller")
    check(client.calls.is_empty() and inventory.requests==0,"rejected route sends neither Target nor BuyItem packet")
    check(inventory.pending.is_empty() and inventory.money.gold==5,"rejected route never changes money or pending purchase")
    check(inventory.feedback==gate.UNAVAILABLE,"unavailable destination explains itself in original shop feedback: "+inventory.feedback)
    command.index=supported.index;command.page=supported.page
    check(inventory.execute(command,client,inter,{"npc:5":stable},pos,2),"supported route reaches original inventory BuyItem path: "+inventory.feedback)
    check(client.calls.size()==2 and client.calls[1][0]=="buy" and client.calls[1][3]==supported.page*30+supported.index,"original merchant slot and one packet retained")
    client.free()
    check(not gate.configure({}),"malformed catalogue cannot enable travel")
    check(not gate.decision(unknown,0,{"model":499,"object_type":0}).available,"missing catalogue cannot enable ticket purchase")
    print(JSON.stringify({"passed":true,"checks":checks,"server_started":false}));quit(0)
