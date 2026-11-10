extends SceneTree
var checks:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func _initialize()->void:
    var folder:String=get_script().resource_path.get_base_dir()
    var a=load(folder.path_join("decoded_world_adapter.gd")).new()
    a.zone_info={"x":35,"y":51}
    a.consume_world("you",{"oid":1,"x":341280,"y":468312,"z":5200,"model":0})
    var spawn:={"oid":2,"session":17,"x":341280,"y":468312,"z":5200,"heading":0,"model":318,"size":50,"name":"Other player","level":10,"flags":12}
    a.consume_world("player",spawn)
    var row:Dictionary=a.entities["player:2"]
    a.consume_world("equipment",{"oid":2,"items":[{"slot":10,"model":445}],"weapon_slots":0})
    var gear:Dictionary=row.equipment.duplicate(true)
    # PacketLib168.SendModelChange uses size zero for players. Zero means
    # unchanged size, not a request to reduce the native body to its clamp.
    a.consume_world("model_change",{"oid":2,"model":118,"size":0})
    check(row.model_id==118,"remote original model change reaches world row")
    check(row.size==50,"player model change with zero size retains original size")
    check(row.equipment==gear,"morph retains server equipment for later restoration")
    a.consume_world("model_change",{"oid":2,"model":318,"size":0})
    check(row.model_id==318 and row.size==50,"return to race model retains normal size")
    check(row.equipment==gear,"return retains authoritative equipment revision")
    a.consume_world("model_change",{"oid":2,"model":118,"size":75})
    check(row.size==75,"explicit nonzero model size is applied")
    a.consume_world("model_change",{"oid":2,"model":318,"size":0})
    check(row.size==75,"zero also preserves an explicitly changed size")
    var before:Dictionary=row.duplicate(true)
    a.consume_world("model_change",{"oid":999,"model":118,"size":0})
    check(row==before and a.entities.size()==2,"unknown model change cannot create a living")
    var npc:Dictionary=spawn.duplicate();npc.oid=3;npc.erase("session");npc.size=85
    a.consume_world("npc",npc)
    a.consume_world("model_change",{"oid":3,"model":118,"size":0})
    check(a.entities["npc:3"].size==85,"NPC zero-size refresh retains actual size")
    a.consume_world("model_change",{"oid":3,"model":123,"size":120})
    check(a.entities["npc:3"].size==120,"original NPC model-and-size request still resizes")
    a.consume_world("quit",{})
    check(a.entities.is_empty() and a.equipment_packets.is_empty(),"logout clears model and retained equipment")
    a.free()
    var result:={"passed":failures.is_empty(),"checks":checks,"failures":failures}
    print(JSON.stringify(result));quit(0 if failures.is_empty() else 1)
