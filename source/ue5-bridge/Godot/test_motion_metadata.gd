extends SceneTree
func _initialize()->void:
    var a=load("res://decoded_world_adapter.gd").new();a.zone_info={"x":35,"y":51}
    a.consume_world("npc",{"oid":2,"x":35*8192+56000,"y":51*8192+50000,"z":5200,"heading":0,"model":999980,"speed":100})
    var row:Dictionary=a.entities["npc:2"];var first:int=row.motion.seq
    assert(row.motion.position_valid and is_equal_approx(row.motion.speed_mps,2.5))
    a.consume_world("move",{"oid":2,"zone":207,"x":56000,"y":50000,"z":5200,"tx":56400,"ty":50200,"tz":5200,"tzone":207,"speed":100,"heading":0})
    assert(row.motion.seq>first and row.motion.destination_m==[1410.0,130.0,1255.0])
    var seq:int=row.motion.seq
    a.consume_world("model_change",{"oid":2,"model":999981,"size":50})
    assert(row.motion.seq==seq)
    a.consume_world("death",{"oid":2})
    assert(not row.motion.position_valid and row.motion.speed_mps==0 and row.motion.seq>seq)
    a.consume_world("revive",{"oid":2})
    assert(not row.motion.position_valid and row.motion.speed_mps==0)
    a.consume_world("move",{"oid":2,"zone":207,"x":56000,"y":50000,"z":5200,"tx":56400,"ty":50200,"tz":5200,"tzone":208,"speed":100})
    assert(row.motion.position_valid and not row.motion.has("destination_m"))
    var f:=FileAccess.open("res://../Reports/movement/godot_tests.json",FileAccess.WRITE);f.store_string(JSON.stringify({"passed":true,"checks":6}));f.close()
    print("MOTION_METADATA 6 checks passed");a.free();quit()
