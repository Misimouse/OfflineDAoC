extends RefCounted
## Inactive until the bridge supplies original packets and authoritative interaction context.
const OFFER := 0x22
const REWARD := 0x21
const TIMEOUT_MS := 5000

var _dialog: Dictionary = {}
var _binding: Array = []
var _pending: Dictionary = {}
var _responded: Dictionary = {}
var _crypto := Crypto.new()
var feedback := ""

# Context must come from the bridge, never from a UI command. conversation_epoch
# changes on each NPC interaction, even when an object ID is reused.
func _identity(context: Dictionary, giver: int) -> Array:
    var row: Dictionary = context.get("npc", {})
    var id := "npc:%d" % giver
    if not context.get("alive", false) or context.get("selected", "") != id or context.get("conversation", "") != id:
        return []
    if row.get("id", "") != id or row.get("kind", "") != "npc" or not row.get("targetable", true) or not (float(row.get("health", 0)) > 0):
        return []
    var distance := float(context.get("distance_m", INF))
    var epoch := int(context.get("conversation_epoch", 0))
    if not is_finite(distance) or distance < 0 or distance > 6 or epoch <= 0:
        return []
    return [epoch, id, row.get("name", ""), row.get("model_id", 0)]

func reset() -> void:
    _dialog.clear()
    _binding.clear()
    _pending.clear()
    _responded.clear()
    feedback = ""

func observe(kind: String, data: Dictionary) -> void:
    if kind in ["you", "region_changed", "quit", "disconnect", "death"]:
        reset()
    elif kind == "remove" and not _binding.is_empty() and ("npc:%d" % int(data.get("oid", 0))) == _binding[1]:
        _dialog.clear()
        _binding.clear()

func receive(data: Dictionary, context: Dictionary) -> bool:
    var code := _number(data.get("code"), OFFER)
    var quest := _number(data.get("quest_id"), 65535)
    var giver := _number(data.get("giver_id"), 65535)
    if code not in [OFFER, REWARD] or quest <= 0 or giver <= 0:
        return false
    if _number(data.get("type"), 2) != (2 if code == OFFER else 1):
        return false
    var binding := _identity(context, giver)
    if binding.is_empty() or not _pending.is_empty():
        return false
    var title: Variant = data.get("title")
    var options: Variant = data.get("optional_items")
    var required := _number(data.get("required_choices"), 8)
    if not title is String or title.strip_edges().is_empty() or not options is Array or options.size() > 255 or required < 0 or required > options.size():
        return false
    var key := JSON.stringify([binding, quest, code])
    if _responded.has(key):
        return false
    if not _dialog.is_empty() and _dialog.key == key and data == _dialog.payload:
        return true
    _binding = binding
    _dialog = {"key": key, "token": _crypto.generate_random_bytes(16).hex_encode(), "payload": data.duplicate(true)}
    feedback = ""
    return true

func _number(value: Variant, limit: int) -> int:
    if not (value is int or value is float) or not is_finite(float(value)) or value < 0 or value > limit or float(value) != floor(float(value)):
        return -1
    return int(value)

func _journal_matches(journal: Array, title: String) -> Array:
    var matches: Array = []
    for row in journal:
        var name := String(row.get("name", ""))
        var level_suffix := name.trim_prefix(title)
        if name == title or (name.begins_with(title) and level_suffix.begins_with(" (Level ") and level_suffix.ends_with(")") and level_suffix.substr(8, level_suffix.length() - 9).is_valid_int()):
            matches.append(row.get("index", -1))
    return matches

func maintain(context: Dictionary, journal: Array, now: int) -> void:
    if not _dialog.is_empty() and _identity(context, int(_dialog.payload.giver_id)) != _binding:
        _dialog.clear()
        _binding.clear()
    if _pending.is_empty():
        return
    var matches := _journal_matches(journal, _pending.title)
    if (_pending.action == "accept" and matches.size() == 1) or (_pending.action == "finish" and matches.is_empty()):
        feedback = "Journal updated by the server."
        _pending.clear()
    elif now - int(_pending.at) >= TIMEOUT_MS:
        feedback = "The server has not confirmed the request. Check your journal."
        _pending.clear()

func request(command: Dictionary, client: Object, context: Dictionary, journal: Array, now: int) -> bool:
    maintain(context, journal, now)
    if _dialog.is_empty() or command.get("token") != _dialog.token or not _pending.is_empty():
        return false
    var action: Variant = command.get("action")
    var data: Dictionary = _dialog.payload
    if action == "close":
        _dialog.clear()
        _binding.clear()
        return true
    var matches := _journal_matches(journal, data.title)
    var sent := false
    if data.code == OFFER and action in ["accept", "decline"] and matches.is_empty():
        sent = client.call("QuestOffer", int(data.quest_id), int(data.giver_id), action == "accept") == true
    elif data.code == REWARD and action == "finish" and matches.size() == 1 and not context.get("exchange_busy", false):
        var choices: Variant = command.get("choices")
        if not choices is Array or choices.size() != int(data.required_choices):
            return false
        var indices := PackedInt32Array()
        for raw in choices:
            var index := _number(raw, data.optional_items.size() - 1)
            if index < 0 or indices.has(index):
                return false
            indices.append(index)
        sent = client.call("QuestReward", int(data.quest_id), int(data.giver_id), int(data.required_choices), data.optional_items.size(), indices) == true
    if not sent:
        return false
    # Remember the response for this conversation, including declines. A fresh
    # interaction can reoffer after rejection or a missing server response.
    _responded[_dialog.key] = _binding[0]
    for key in _responded.keys():
        if _responded[key] != _binding[0]:
            _responded.erase(key)
    if action != "decline":
        _pending = {"action": action, "title": data.title, "at": now}
        feedback = "Request sent to server."
    else:
        feedback = ""
    _dialog.clear()
    _binding.clear()
    return true

func finishing() -> bool:
    return _pending.get("action", "") == "finish"

func snapshot() -> Dictionary:
    return {
        "dialog": {} if _dialog.is_empty() else _dialog.payload.duplicate(true),
        "token": _dialog.get("token", ""),
        "pending": not _pending.is_empty(),
        "feedback": feedback,
    }
