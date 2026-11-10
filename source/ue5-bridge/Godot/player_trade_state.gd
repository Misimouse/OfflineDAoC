extends RefCounted
## Inactive player-trade adapter. Only authoritative windows describe an offer.
## A close packet never implies completion; inventory and money remain server-owned.
var visible := false
var partner_id := ""
var partner_session := -1
var generation := 0
var token := ""
var offer: Dictionary = {}
var pending := false
var pending_action := ""
var cancel_required := false
var feedback := ""

func reset(needs_cancel: bool = false) -> void:
    generation += 1
    visible = false
    partner_id = ""
    partner_session = -1
    token = ""
    offer.clear()
    pending = false
    pending_action = ""
    cancel_required = needs_cancel
    feedback = ""

func _near(row: Dictionary, pos: Vector3) -> bool:
    var p: Array = row.get("position_m", [])
    if p.size() != 3 or row.get("kind", "") != "player" or int(row.get("session_id", 0)) <= 0 or row.get("state", "") == "dead": return false
    var point := Vector3(float(p[0]), float(p[1]), float(p[2]))
    return point.is_finite() and pos.is_finite() and pos.distance_to(point) <= 6.0

func _partner(title: String, entities: Dictionary, pos: Vector3) -> String:
    const PREFIX := "Trading with "
    if not title.begins_with(PREFIX): return ""
    var name := title.substr(PREFIX.length())
    if name.is_empty(): return ""
    var found := ""
    for key in entities:
        var row: Dictionary = entities[key]
        if String(row.get("name", "")) == name:
            # Ambiguous names, including a distant duplicate, cannot authorize a trade.
            if not found.is_empty() or not _near(row, pos): return ""
            found = String(key)
    return found

func observe(kind: String, data: Dictionary, entities: Dictionary, pos: Vector3, alive: bool) -> void:
    if kind in ["you", "region_changed", "quit", "disconnect"]:
        reset()
        return
    if kind != "player_trade": return
    if not bool(data.get("open", false)):
        reset()
        cancel_required = false
        return
    var id := _partner(String(data.get("title", "")), entities, pos)
    if not alive or id.is_empty():
        reset(true)
        return
    var session := int(entities[id].get("session_id", -1))
    if visible and (id != partner_id or session != partner_session):
        reset(true)
        return
    # Each packet revokes every prior action token, including identical-looking offers.
    generation += 1
    visible = true
    partner_id = id
    partner_session = session
    offer = data.duplicate(true)
    token = JSON.stringify([generation, id, session, offer]).sha256_text()
    pending = false
    pending_action = ""
    feedback = ""

func maintain(entities: Dictionary, pos: Vector3, alive: bool) -> void:
    if visible and (not alive or not entities.has(partner_id) or not _near(entities[partner_id], pos) or int(entities[partner_id].get("session_id", -1)) != partner_session):
        reset(true)

func request(value: Dictionary, client: Object, entities: Dictionary, pos: Vector3, alive: bool) -> bool:
    maintain(entities, pos, alive)
    if not visible or cancel_required or String(value.get("trade_token", "")) != token: return false
    var action := String(value.get("action", ""))
    if pending and (action != "player_trade_cancel" or pending_action == "cancel"): return false
    if action not in ["player_trade_accept", "player_trade_cancel"]: return false
    if not bool(client.call("PlayerTrade", 2 if action == "player_trade_accept" else 0, PackedInt32Array(), PackedInt32Array())): return false
    pending = true
    pending_action = "cancel" if action == "player_trade_cancel" else "accept"
    feedback = "Waiting for the server..."
    # Never mark accepted/completed or transfer goods in response to a local click.
    return true

func update_offer(value: Dictionary, client: Object, inventory: RefCounted, entities: Dictionary, pos: Vector3, alive: bool) -> bool:
    maintain(entities, pos, alive)
    if not visible or pending or cancel_required or String(value.get("trade_token", "")) != token: return false
    if not inventory.snapshot().get("ready", false) or not inventory.pending.is_empty() or inventory.input_integer(value, "inventory_revision") != inventory.state_revision: return false
    var slots = value.get("slots", null)
    var money = value.get("money", null)
    var identities = value.get("item_tokens", null)
    if not slots is Array or slots.size() > 10 or not money is Array or money.size() != 5 or not identities is Dictionary: return false
    var outgoing := PackedInt32Array()
    var seen: Array = []
    for raw in slots:
        var slot: int = inventory.input_integer({"slot":raw}, "slot")
        if slot == 0: outgoing.append(0); continue
        if slot < 40 or slot > 79 or slot in seen or not inventory.items.has(slot): return false
        if String(identities.get(str(slot), "")) != String(inventory.items[slot].get("token", "")) or String(identities.get(str(slot), "")).is_empty(): return false
        seen.append(slot);outgoing.append(slot)
    var coins := PackedInt32Array()
    for raw in money:
        var coin: int = inventory.input_integer({"coin":raw}, "coin")
        if coin < 0 or coin > 65535: return false
        coins.append(coin)
    if not bool(client.call("PlayerTrade", 1, outgoing, coins)): return false
    pending = true
    pending_action = "update"
    feedback = "Waiting for the server..."
    return true

func take_cancel() -> bool:
    var result := cancel_required
    cancel_required = false
    return result

func snapshot() -> Dictionary:
    return {"visible": visible, "partner_id": partner_id, "partner_session": partner_session, "token": token, "offer": offer.duplicate(true), "pending": pending, "feedback": feedback}
