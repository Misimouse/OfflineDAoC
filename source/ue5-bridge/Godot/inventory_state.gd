extends RefCounted
## A view of server inventory. Commands never change items or coins optimistically.
const EQUIPMENT:=[10,11,12,13,21,22,23,24,25,26,27,28,29,32,33,34,35,36,37]
var purchase_filter:Callable
var items:Dictionary={}
var vault:Dictionary={}
var money:Dictionary={}
var gear:Dictionary={}
var weapon_set:="standard"
var weight_now:=-1
var weight_max:=-1
var revision:=0
var state_revision:=0
var fingerprint:=""
var feedback:=""
var pending:Dictionary={}
var requests:=0
var rejected:=0
var inventory_events:=0

func reset()->void:
    items.clear();vault.clear();money.clear();gear.clear();pending.clear();fingerprint="";feedback="";weapon_set="standard";weight_now=-1;weight_max=-1;state_revision+=1;revision+=1;inventory_events=0

func observe(kind:String,data:Dictionary={})->void:
    if kind=="inventory":
        if inventory_events==0:revision+=1
        inventory_events+=1
    elif kind=="message" and bool(pending.get("equipment_request",false)):
        var text:=String(data.get("text",""))
        # These exact original server replies reject the outstanding equipment move.
        # Keep items/coins/tokens authoritative; only finish the rejected request.
        if text in ["You have no skill in wearing this armor type!","You have no skill in using this weapon type!","You cannot equip an item from another realm!","Your class cannot use this item!"]:
            pending.clear();feedback=text;rejected+=1;revision+=1

func sync(rows:Array,coins:Dictionary,appearance:Dictionary,weapons:String,carried:int,capacity:int,now:int,vault_state:Dictionary={})->void:
    vault=vault_state.duplicate(true)
    var next:Dictionary={}
    for row in rows:
        var slot:=int(row.get("slot",-1))
        if not allowed_slots().has(slot):continue
        var it:Dictionary=row.duplicate(true)
        it["token"]=JSON.stringify(row).sha256_text();next[slot]=it
    var ordered:Array=[]
    for slot in allowed_slots():
        if next.has(slot):ordered.append(next[slot])
    var normalized:Dictionary={}
    for key in ["mithril","platinum","gold","silver","copper"]:normalized[key]=maxi(0,int(coins.get(key,0)))
    var key:=JSON.stringify([ordered,normalized,appearance,weapons,carried,capacity,vault]).sha256_text()
    if key!=fingerprint:
        items=next;money=normalized;gear=appearance.duplicate(true);weapon_set=weapons;weight_now=carried;weight_max=capacity;fingerprint=key;state_revision+=1;revision+=1
        if not pending.is_empty() and inventory_events>int(pending.inventory_events):
            pending.clear();feedback="Inventory updated by the server.";revision+=1
    # NPC services also return an unchanged slot when refusing an item or opening
    # a confirmation. This is a refresh, not proof that the NPC accepted it.
    if pending.get("action","")=="inventory_give" and inventory_events>int(pending.inventory_events):
        pending.clear();feedback="Inventory refreshed. Check the NPC's response.";revision+=1
    if bool(pending.get("item_application",false)) and inventory_events>int(pending.inventory_events):
        pending.clear();feedback="Inventory refreshed. Check the server's response.";revision+=1
    if not pending.is_empty() and now>=int(pending.until_ms):
        pending.clear();feedback="No confirmation received. Check inventory before repeating the operation.";revision+=1

func allowed_slots()->Array:
    var slots:Array=EQUIPMENT+range(40,80)
    if bool(vault.get("valid",false)) and [int(vault.get("first",0)),int(vault.get("count",0))] in [[110,40],[150,100]]:slots.append_array(range(int(vault.first),int(vault.first)+int(vault.count)))
    return slots
func vault_slot(slot:int)->bool:return bool(vault.get("valid",false)) and slot>=int(vault.get("first",0)) and slot<int(vault.get("first",0))+int(vault.get("count",0))
func poison_application(source:int,destination:int)->bool:
    if source<40 or source>79 or not items.has(source) or not items.has(destination) or int(items[source].get("object_type",0))!=46:return false
    var object_type:=int(items[destination].get("object_type",0))
    # Original GlobalConstants.IsWeapon includes shields. DOL decides whether
    # this character can poison that weapon; the bridge never grants a coating.
    return (object_type>=1 and object_type<=28) or object_type==42
