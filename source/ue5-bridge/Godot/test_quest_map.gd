extends SceneTree

class ServerStub extends Node:
    var playing := true
    var entry := {"zone": 207}
    var map_markers := {}
    var marks: Array = []
    func quest_map_marks() -> Array:
        return marks

var checks := 0
var failures: Array = []

func check(ok: bool, label: String) -> void:
    checks += 1
    if not ok:
        failures.append(label)

func _initialize() -> void:
    var state = load("res://quest_map_state.gd")
    var server := ServerStub.new()
    check(state.snapshot(null, false).is_empty(), "missing server has no marks")
    check(state.snapshot(server, false).is_empty(), "empty original marks stay empty")
    server.marks = [{"at": Vector2(12.5, 51.0), "kind": "step"}]
    check(state.snapshot(server, false) == [{"position_m": [12.5, 51.0]}], "original projected meters are preserved")
    check(state.snapshot(server, true).is_empty(), "logout immediately hides marks")
    server.playing = false
    check(state.snapshot(server, false).is_empty(), "menu cannot show previous marks")
    server.playing = true
    server.entry.zone = 206
    check(state.snapshot(server, false).is_empty(), "unsupported zone cannot reuse Connacht coordinates")
    server.entry.zone = 207
    for point in [null, "12,51", [12,51], Vector2(INF,1), Vector2(0,NAN)]:
        server.marks = [{"at": point, "kind": "step"}]
        check(state.snapshot(server, false).is_empty(), "malformed projected coordinate is ignored")
    server.marks = [{"at": Vector2(12,51), "kind":"bot"}, {}, null]
    check(state.snapshot(server, false).is_empty(), "other markers cannot become quest objectives")
    server.marks.clear()
    for i in 129:
        server.marks.append({"at": Vector2(i,1), "kind":"step"})
    check(state.snapshot(server, false).size()==128, "map payload is bounded")
    server.map_markers = {1:Vector4.ONE, 0xFFFE0001:Vector4.ONE}
    state.reset(server)
    check(server.map_markers.is_empty(), "character change clears original per-player marker table")
    state.reset(null)
    check(state.snapshot(server, false).size()==128, "reset is independent of projected fixture input")
    server.free()
    var result := {"passed":failures.is_empty(),"checks":checks,"failures":failures}
    var file := FileAccess.open("res://verified_state.json", FileAccess.WRITE)
    file.store_string(JSON.stringify(result))
    file.close()
    print(JSON.stringify(result))
    quit(0 if failures.is_empty() else 1)
