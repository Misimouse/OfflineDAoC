extends SceneTree
var failures:Array=[]
var checks:=0
var requests:Array=[]
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func _initialize()->void:
    var a=load("res://decoded_world_adapter.gd").new();a.zone_info={"x":35,"y":51};a.missing_entity.connect(func(oid):requests.append(oid))
    var spawn:Dictionary={"oid":1,"region":200,"x":35*8192+56000,"y":51*8192+50000,"z":5200,"heading":0,"model":123,"health":100,"speed":80}
    a.consume_world("you",spawn);spawn.oid=2;a.consume_world("npc",spawn)
    var row:Dictionary=a.entities["npc:2"];var motion:Dictionary=row.motion.duplicate(true)
    a.consume_world("combat",{"attacker":1,"defender":2,"health":63,"style":0,"result":10})
    check(is_equal_approx(row.health,.63) and row.health_known,"actual defender health applied")
    check(row.motion==motion,"ordinary hit does not reset interpolation")
    check(a.entities["player:local"].health==1,"remote damage cannot change local health")
    for invalid in [-1,101,255,1.5,"50",true]:
        a.consume_world("combat",{"attacker":1,"defender":2,"health":invalid});check(is_equal_approx(row.health,.63),"invalid damage percentage ignored: "+str(invalid))
    a.consume_world("combat",{"attacker":1,"defender":2,"health":0,"style":0x3E80});check(is_equal_approx(row.health,.63),"bow prepare is not death")
    a.consume_world("combat",{"attacker":1,"defender":2,"health":0,"style":0x3E83});check(row.health==0 and row.state=="dead" and row.speed_mps==0,"actual bow hit can kill defender")
    check(row.motion.seq>motion.seq and not row.motion.position_valid,"death stops prediction without inventing position")
    var death_seq:int=row.motion.seq;a.consume_world("combat",{"attacker":1,"defender":2,"health":0});check(row.motion.seq==death_seq,"repeated death health does not restart death event")
    a.consume_world("combat",{"attacker":88,"defender":89,"health":40});check(requests==[88,89],"unknown combatants requested via original object protocol")
    a.consume_world("combat",{"attacker":88,"defender":89,"health":40});check(requests==[88,89],"combat object requests throttled")
    a.consume_world("object",{"oid":90});a.consume_world("combat",{"attacker":90,"defender":1,"health":0});check(requests==[88,89],"nonliving and local combatants never requested as mobs")
    check(a.entities["player:local"].health==1,"local status belongs to separate authoritative player state")
    a.consume_world("combat",{"attacker":0,"defender":65536,"health":0});check(requests==[88,89],"invalid object IDs ignored")
    a.consume_world("region_changed",{});check(a.entities.is_empty() and a.requested.is_empty(),"region cleanup clears combatant cache")
    var file:=FileAccess.open("res://../Reports/player_state/combat_entity_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify({"checks":checks,"passed":failures.is_empty(),"failures":failures},"  "));file.close();a.free();print("COMBAT_ENTITY_CHECKS ",checks," failures=",failures);quit(0 if failures.is_empty() else 1)
