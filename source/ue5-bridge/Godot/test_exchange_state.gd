extends SceneTree
class Wire extends Node:
    var calls:Array=[]
    func Target(oid:int,flags:int)->void:calls.append(["Target",oid,flags])
    func MoveItem(source:int,target:int,count:int)->void:calls.append(["MoveItem",source,target,count])
class FakeServer extends Node:
    var client:Node
    var calls:Array=[]
    var items:Dictionary={}
    var market_items:Array=[]
    var market_page:=0
    var market_pages:=2
    var market_count:=1
    var listings:Dictionary={}
    var listing_page:=0
    var proceeds:=1000
    var container_mode:=""
    var prices:Dictionary={}
    func lookup(id:String)->Dictionary:return items.get(id,{})
    func listing_price(slot:int)->int:return int(prices.get(slot,-1))
    func exchange_search(filters:Dictionary,page:int)->void:calls.append(["Search",filters.duplicate(true),page])
    func exchange_buy(place:int,to:int)->bool:calls.append(["Buy",place,to]);return true
    func set_listing_price(slot:int,copper:int)->void:calls.append(["Price",slot,copper]);prices[slot]=copper
    func command(text:String)->void:calls.append(["Command",text])
    func detail_shown(kind:int,index:int)->void:calls.append(["Detail",kind,index])
var checks:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func command(state:RefCounted,action:String,extra:Dictionary={})->Dictionary:
    var value:Dictionary={"action":action,"exchange_token":state.token,"catalog_revision":state.catalog_revision}
    value.merge(extra,true);return value
