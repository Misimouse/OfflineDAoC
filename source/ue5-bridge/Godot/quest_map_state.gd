extends RefCounted
## Reuse Server.quest_map_marks, including its region and zone projection.
const MAX_MARKS := 128

static func snapshot(server: Node, leaving: bool) -> Array:
    if server == null or leaving or not bool(server.get("playing")):
        return []
    var entry: Variant = server.get("entry")
    if not entry is Dictionary or int(entry.get("zone", -1)) != 207:
        return []
    if not server.has_method("quest_map_marks"):
        return []
    var rows: Variant = server.call("quest_map_marks")
    if not rows is Array:
        return []
    var marks: Array = []
    for row in rows:
        if not row is Dictionary or row.get("kind", "") != "step":
            continue
        var point: Variant = row.get("at")
        if not point is Vector2 or not point.is_finite():
            continue
        marks.append({"position_m": [point.x, point.y]})
        if marks.size() >= MAX_MARKS:
            break
    return marks

static func reset(server: Node) -> void:
    if server == null:
        return
    var markers: Variant = server.get("map_markers")
    if markers is Dictionary:
        markers.clear()
