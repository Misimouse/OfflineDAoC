extends SceneTree
var checks:=0
var failures:Array=[]
func check(value:bool,label:String)->void:
    checks+=1
    if not value:failures.append(label)
func _initialize()->void:
    var state=load(get_script().resource_path.get_base_dir().path_join("combat_audio_state.gd")).new()
    state.configure({"310":8,"123":9},{"445":{"sound_set":25},"555":{"sound_set":20}})
    var ids:Dictionary={2:"npc:2"}
    var entities:Dictionary={"player:local":{"model_id":310,"position_m":[1,2,3],"health":1.0,"health_known":true},
        "npc:2":{"model_id":123,"position_m":[2,2,3],"health":1.0,"health_known":true}}
    var untouched:Dictionary=entities.duplicate(true)
    var packet:Dictionary={"attacker":1,"defender":2,"weapon":445,"shield":555,"style":0,"result":10,"health":95}
    state.consume("combat",packet,1,ids,entities,1000)
    var got:Array=state.snapshot(1001)
    check(got.size()==3 and got[0].sheet=="weapons" and got[0].event=="use","real melee packet emits weapon swing")
    check(got[1].event=="hit_light" and got[2].event=="pain_light","small hit uses original light impact and pain")
    check(got[0].age_ms==1 and state.snapshot(1200)[0].seq==got[0].seq,"snapshots retain sequence and event age")
    check(entities==untouched,"audio cannot change world health, equipment or coordinates")
    packet.health=70;state.consume("combat",packet,1,ids,entities,1200)
    got=state.snapshot(1200)
    check(got.size()==5 and got.back().event=="hit_medium","previous packet health retained and pain throttled700ms")
    state.reset();packet.style=12;packet.result=11
    state.consume("combat",packet,1,ids,entities,2000);got=state.snapshot(2000)
    check(got[0].event=="style_use" and got[1].event=="style_hit" and got[2].event=="pain_heavy","styled hit uses original style audio")
    state.reset();packet.style=0;packet.result=1
    state.consume("combat",packet,1,ids,entities,3000);got=state.snapshot(3000)
    check(got.size()==2 and got[1].event=="parried" and got[1].set==20,"parry uses defender packet weapon sound set")
    state.reset();packet.result=2;packet.shield=0
    state.consume("combat",packet,1,ids,entities,4000)
    check(state.snapshot(4000).back().set==19,"original weaponless set handles missing defense weapon")
    state.reset();packet.result=3
    state.consume("combat",packet,1,ids,entities,5000)
    check(state.snapshot(5000).back().event=="evade","evade uses defender creature sheet")
    state.reset();packet.result=0x94;packet.health=90
    state.consume("combat",packet,1,ids,entities,6000);got=state.snapshot(6000)
    check(got.size()==1 and got[0].sheet=="creatures" and got[0].event=="pain_medium","masked spell damage never emits weapon audio")
    state.reset();packet.style=0x3E80;packet.health=0
    state.consume("combat",packet,1,ids,entities,7000)
    check(state.snapshot(7000).is_empty() and state.dead.is_empty(),"bow preparation cannot invent hit or death audio")
    state.reset();packet.style=0;packet.result=10
    state.consume("combat",packet,1,ids,entities,8000)
    state.consume("death",{"oid":2},1,ids,entities,8001)
    got=state.snapshot(8001)
    check(got.size()==3 and got.back().event=="die","fatal hit followed by death packet cries exactly once")
    state.consume("remove",{"oid":2},1,ids,entities,8002)
    check(state.snapshot(8002).size()==3,"object removal cannot duplicate a death")
    state.consume("revive",{"oid":2,"health":100},1,ids,entities,8100)
    state.consume("death",{"oid":2},1,ids,entities,8200)
    check(state.snapshot(8200).size()==4,"a revived living may die again")
    state.consume("npc",{"oid":2,"health":100},1,{},entities,8300)
    check(not state.dead.has("npc:2"),"server OID reuse clears old death even before adapter publishes its new identity")
    state.reset();packet.attacker=2;packet.defender=1;packet.weapon=0;packet.health=50
    state.consume("combat",packet,1,ids,entities,9000);got=state.snapshot(9000)
    check(got[0].event=="attack" and got[0].sheet=="creatures" and got[1].set==19,"unarmed creature uses its vocal and original weaponless impact")
    state.reset();packet.attacker=60000;packet.defender=60001
    state.consume("combat",packet,1,ids,entities,10000)
    check(state.snapshot(10000).is_empty(),"unknown combatants never become invented audio sources")
    packet.attacker=1;packet.defender=2;packet.health=101
    state.consume("combat",packet,1,ids,entities,11000)
    check(not state.dead.has("npc:2"),"invalid health cannot invent death")
    check(state.snapshot(14000).is_empty(),"stale event queues expire")
    state.consume("quit",{},1,ids,entities,14000)
    check(state.events.is_empty() and state.health.is_empty() and state.dead.is_empty(),"session reset clears pending audio and health history")
    check(entities==untouched,"all dispatch cases preserve authoritative world state")
    state.reset();entities["player:local"].state="dead";entities["player:local"].health=0
    packet.result=10;packet.weapon=445;packet.health=50
    state.consume("combat",packet,1,ids,entities,15000)
    var no_dead_swing:=true
    for value in state.snapshot(15000):
        if value.owner=="player:local":no_dead_swing=false
    check(no_dead_swing,"already dead attacker cannot start a new weapon voice")
    print(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures,"scope":"isolated combat audio decisions only; not native playback or installed"}))
    quit(0 if failures.is_empty() else 1)