func inventory_sync(inv:RefCounted,rows:Array,copper:int=5000)->void:inv.sync(rows,{"copper":copper},{},"standard",0,100,0)
func item(slot:int,name:String,model:int,count:int=1)->Dictionary:return {"slot":slot,"name":name,"model":model,"count":count,"item_type":10,"object_type":2}
func _initialize()->void:run.call_deferred()
func run()->void:
    var folder:String=get_script().resource_path.get_base_dir()
    var state=load(folder.path_join("exchange_state.gd")).new()
    var inv=load(folder.path_join("inventory_state.gd")).new();inv.observe("inventory")
    var interaction=load(folder.path_join("interaction_state.gd")).new();interaction.selected_id="npc:7";interaction.conversation_id="npc:7"
    var entities:={"npc:7":{"kind":"npc","name":"Broker","guild":"Realm Exchange","health":1.0,"targetable":true,"position_m":[0,0,2]}}
    var wire:=Wire.new();root.add_child(wire)
    var server:=FakeServer.new();server.client=wire;root.add_child(server);state.item_lookup=Callable(server,"lookup")
    var backpack:Array=[item(40,"Twig",19,2)];inventory_sync(inv,backpack)
    check(not state.open("browse",server,interaction,entities,Vector3(0,0,20),true,0) and server.calls.is_empty(),"remote broker cannot open a transaction")
    check(not state.open("browse",server,interaction,entities,Vector3.ZERO,false,0),"dead player cannot use exchange")
    entities["npc:7"].guild="Account Vault Keeper"
    check(not state.open("listings",server,interaction,entities,Vector3.ZERO,true,0),"account vault keeper cannot masquerade as exchange")
    entities["npc:7"].guild="Realm Exchange"
    check(state.open("browse",server,interaction,entities,Vector3.ZERO,true,10) and server.calls.size()==1 and server.calls[0][0]=="Search","real browse open requests original search API")
    check(not state.pending.is_empty() and state.market_rows.is_empty(),"old search results remain unavailable before server reply")
    server.items["srvx:5"]={"name":"Bronze Staff","model":445,"icon":1145,"level":5,"quality":99,"count":1,"price":1000}
    server.market_items=["srvx:5"];state.observe("market",{});state.sync(server,inv,20)
    check(state.pending.is_empty() and state.market_rows.size()==1 and state.market_rows[0].index==5,"packet result place survives without assuming sequential array index")
    var row:Dictionary=state.market_rows[0]
    var view:Dictionary=state.snapshot();view.market_rows[0].name="Modified"
    check(state.market_rows[0].name=="Bronze Staff","snapshot copies cannot mutate authoritative view")
    var buy:Dictionary=command(state,"exchange_buy",{"index":5,"exchange_item_token":row.token})
    var before:int=server.calls.size();var bad:Dictionary=buy.duplicate();bad.exchange_token="stale"
    check(not state.execute(bad,server,inv,interaction,entities,Vector3.ZERO,true,30) and server.calls.size()==before,"stale window sends no purchase")
    bad=buy.duplicate();bad.catalog_revision-=1
    check(not state.execute(bad,server,inv,interaction,entities,Vector3.ZERO,true,30),"stale result revision cannot buy")
    bad=buy.duplicate();bad.exchange_item_token="different"
    check(not state.execute(bad,server,inv,interaction,entities,Vector3.ZERO,true,30),"changed item token cannot buy")
    inventory_sync(inv,backpack,999)
    check(not state.execute(buy,server,inv,interaction,entities,Vector3.ZERO,true,30),"insufficient funds block purchase")
    inventory_sync(inv,backpack)
    check(state.execute(buy,server,inv,interaction,entities,Vector3.ZERO,true,40) and server.calls.back()==["Buy",5,41],"purchase uses original result place and actual free backpack slot")
    check(not inv.items.has(41) and inv.total_copper()==5000 and server.market_items==["srvx:5"],"purchase never invents goods or changes money")
    before=server.calls.size()
    check(not state.execute(buy,server,inv,interaction,entities,Vector3.ZERO,true,41) and server.calls.size()==before,"pending purchase cannot be sent twice")
    state.execute(command(state,"exchange_close"),server,inv,interaction,entities,Vector3.ZERO,true,42)
    check(not state.visible and not state.pending.is_empty(),"closing the window preserves the in-flight financial lock")
    interaction.conversation_id="npc:7"
    check(not state.open("listings",server,interaction,entities,Vector3.ZERO,true,43),"reopening cannot clear a pending purchase")
    inventory_sync(inv,backpack+[item(41,"Bronze Staff",445)],4000);state.sync(server,inv,50)
    check(state.pending.is_empty(),"server inventory confirmation completes purchase after window close")
    inventory_sync(inv,backpack)
    check(state.open("listings",server,interaction,entities,Vector3.ZERO,true,60),"owner listing chest opens from its own packet")
    var listing:Dictionary=command(state,"exchange_list",{"slot":40,"to_slot":150,"item_token":inv.items[40].token,"inventory_revision":inv.state_revision})
    bad=listing.duplicate();bad.item_token="old"
    check(not state.execute(bad,server,inv,interaction,entities,Vector3.ZERO,true,70),"backpack identity is checked before listing")
    check(state.execute(listing,server,inv,interaction,entities,Vector3.ZERO,true,71) and wire.calls.back()==["MoveItem",40,150,2],"listing moves the real stack through the original inventory protocol")
    check(inv.items.has(40) and state.listing_rows.is_empty(),"listing does not optimistically remove or create an item")
    server.items["srvc:150"]={"name":"Twig","model":19,"count":2,"price":0};server.listings[150]="srvc:150"
    inventory_sync(inv,[]);state.sync(server,inv,80)
    check(state.pending.is_empty() and state.listing_rows.size()==1,"both chest and backpack confirmation complete a listing")
    row=state.listing_rows[0]
    var price:Dictionary=command(state,"exchange_price",{"index":150,"exchange_item_token":row.token,"copper":2147483648})
    check(not state.execute(price,server,inv,interaction,entities,Vector3.ZERO,true,90),"price overflow is rejected before protocol clamping")
    price.copper=true
    check(not state.execute(price,server,inv,interaction,entities,Vector3.ZERO,true,90),"boolean price is not accepted as currency")
    price.copper=2345
    check(state.execute(price,server,inv,interaction,entities,Vector3.ZERO,true,91) and server.calls.back()==["Price",150,2345],"listing price uses original server API")
    state.observe("message",{"text":"Other item is listed for 23 silver."})
    check(not state.pending.is_empty(),"unrelated price messages cannot acknowledge this request")
    state.observe("message",{"text":"Twig is listed for 23 silver and 45 copper."});state.sync(server,inv,100)
    check(state.pending.is_empty(),"server price confirmation releases transaction lock")
    row=state.listing_rows[0]
    check(state.execute(command(state,"exchange_inspect",{"index":150,"exchange_item_token":row.token}),server,inv,interaction,entities,Vector3.ZERO,true,101) and server.calls.back()==["Detail",1,150],"listing inspection uses actual inventory detail type")
    var take:Dictionary=command(state,"exchange_take",{"index":150,"exchange_item_token":row.token})
    check(state.execute(take,server,inv,interaction,entities,Vector3.ZERO,true,110) and wire.calls.back()==["MoveItem",150,40,2],"taking a listing back moves the real complete stack")
    server.listings.clear();inventory_sync(inv,backpack);state.sync(server,inv,120)
    check(state.pending.is_empty(),"server chest removal and backpack update confirm cancellation")
    server.container_mode="account";state.observe("inventory",{"window":4})
    check(not state.visible and not state.execute(take,server,inv,interaction,entities,Vector3.ZERO,true,121),"account-vault packet invalidates every exchange operation")
    server.container_mode="";interaction.conversation_id="npc:7";state.open("browse",server,interaction,entities,Vector3.ZERO,true,130);state.observe("market",{});state.sync(server,inv,131)
    check(not state.execute(command(state,"exchange_search",{"filters":{"slot":99}}),server,inv,interaction,entities,Vector3.ZERO,true,140),"unsupported search slot is rejected")
    check(not state.execute(command(state,"exchange_search",{"filters":{"bonus1":1,"bonus1_value":0}}),server,inv,interaction,entities,Vector3.ZERO,true,140),"unsupported stat bonus is rejected")
    var query:={"name":"Bronze","quality_min":80,"crafted":1,"price_max":10000}
    check(state.execute(command(state,"exchange_search",{"filters":query}),server,inv,interaction,entities,Vector3.ZERO,true,141) and server.calls.back()[1].quality_min==80,"valid search preserves original filter semantics")
    state.observe("market",{});state.sync(server,inv,150)
    check(state.execute(command(state,"exchange_page",{"page":1}),server,inv,interaction,entities,Vector3.ZERO,true,151) and server.calls.back()[2]==1,"search page uses bounded original API")
    server.market_page=1;state.observe("market",{});state.sync(server,inv,160)
    bad=command(state,"exchange_close");bad.exchange_token="old-window"
    check(not state.execute(bad,server,inv,interaction,entities,Vector3.ZERO,true,161) and state.visible,"stale close cannot dismiss a new conversation")
    state.execute(command(state,"exchange_search",{"filters":query}),server,inv,interaction,entities,Vector3.ZERO,true,170);state.sync(server,inv,12171)
    check(state.stale and state.pending.is_empty(),"missing server reply marks the window stale")
    check(not state.execute(command(state,"exchange_buy",{"index":5,"exchange_item_token":state.market_rows[0].token}),server,inv,interaction,entities,Vector3.ZERO,true,12172),"timed-out contents cannot be bought without reopening")
    state.reset();interaction.conversation_id="npc:7";state.open("listings",server,interaction,entities,Vector3.ZERO,true,13000)
    check(state.execute(command(state,"exchange_claim"),server,inv,interaction,entities,Vector3.ZERO,true,13001) and wire.calls.back()==["Target",7,0xE000] and server.calls.back()==["Command","/whisper Claim sale proceeds"],"claim uses the original nearby broker command")
    check(state.proceeds==1000 and inv.total_copper()==5000,"claim never credits player money optimistically")
    state.observe("message",{"text":"You claimed 10 silver from your Realm Exchange sales."});server.proceeds=0;state.sync(server,inv,13010)
    check(state.pending.is_empty() and state.proceeds==0,"claim is reflected only after original server confirmation")
    check(not state.execute(command(state,"exchange_claim"),server,inv,interaction,entities,Vector3.ZERO,true,13011),"no duplicate zero-proceeds claim")
    interaction.selected_id="npc:8";state.maintain(interaction,entities,Vector3.ZERO,true)
    check(not state.visible,"switching target closes the broker view")
    state.reset();interaction.selected_id="npc:7";interaction.conversation_id="npc:7";state.open("browse",server,interaction,entities,Vector3.ZERO,true,14000);state.observe("market",{});state.sync(server,inv,14001)
    row=state.market_rows[0]
    check(state.execute(command(state,"exchange_buy",{"index":5,"exchange_item_token":row.token}),server,inv,interaction,entities,Vector3.ZERO,true,14002),"visible purchase can start with current server results")
    inventory_sync(inv,backpack+[item(41,"Bronze Staff",445)],4000);state.sync(server,inv,14003)
    check(state.pending.get("kind","")=="search" and server.calls.back()[0]=="Search","confirmed purchase refreshes results before allowing another purchase")
    server.market_items=[];state.observe("market",{});state.sync(server,inv,14004)
    check(state.pending.is_empty() and state.market_rows.is_empty(),"sold item disappears only when the refreshed server page arrives")
    var out:String=ProjectSettings.globalize_path(folder.path_join("../Reports/exchange")).simplify_path();DirAccess.make_dir_recursive_absolute(out)
    var file:=FileAccess.open(out.path_join("godot_tests.json"),FileAccess.WRITE);file.store_string(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures},"  "));file.close();print(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures}));server.free();wire.free();quit(0 if failures.is_empty() else 1)
