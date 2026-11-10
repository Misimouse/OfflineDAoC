extends RefCounted
## Candidate coordinator for original MoveItem opening, trade state and item icons.
var state = load(get_script().resource_path.get_base_dir().path_join("player_trade_state.gd")).new()
var opening: Dictionary = {}
var generation := 0
var feedback := ""

func blocks_inventory() -> bool:
    return state.visible or not opening.is_empty()

func reject(message: String) -> bool:
    feedback=message
    return false

func begin(value: Dictionary, client: Object, inventory: RefCounted, entities: Dictionary, pos: Vector3, alive: bool, now: int) -> bool:
    maintain(entities, pos, alive, now)
    if not alive or state.cancel_required or blocks_inventory() or not inventory.pending.is_empty() or not inventory.snapshot().get("ready", false): return reject("Finish the current trade or inventory operation first.")
    if inventory.input_integer(value,"inventory_revision") != inventory.state_revision: return reject("Inventory changed. Try again.")
    var slot: int = inventory.input_integer(value,"slot")
    if slot < 40 or slot > 79 or not inventory.items.has(slot): return reject("Select a carried backpack item.")
    var item: Dictionary = inventory.items[slot]
    var item_token := String(value.get("item_token",""))
    if item_token.is_empty() or item_token != String(item.get("token","")): return reject("The inventory item has changed. Try again.")
    var id := String(value.get("entity_id",""))
    var oid := id.get_slice(":",1).to_int()
    if oid <= 0 or oid > 64535 or id != "player:"+str(oid) or not entities.has(id): return reject("Select another nearby player.")
    var row: Dictionary = entities[id]
    if not state._near(row,pos) or inventory.input_integer(value,"target_session") != int(row.get("session_id",0)): return reject("The player is no longer available nearby.")
    if String(value.get("target_name","")) != String(row.get("name","")) or inventory.input_integer(value,"target_model") != int(row.get("model_id",-1)): return reject("The player has changed. Try again.")
    if not client.has_method("MoveItem") or not client.has_method("PlayerTrade"): return reject("Player trade is unavailable.")
    generation += 1
    opening={"id":id,"session":int(row.session_id),"until_ms":now+12000,"token":JSON.stringify([generation,id,row.session_id,item_token]).sha256_text()}
    feedback="Waiting for the server..."
    # DOL receives the actual complete inventory item for a player destination.
    client.call("MoveItem",slot,oid+1000,1)
    return true

func observe(kind: String, data: Dictionary, entities: Dictionary, pos: Vector3, alive: bool) -> void:
    if kind in ["you","region_changed","quit","disconnect"]:
        opening.clear();feedback=""
    if kind=="player_trade" and bool(data.get("open",false)) and not opening.is_empty():
        var id: String=state._partner(String(data.get("title","")),entities,pos)
        if id != String(opening.id) or not entities.has(id) or int(entities[id].get("session_id",0)) != int(opening.session):
            opening.clear();state.reset(true);return
    state.observe(kind,data,entities,pos,alive)
    if kind=="player_trade":opening.clear();feedback=""
    elif kind=="inventory" and not opening.is_empty():
        # Original MoveItem refresh follows its trade window or refusal. No window
        # means no accepted offer; clear any hidden server-side trade allocation.
        opening.clear();state.reset(true);feedback="Inventory refreshed. Check the server's response."

func maintain(entities: Dictionary, pos: Vector3, alive: bool, now: int) -> void:
    state.maintain(entities,pos,alive)
    if opening.is_empty(): return
    var row: Dictionary=entities.get(String(opening.id),{})
    if not alive or not state._near(row,pos) or int(row.get("session_id",0)) != int(opening.session) or now >= int(opening.until_ms):
        opening.clear();state.reset(true);feedback="No trade window received. Check the server's response."

func flush_cancel(client: Object) -> void:
    if state.take_cancel() and client.has_method("PlayerTrade"):
        client.call("PlayerTrade",0,PackedInt32Array(),PackedInt32Array())

func request(value: Dictionary, client: Object, inventory: RefCounted, entities: Dictionary, pos: Vector3, alive: bool, now: int) -> bool:
    maintain(entities,pos,alive,now)
    match String(value.get("action","")):
        "player_trade_begin":return begin(value,client,inventory,entities,pos,alive,now)
        "player_trade_update":return state.update_offer(value,client,inventory,entities,pos,alive)
        "player_trade_accept", "player_trade_cancel":return state.request(value,client,entities,pos,alive)
    return false

func snapshot(icon_for_model: Callable=Callable()) -> Dictionary:
    var value: Dictionary=state.snapshot()
    if not opening.is_empty():value["opening"]=true
    if not feedback.is_empty():value["feedback"]=feedback
    var offer: Dictionary=value.get("offer",{})
    for item in offer.get("partner_items",[]):
        if icon_for_model.is_valid():item["icon"]=int(icon_for_model.call(int(item.get("model",0))))
    return value
