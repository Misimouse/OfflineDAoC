extends Node
## A local data transport. Does not load graphics, connect to DAoC, or move a character.
signal command_received(command: Dictionary)
const VERSION := 1
const MAX_FRAME := 1048576
const MAX_ENTITIES := 2048
var listener := TCPServer.new()
var peer: StreamPeerTCP
var buffer := PackedByteArray()
var outgoing := PackedByteArray()
var last_snapshot: Dictionary = {}
var session := ""
var sequence := 0
var sent_at := 0
var received_ids: Dictionary = {}
var commands := 0
var connections := 0
var rejected := 0
var gameplay_enabled := false
var snapshot_metadata: Dictionary = {}

func start(port: int = 19727) -> Error:
    session = Crypto.new().generate_random_bytes(16).hex_encode()
    return listener.listen(port, "127.0.0.1")

func stop() -> void:
    if peer != null: peer.disconnect_from_host()
    peer = null
    listener.stop()
    buffer.clear()
    outgoing.clear()

func publish(entities: Array, zone_id: int = 207, source: String = "live") -> bool:
    if zone_id != 207 or entities.size() > MAX_ENTITIES: return false
    sequence += 1
    last_snapshot = {"type":"snapshot", "protocol":"daoc-visual-bridge", "version":VERSION,
        "session":session, "seq":sequence, "zone_id":zone_id, "source":source,
        "origin_m":[1364.0,130.0,1263.0], "entities":entities}
    for key in ["character","status","in_game","gm","max_speed_mps","doors","interaction","inventory","player_status","messages","chat","classic_ui","los_queries","spell_visuals","combat_audio","server_sound_audio","zone_lights","character_lobby","exchange"]:
        if snapshot_metadata.has(key):last_snapshot[key]=snapshot_metadata[key]
    return true

func _send(message: Dictionary) -> void:
    if peer == null: return
    var bytes := (JSON.stringify(message) + "\n").to_utf8_buffer()
    if bytes.size() > MAX_FRAME: rejected += 1; return
    # Drop superseded snapshots under backpressure; never block the game thread.
    if message.get("type", "") == "snapshot" and not outgoing.is_empty(): return
    if outgoing.size()+bytes.size()>MAX_FRAME:
        rejected+=1;peer.disconnect_from_host();return
    outgoing.append_array(bytes)

func _process(_delta: float) -> void:
    if listener.is_connection_available():
        var incoming := listener.take_connection()
        if peer != null and peer.get_status() == StreamPeerTCP.STATUS_CONNECTED:
            incoming.disconnect_from_host()
        else:
            peer = incoming; peer.set_no_delay(true); buffer.clear(); outgoing.clear(); received_ids.clear(); connections += 1
            _send({"type":"hello", "protocol":"daoc-visual-bridge", "version":VERSION,
                "session":session, "zone_id":207, "read_only":not gameplay_enabled})
    if peer == null: return
    peer.poll()
    if peer.get_status() != StreamPeerTCP.STATUS_CONNECTED: return
    if not outgoing.is_empty():
        var sent := peer.put_partial_data(outgoing.slice(0,65536))
        if sent[0] != OK: peer.disconnect_from_host(); return
        outgoing=outgoing.slice(int(sent[1]))
    var available := peer.get_available_bytes()
    if available + buffer.size() > MAX_FRAME:
        rejected += 1; peer.disconnect_from_host(); buffer.clear(); return
    if available > 0:
        var chunk := peer.get_data(available)
        if chunk[0] != OK: return
        buffer.append_array(chunk[1])
    var handled := 0
    while handled < 32:
        var end := buffer.find(10)
        if end < 0: break
        var value = JSON.parse_string(buffer.slice(0,end).get_string_from_utf8())
        buffer = buffer.slice(end+1); handled += 1
        if not value is Dictionary or value.get("type", "") != "command" or value.get("session", "") != session:
            rejected += 1; continue
        var id := String(value.get("id", ""))
        var action := String(value.get("action", ""))
        if id.is_empty() or id.length() > 100 or received_ids.has(id): rejected += 1; continue
        var permitted := action in ["ping", "select_preview"]
        if gameplay_enabled and action in ["move","target","interact","chat","logout","door","keyword","dialog_response","dismiss_interaction","inventory_move","inventory_equip","inventory_unequip","merchant_buy","merchant_sell","combat_attack","player_sit","gm_test_mode","player_release","ui_bank","ui_assign","ui_clear","ui_use","ui_use_slot","ui_detail","ui_detail_close","ui_server_window_close","los_reply","target_self","group_target","group_invite","group_remove","group_leave","journal_remove","journal_guide","journal_guide_close","trainer_refresh","trainer_train","conc_cancel","vault_close","character_enter","character_create","character_refresh","character_customize","exchange_close","exchange_search","exchange_page","exchange_buy","exchange_list","exchange_take","exchange_price","exchange_claim","exchange_tab","exchange_chest_page","exchange_inspect"]:permitted=true
        if not permitted: rejected += 1; continue
        if received_ids.size() >= 4096: received_ids.clear()
        received_ids[id] = true; commands += 1
        command_received.emit(value)
        _send({"type":"ack", "id":id, "action":action, "session":session,
            "ok":true, "forwarded_to_game":gameplay_enabled and action not in ["ping","select_preview"]})
    if not last_snapshot.is_empty() and Time.get_ticks_msec() - sent_at >= 50:
        sent_at = Time.get_ticks_msec(); _send(last_snapshot)

func _exit_tree() -> void: stop()
