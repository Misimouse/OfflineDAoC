extends RefCounted
## Realm Exchange view and commands; original Server/ItemDb retain the actual goods and money.
const ACTIONS:=["exchange_close","exchange_search","exchange_page","exchange_buy","exchange_list","exchange_take","exchange_price","exchange_claim","exchange_tab","exchange_chest_page","exchange_inspect"]
const SLOTS:=[0,1,5,8,2,7,3,6,9,4,12,13,15,100,101,102,103,104,105,106]
var item_lookup:Callable
var visible:=false
var tab:="browse"
var keeper_id:=""
var generation:=0
var token:=""
var catalog_revision:=0
var catalog_stamp:=""
var market_rows:Array=[]
var listing_rows:Array=[]
var market_page:=0
var market_pages:=0
var market_count:=-1
var listing_page:=0
var proceeds:=-1
var loaded_market:=false
var market_events:=0
var pending:Dictionary={}
var stale:=false
var feedback:=""
var requests:=0
var rejected:=0
var filters:Dictionary={"name":"","slot":0,"armor":0,"damage":0,"level_min":1,"level_max":52,"quality_min":0,"price_max":0,"crafted":0,"bonus1":0,"bonus1_value":0}

func reset()->void:
    visible=false;keeper_id="";token="";generation+=1;market_rows=[];listing_rows=[];loaded_market=false;pending.clear();stale=false;feedback="";catalog_stamp="";catalog_revision+=1

func close(interaction:RefCounted)->void:
    visible=false;keeper_id="";generation+=1;token=""
    # A financial operation already sent still blocks other item moves until its reply/timeout.
    if pending.get("kind","") in ["search","tab"]:pending.clear()
    interaction._close_conversation();interaction.revision+=1

func valid_keeper(interaction:RefCounted,entities:Dictionary,pos:Vector3,alive:bool)->bool:
    var row:Dictionary=entities.get(keeper_id,{})
    return alive and String(row.get("guild","")).nocasecmp_to("Realm Exchange")==0 and keeper_id!="" and keeper_id==interaction.selected_id and keeper_id==interaction.conversation_id and interaction._valid(row) and interaction._distance(row,pos)<=6

func open(which:String,server:Node,interaction:RefCounted,entities:Dictionary,pos:Vector3,alive:bool,now:int)->bool:
    if which not in ["browse","listings"]:return false
    if not pending.is_empty() and pending.get("kind","") not in ["search","tab"]:return fail("Wait for the previous exchange operation to finish.")
    keeper_id=String(interaction.conversation_id)
    if not valid_keeper(interaction,entities,pos,alive):reset();return false
    visible=true;tab=which;generation+=1;token=JSON.stringify([generation,keeper_id,which]).sha256_text();stale=false;pending.clear();feedback="";catalog_stamp=""
    if which=="browse":
        loaded_market=false
        _start("search",now,{"market_events":market_events})
        server.exchange_search(filters,0)
    sync(server,null,now)
    return true

func _lookup(id:String)->Dictionary:
    if not item_lookup.is_valid():return {}
    var value=item_lookup.call(id)
    return value if value is Dictionary else {}

func _row(id:String,index:int,page:int,kind:String,server:Node)->Dictionary:
    var item:Dictionary=_lookup(id)
    if item.is_empty():return {}
    var row:Dictionary={"id":id,"index":index,"name":String(item.get("name","")).left(256),"model":int(item.get("model",0)),"icon":int(item.get("icon",0)),"level":int(item.get("level",0)),"quality":int(item.get("quality",0)),"count":int(item.get("count",1)),"price":int(item.get("price",0)),"can_use":bool(item.get("can_use",true))}
    if kind=="listing":row.price=server.listing_price(index)
    row.token=JSON.stringify([kind,page,index,id,item]).sha256_text()
    return row

func sync(server:Node,inventory:RefCounted,now:int)->void:
    var market:Array=[];var listings:Array=[]
    if loaded_market:
        for id in server.market_items.slice(0,20):
            var place:=String(id).get_slice(":",1).to_int()
            if place<0 or place>19:continue
            var row:=_row(String(id),place,int(server.market_page),"market",server)
            if not row.is_empty():market.append(row)
    if server.container_mode!="account":
        var slots:Array=server.listings.keys();slots.sort()
        for key in slots.slice(0,100):
            var slot:=int(key)
            if slot<150 or slot>249:continue
            var row:=_row(String(server.listings[key]),slot,int(server.listing_page),"listing",server)
            if not row.is_empty():listings.append(row)
    market_page=int(server.market_page);market_pages=clampi(int(server.market_pages),0,255);market_count=int(server.market_count);listing_page=int(server.listing_page);proceeds=int(server.proceeds)
    var stamp:=JSON.stringify([market_page,listing_page,market,listings]).sha256_text()
    if stamp!=catalog_stamp:catalog_stamp=stamp;catalog_revision+=1;market_rows=market;listing_rows=listings
    if not pending.is_empty():
        var kind:=String(pending.kind)
        if kind=="search" and market_events>int(pending.market_events):pending.clear();feedback=""
        elif inventory!=null and kind in ["buy","list","take"] and _move_confirmed(inventory):
            pending.clear();feedback="Inventory updated by the server."
            if kind=="buy" and visible and tab=="browse":
                _start("search",now,{"market_events":market_events});feedback="Purchase confirmed. Refreshing listings..."
                server.exchange_search(filters,market_page)
        if not pending.is_empty() and now>=int(pending.until_ms):
            pending.clear();stale=true;feedback="No confirmation received. Check inventory and reopen the exchange before repeating the operation."

