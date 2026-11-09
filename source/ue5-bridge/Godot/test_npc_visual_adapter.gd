extends SceneTree
var checks:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func _initialize()->void:
    var folder:String=get_script().resource_path.get_base_dir()
    var adapter=load(folder.path_join("decoded_world_adapter.gd")).new()
    adapter.zone_info={"x":35,"y":51}
    var spawn:={"oid":42,"x":35*8192+4000,"y":51*8192+4000,"z":5000,"heading":0,"model":110,"health":100,"flags":1,"flags2":0}
    adapter.consume_world("npc",spawn)
    check(adapter.entities["npc:42"].npc_visual.ghost,"decoded spawn carries ghost contract")
    adapter.consume_world("move",{"oid":42,"zone":207,"x":4100,"y":4100,"z":5000,"heading":0,"speed":20,"flags":0,"flags2":255})
    check(adapter.entities["npc:42"].npc_visual.ghost,"zone/movement flags preserve ghost")
    adapter.consume_world("model_change",{"oid":42,"model":307})
    check(adapter.entities["npc:42"].npc_visual.ghost and adapter.entities["npc:42"].model_id==307,"model change preserves server ghost identity")
    adapter.consume_world("equipment",{"oid":42,"items":[],"weapon_slots":255})
    check(adapter.entities["npc:42"].npc_visual.ghost and adapter.entities["npc:42"].has("equipment"),"equipment packet preserves ghost")
    spawn.flags=4;adapter.consume_world("npc",spawn)
    check(not adapter.entities["npc:42"].npc_visual.ghost and adapter.entities["npc:42"].npc_visual.torch_flag,"replacement spawn cannot borrow ghost from same OID")
    spawn.erase("flags2");adapter.consume_world("npc",spawn)
    check(adapter.entities["npc:42"].npc_visual.is_empty(),"incomplete create forgets previous visual contract")
    adapter.consume_world("remove",{"oid":42,"type":1})
    check(not adapter.entities.has("npc:42"),"removal clears identity")
    spawn.flags=1;spawn.flags2=0;adapter.consume_world("npc",spawn)
    adapter.consume_world("region_changed",{})
    check(adapter.entities.is_empty(),"zone change clears visual state")
    adapter.free()
    var result:={"passed":failures.is_empty(),"checks":checks,"failures":failures,"installed":false}
    FileAccess.open("res://npc_adapter_tests.json",FileAccess.WRITE).store_string(JSON.stringify(result));print(JSON.stringify(result));quit(0 if failures.is_empty() else 1)
