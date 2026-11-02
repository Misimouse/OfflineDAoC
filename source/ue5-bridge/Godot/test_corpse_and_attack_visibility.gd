extends SceneTree
var checks:=0
var failures:Array=[]
class FakeClient extends Node:
    var calls:Array=[]
    func Heading(a,b,c,d):calls.append(["heading",a,b,c,d])
    func Attack(on):calls.append(["attack",on])
class FakeServer extends Node:
    var client:Node
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func spawn(oid:int)->Dictionary:
    return {"oid":oid,"x":35*8192+56000,"y":51*8192+50000,"z":5200,"heading":0,"model":348,"name":"Probe","size":50,"speed":0}
func _initialize()->void:
    var a=load("res://decoded_world_adapter.gd").new();a.zone_info={"x":35,"y":51}
    a.consume_world("npc",spawn(2));var before:Dictionary=a.entities["npc:2"].duplicate(true)
    a.consume_world("remove",{"oid":2,"type":0})
    check(a.entities.has("npc:2") and not a.oid_to_id.has(2),"dead removal keeps visual actor and detaches server identity")
    var row:Dictionary=a.entities["npc:2"]
    check(row.state=="dead" and row.health==0 and row.speed_mps==0,"dead removal without HP starts death")
    check(not row.targetable and not row.show_name,"corpse is not targetable and hides name")
    check(row.model_id==before.model_id and row.position_m==before.position_m,"original model and position retained")
    check(row.motion.event=="death" and not row.motion.position_valid,"death freezes previous native visual position")
    var at:int=a.corpses["npc:2"].at_ms
    a.advance_corpses(at+11999);check(row.position_m==before.position_m,"body remains before sink")
    a.advance_corpses(at+14000);check(is_equal_approx(float(row.position_m[1]),float(before.position_m[1])-1.0),"body sinks progressively")
    check(row.motion.position_valid and row.motion.event=="death","native motion receives sink positions without restarting death age")
    a.advance_corpses(at+16000);check(a.entities.is_empty() and a.corpses.is_empty(),"corpse expires without loot invention")
    a.consume_world("npc",spawn(2));a.consume_world("combat",{"attacker":1,"defender":2,"health":0});var seq:int=a.entities["npc:2"].motion.seq
    a.consume_world("remove",{"oid":2,"type":0});check(a.entities["npc:2"].motion.seq==seq,"existing death timestamp does not restart on remove")
    a.consume_world("remove",{"oid":2,"type":0});check(a.corpses.size()==1,"duplicate death remove does not duplicate corpse")
    a.consume_world("npc",spawn(2));check(a.entities.has("npc:2") and a.entities["npc:2"].health>0 and a.entities.size()==2,"OID reuse spawns living separately from old corpse")
    a.consume_world("remove",{"oid":2,"type":1});check(a.entities.size()==1,"normal visibility removal does not invent corpse")
    a.clear_world();check(a.entities.is_empty() and a.corpses.is_empty(),"session reset clears corpse timers")
    var g=load("res://live_gateway.gd").new();var c=FakeClient.new();var server=FakeServer.new();server.client=c
    g.server=server;g.adapter=a;g.interaction=load("res://interaction_state.gd").new();g.player_state=load("res://player_combat_state.gd").new()
    a.consume_world("npc",spawn(3));g.interaction.selected_id="npc:3";var now:=Time.get_ticks_msec();g.target_sight_id="npc:3";g.target_sight=true;g.target_sight_at=now
    check(g.target_visible(now),"fresh native visibility belongs to selected target")
    check(not g.target_visible(now+1501),"expired visibility cannot grant view")
    g.target_sight_id="npc:2";check(not g.target_visible(now),"previous target visibility never transfers to next target")
    g.target_sight_id="npc:3";g.player_state.consume("status",{"health_pct":100},1,now)
    check(g.player_state.execute({"action":"combat_attack","on":true,"entity_id":"npc:3","player_generation":g.player_state.generation},c,"npc:3",a.entities,now,g.sync_attack_visibility),"attack can follow a prior target death")
    check(c.calls.size()==2 and c.calls[0][0]=="heading" and c.calls[0][2]==3 and c.calls[0][3]==0x30 and c.calls[1]==["attack",true],"fresh server visibility sent immediately before original Attack request")
    g.player_state.consume("attack_mode",{"on":false},1,now+1);c.calls.clear();g.target_sight=false
    g.player_state.execute({"action":"combat_attack","on":true,"entity_id":"npc:3","player_generation":g.player_state.generation},c,"npc:3",a.entities,now+2,g.sync_attack_visibility)
    check(c.calls[0][3]==0,"blocked native sight is never forced clear")
    g.player_state.consume("attack_mode",{"on":true},1,now+3);c.calls.clear()
    check(not g.player_state.observe_target_death("remove",{"oid":2,"type":0},"npc:3",a.oid_to_id,a.entities,c,now+4),"another target death cannot stop this fight")
    check(g.player_state.observe_target_death("remove",{"oid":3,"type":0},"npc:3",a.oid_to_id,a.entities,c,now+5),"selected target death requests original Attack false")
    check(c.calls==[["attack",false]] and g.player_state.attack_on and not g.player_state.pending.on,"death stop waits for server ACK without inventing mode")
    check(not g.player_state.observe_target_death("death",{"oid":3},"npc:3",a.oid_to_id,a.entities,c,now+6) and c.calls.size()==1,"duplicate death does not retry a pending stop")
    g.player_state.consume("attack_mode",{"on":false},1,now+7)
    check(not g.player_state.attack_on and g.player_state.pending.is_empty(),"stop ACK clears mode for following fight")
    a.consume_world("npc",spawn(4));g.interaction.selected_id="npc:4";g.target_sight_id="npc:4";g.target_sight=true;g.target_sight_at=now
    check(g.player_state.execute({"action":"combat_attack","on":true,"entity_id":"npc:4","player_generation":g.player_state.generation},c,"npc:4",a.entities,now+8,g.sync_attack_visibility),"second independent target can start attacking after death ACK")
    g.target_sight_id="npc:3";g.interaction.selected_id="npc:3"
    a.consume_world("remove",{"oid":3,"type":0});check(not g.target_visible(now),"dead target cannot keep visibility")
    var f=FileAccess.open("res://../Reports/combat_lifecycle/offline_tests.json",FileAccess.WRITE);f.store_string(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures},"  "));f.close()
    print("CORPSE_VISIBILITY_CHECKS ",checks," failures=",failures)
    g.free();a.free();c.free();server.free();quit(0 if failures.is_empty() else 1)