func first_free()->int:
    for slot in range(40,80):
        if not items.has(slot):return slot
    return -1

func slots_for(it:Dictionary)->Array:
    var t:=int(it.get("item_type",0))
    match t:
        10:return [10]
        11:return [11] if int(it.get("object_type",0))==42 else [10,11]
        12,13,21,22,23,24,25,26,27,28,29,32,37:return [t]
        33,34:return [33,34]
        35,36:return [35,36]
    return []

func total_copper()->int:
    return int(money.get("copper",0))+100*int(money.get("silver",0))+10000*int(money.get("gold",0))+10000000*int(money.get("platinum",0))+10000000000*int(money.get("mithril",0))

func fail(text:String)->bool:
    feedback=text;rejected+=1;revision+=1;return false

func input_integer(value:Dictionary,key:String,fallback:int=-1)->int:
    var n=value.get(key,fallback)
    if not (n is int or n is float) or not is_finite(float(n)) or float(n)!=floor(float(n)) or absf(float(n))>9007199254740991.0:return -2147483648
    return int(n)

func execute(value:Dictionary,client:Node,interaction:RefCounted,entities:Dictionary,pos:Vector3,now:int)->bool:
    var action:=String(value.get("action",""))
    if action not in ["inventory_move","inventory_equip","inventory_unequip","inventory_give","merchant_buy","merchant_sell"]:return false
    if inventory_events==0 or fingerprint.is_empty():return fail("The server is still sending inventory.")
    if not pending.is_empty():return fail("Wait for the server's response to the previous operation.")
    if input_integer(value,"inventory_revision")!=state_revision:return fail("The inventory has changed. Select the item again.")
    if not interaction.dialogs.is_empty():return fail("Answer the pending confirmation first.")
    var source:=input_integer(value,"slot");var destination:=-1;var count:=1;var applying_poison:=false
    if action!="merchant_buy":
        if not items.has(source) or String(value.get("item_token",""))!=String(items[source].token):return fail("That item is no longer in this slot.")
        count=int(items[source].get("count",1))
        if count<1 or count>65535:return fail("Invalid item quantity.")
    if action=="inventory_give":
        if source not in EQUIPMENT and (source<40 or source>79):return fail("Select a carried item.")
        var id:=String(value.get("entity_id",""))
        var part:=id.trim_prefix("npc:")
        if not id.begins_with("npc:") or not part.is_valid_int():return fail("Drop the item onto a nearby NPC.")
        var oid:=int(part)
        if oid<1 or oid>64535 or id!="npc:%d"%oid:return fail("That NPC is no longer available.")
        var row:Dictionary=entities.get(id,{})
        if row.get("kind","")!="npc" or not interaction._valid(row):return fail("That NPC is no longer available.")
        if input_integer(value,"target_model")<0 or int(row.get("model_id",-1))<0 or not value.get("target_name") is String or value.target_name!=String(row.get("name","")) or input_integer(value,"target_model")!=int(row.get("model_id",-1)):return fail("The NPC has changed. Select it again.")
        var distance:float=interaction._distance(row,pos)
        if not is_finite(distance) or distance>3.2001:return fail("Move closer to hand the item to that NPC.")
        if client==null:return fail("The server connection is unavailable.")
        # Original PlayerMoveItem: object ID + 1000. DOL alone decides whether a
        # service accepts backpack/equipped items, asks confirmation or charges.
        client.call("MoveItem",source,1000+oid,count)
    elif action in ["inventory_move","inventory_equip","inventory_unequip"]:
        if action=="inventory_move":destination=input_integer(value,"to_slot")
        elif action=="inventory_equip":
            if source<40 or source>79:return fail("Select a backpack item.")
            var fits:=slots_for(items[source])
            if fits.is_empty():return fail("That item cannot be equipped.")
            destination=int(fits[0])
            for slot in fits:
                if not items.has(slot):destination=slot;break
        else:
            if source not in EQUIPMENT:return fail("Select an equipped item.")
            destination=first_free()
            if destination<0:return fail("Your backpack is full.")
        if destination==source or not allowed_slots().has(destination):return fail("Invalid destination slot.")
        if value.has("count"):
            var selected_count:=input_integer(value,"count")
            if action!="inventory_move" or selected_count<1 or selected_count>count:return fail("Invalid item quantity.")
            if selected_count<count:
                # Split only into an empty storage slot. Never turn a quantity
                # choice into equipment, poison application or a guessed merge.
                if (source<40 or (source>79 and not vault_slot(source))) or (destination<40 or (destination>79 and not vault_slot(destination))) or items.has(destination):return fail("Choose an empty backpack or vault slot to split a stack.")
            count=selected_count
        if source>=110 or destination>=110:
            if action!="inventory_move" or String(value.get("vault_token",""))!=String(vault.get("token","")) or not bool(vault.get("valid",false)):return fail("The vault has changed or is closed.")
            if (not vault_slot(source) and (source<40 or source>79)) or (not vault_slot(destination) and (destination<40 or destination>79)):return fail("Move the item between backpack and vault.")
        applying_poison=action=="inventory_move" and poison_application(source,destination)
        if destination in EQUIPMENT and destination not in slots_for(items[source]) and not (applying_poison and destination in [10,11,12,13]):return fail("That item does not match this equipment slot.")
        if source in EQUIPMENT and items.has(destination) and source not in slots_for(items[destination]):return fail("The destination item cannot occupy this equipment slot.")
        client.call("MoveItem",source,destination,count)
    else:
        var merchant:Dictionary=interaction.merchant
        var id:=String(merchant.get("entity_id",""))
        var row:Dictionary=entities.get(id,{})
        if merchant.is_empty() or id!=interaction.selected_id or id!=interaction.conversation_id or not interaction._valid(row) or interaction._distance(row,pos)>6:return fail("Open the nearby merchant's catalogue.")
        if int(merchant.get("window",-1))!=0:return fail("This service needs its own window.")
        if String(value.get("merchant_id",""))!=id or input_integer(value,"merchant_revision")!=int(merchant.get("catalog_revision",-2)):return fail("The catalogue has changed. Select the item again.")
        var x:=int(pos.x*40+35*8192);var y:=int(pos.z*40+51*8192)
        if action=="merchant_buy":
            var page:=input_integer(value,"page");var index:=input_integer(value,"index");var offered:Dictionary={}
            for it in merchant.get("pages",{}).get(str(page),[]):
                if int(it.index)==index:offered=it;break
            if page<0 or page>9 or index<0 or index>29 or offered.is_empty():return fail("That item is not in the current catalogue.")
            if input_integer(value,"count",1)!=1:return fail("Buy one pack at a time.")
            if int(offered.get("price",-1))<0 or total_copper()<int(offered.price):return fail("You do not have enough money.")
            if first_free()<0:return fail("Free a backpack slot before buying.")
            if purchase_filter.is_valid():
                var gate:Dictionary=purchase_filter.call(row,page,offered)
                if gate.get("managed",false) and not gate.get("available",false):return fail(String(gate.get("reason","This destination is not available in the loaded world yet.")))
            client.call("Target",int(id.get_slice(":",1)),0xE000)
            client.call("BuyItem",x,y,page*30+index,1,0)
        else:
            if source<40 or source>79:return fail("You can only sell backpack items.")
            client.call("Target",int(id.get_slice(":",1)),0xE000)
            client.call("SellItem",x,y,source)
    requests+=1;feedback="Waiting for the server update...";pending={"action":action,"until_ms":now+12000,"inventory_events":inventory_events,"equipment_request":action in ["inventory_equip","inventory_move"] and destination in EQUIPMENT and not applying_poison,"item_application":applying_poison};revision+=1;return true

func snapshot()->Dictionary:
    var rows:Array=[]
    for slot in allowed_slots():
        if items.has(slot):rows.append(items[slot])
    return {"revision":revision,"state_revision":state_revision,"ready":inventory_events>0 and not fingerprint.is_empty(),"items":rows,"vault":vault.duplicate(true),"money":money,"gear":gear,"weapon_set":weapon_set,"weight_now":weight_now,"weight_max":weight_max,"pending":not pending.is_empty(),"feedback":feedback}