func _move_confirmed(inventory:RefCounted)->bool:
    var kind:=String(pending.kind);var slot:=int(pending.to_slot)
    if kind=="list":
        var row:=_find(listing_rows,slot)
        return (not inventory.items.has(int(pending.from_slot)) or String(inventory.items[int(pending.from_slot)].token)!=String(pending.source_token)) and _matches(row,pending)
    var item:Dictionary=inventory.items.get(slot,{})
    if not _matches(item,pending):return false
    return kind=="buy" or _find(listing_rows,int(pending.from_slot)).is_empty()

func _matches(row:Dictionary,request:Dictionary)->bool:
    return not row.is_empty() and int(row.get("model",-1))==int(request.model) and String(row.get("name",""))==String(request.name)

func observe(kind:String,data:Dictionary)->void:
    if kind in ["you","region_changed","quit"]:reset();return
    if kind=="market":market_events+=1;loaded_market=true
    if kind=="inventory" and int(data.get("window",0)) in [3,4,6]:reset();return
    if kind!="message" or pending.is_empty():return
    var text:=String(data.get("text",""))
    if pending.kind=="price" and (text.begins_with(String(pending.name)+" is listed for ") or text==String(pending.name)+" is stored but not offered for sale."):
        pending.clear();feedback=text
    elif pending.kind=="claim" and ((text.begins_with("You claimed ") and text.contains("Realm Exchange sales")) or text.begins_with("You have no Realm Exchange sale proceeds")):
        pending.clear();feedback=text

func maintain(interaction:RefCounted,entities:Dictionary,pos:Vector3,alive:bool)->void:
    if visible and not valid_keeper(interaction,entities,pos,alive):visible=false;keeper_id="";token="";generation+=1

func fail(why:String)->bool:
    feedback=why;rejected+=1;return false

func _find(rows:Array,index:int)->Dictionary:
    for row in rows:
        if int(row.index)==index:return row
    return {}

func _start(kind:String,now:int,extra:Dictionary={})->void:
    pending=extra.duplicate(true);pending.kind=kind;pending.until_ms=now+12000;requests+=1;feedback="Waiting for the server..."

func _command(server:Node,text:String)->void:
    server.client.call("Target",int(keeper_id.get_slice(":",1)),0xE000)
    server.command("/whisper "+text)

func _filters(value:Dictionary,inventory:RefCounted)->Dictionary:
    var source=value.get("filters",{})
    if not source is Dictionary:return {}
    var result:Dictionary={"name":String(source.get("name","")).strip_edges()}
    if result.name.length()>63 or result.name.contains("\n") or result.name.contains("\r"):return {}
    var limits:Dictionary={"slot":[0,106],"armor":[0,7],"damage":[0,3],"level_min":[1,51],"level_max":[1,52],"quality_min":[0,100],"price_max":[0,2147483647],"crafted":[0,1],"bonus1":[0,5],"bonus1_value":[0,65535]}
    for key in limits:
        var number:int=inventory.input_integer(source,key,int(filters.get(key,0)))
        if number<int(limits[key][0]) or number>int(limits[key][1]):return {}
        result[key]=number
    if int(result.slot) not in SLOTS or int(result.bonus1) not in [0,1,3,4,5] or int(result.level_min)>int(result.level_max):return {}
    if (int(result.bonus1)==1 and int(result.bonus1_value) not in range(1,9)) or (int(result.bonus1)==5 and int(result.bonus1_value) not in range(0,9)):return {}
    return result

func execute(value:Dictionary,server:Node,inventory:RefCounted,interaction:RefCounted,entities:Dictionary,pos:Vector3,alive:bool,now:int)->bool:
    var action:=String(value.get("action",""))
    if action not in ACTIONS:return false
    if action=="exchange_close":
        if not visible:return true
        if String(value.get("exchange_token",""))!=token:return fail("The exchange window has changed.")
        close(interaction);return true
    if not visible or not valid_keeper(interaction,entities,pos,alive):return fail("Open the nearby Realm Exchange broker.")
    if stale:return fail("Reopen the exchange and check its current contents first.")
    if String(value.get("exchange_token",""))!=token:return fail("The exchange window has changed. Open it again.")
    if not pending.is_empty() or not inventory.pending.is_empty():return fail("Wait for the previous operation to finish.")
    if not interaction.dialogs.is_empty():return fail("Answer the pending confirmation first.")
    if action=="exchange_search":
        if tab!="browse":return fail("Open Browse first.")
        var query:=_filters(value,inventory)
        if query.is_empty():return fail("Invalid search filters.")
        filters=query;_start("search",now,{"market_events":market_events});server.exchange_search(filters,0);return true
    if action=="exchange_page":
        var page:int=inventory.input_integer(value,"page")
        if tab!="browse" or page<0 or page>market_pages:return fail("That search page is not available.")
        _start("search",now,{"market_events":market_events});server.exchange_search(filters,page);return true
    if action in ["exchange_tab","exchange_chest_page","exchange_claim"]:
        var word:=""
        if action=="exchange_tab":
            var which:=String(value.get("tab",""))
            if which not in ["browse","listings"]:return fail("Invalid exchange page.")
            word="Browse the exchange" if which=="browse" else "Manage my listings"
        elif action=="exchange_chest_page":
            var step:int=inventory.input_integer(value,"step",0)
            if tab!="listings" or step not in [-1,1]:return fail("Invalid listing page step.")
            word="Next listing page" if step==1 else "Previous listing page"
        else:
            if proceeds<=0:return fail("No sale proceeds are available to claim.")
            word="Claim sale proceeds"
        _start("claim" if action=="exchange_claim" else "tab",now);_command(server,word);return true
    if inventory.inventory_events<=0 or inventory.fingerprint.is_empty():return fail("The server is still sending inventory.")
    if inventory.input_integer(value,"catalog_revision")!=catalog_revision:return fail("The exchange contents have changed. Select again.")
    if action=="exchange_list":
        if tab!="listings" or server.container_mode=="account":return fail("Open your listing chest first.")
        var source:int=inventory.input_integer(value,"slot");var target:int=inventory.input_integer(value,"to_slot",-1)
        if source<40 or source>79 or not inventory.items.has(source):return fail("Select a backpack item.")
        var item:Dictionary=inventory.items[source]
        if String(value.get("item_token",""))!=String(item.token):return fail("The backpack item has changed. Select again.")
        if inventory.input_integer(value,"inventory_revision")!=inventory.state_revision:return fail("The inventory has changed. Select the backpack item again.")
        if target<0:
            for slot in range(150,250):
                if not server.listings.has(slot):target=slot;break
        var count:=int(item.get("count",1))
        if target<150 or target>249 or server.listings.has(target) or count<1 or count>65535:return fail("Choose an empty listing slot.")
        _start("list",now,{"from_slot":source,"to_slot":target,"source_token":item.token,"model":item.model,"name":item.name});server.client.call("MoveItem",source,target,count);return true
    var index:int=inventory.input_integer(value,"index")
    var row:=_find(market_rows if tab=="browse" else listing_rows,index)
    if row.is_empty() or String(value.get("exchange_item_token",""))!=String(row.token):return fail("That exchange item has changed. Select again.")
    if action=="exchange_inspect":server.detail_shown(10 if tab=="browse" else 1,index);requests+=1;return true
    if action=="exchange_price":
        var copper:int=inventory.input_integer(value,"copper")
        if tab!="listings" or server.container_mode=="account" or copper<0 or copper>2147483647:return fail("Enter a valid listing price.")
        _start("price",now,{"name":row.name});server.set_listing_price(index,copper);return true
    if action not in ["exchange_buy","exchange_take"]:return false
    var target:int=inventory.first_free()
    if target<40 or target>79:return fail("Your backpack is full.")
    if action=="exchange_buy":
        if tab!="browse" or not loaded_market or int(row.price)<=0 or int(row.price)>inventory.total_copper():return fail("Check the price and the copper you carry.")
        if not server.exchange_buy(index,target):return fail("The purchase request could not be sent.")
        _start("buy",now,{"to_slot":target,"model":row.model,"name":row.name});return true
    if tab!="listings" or server.container_mode=="account":return fail("Open your listing chest first.")
    var count:=int(row.count)
    if count<1 or count>65535:return fail("Invalid item quantity.")
    _start("take",now,{"from_slot":index,"to_slot":target,"model":row.model,"name":row.name});server.client.call("MoveItem",index,target,count);return true

func inventory_locked()->bool:
    return pending.get("kind","") in ["buy","list","take","claim"]

func snapshot()->Dictionary:
    return {"visible":visible,"tab":tab,"keeper_id":keeper_id,"token":token,"catalog_revision":catalog_revision,"market_rows":market_rows.duplicate(true),"listing_rows":listing_rows.duplicate(true),"market_page":market_page,"market_pages":market_pages,"market_count":market_count,"listing_page":listing_page,"proceeds":proceeds,"filters":filters.duplicate(true),"pending":not pending.is_empty(),"stale":stale,"feedback":feedback,"requests":requests,"rejected":rejected}
