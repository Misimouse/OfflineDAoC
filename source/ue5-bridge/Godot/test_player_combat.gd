extends SceneTree
class FakeClient extends Node:
    var calls:Array=[]
    func Attack(on:bool)->void:calls.append(on)
    func Sit(on:bool)->void:calls.append(["sit",on])
var failures:Array=[]
var checks:=0
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func _initialize()->void:
    var s=load("res://player_combat_state.gd").new();var c:=FakeClient.new();var entities:Dictionary={"npc:7":{"health":1,"realm":0}}
    s.consume("you",{},1,0);var generation:int=s.generation
    var command:Dictionary={"action":"combat_attack","on":true,"entity_id":"npc:7","player_generation":generation}
    check(not s.execute(command,c,"npc:7",entities,0),"no invented initial HP")
    check(not s.ready and c.calls.is_empty(),"unknown state cannot send attack")
    var status:Dictionary={"health_pct":84,"health":101,"max_health":120,"mana_pct":0,"mana":0,"max_mana":0,"endurance_pct":75,"endurance":75,"max_endurance":100,"conc_pct":100,"conc":0,"max_conc":0,"sitting":2}
    s.consume("status",status,1,1)
    check(s.ready and s.vitals.health_pct==84 and s.vitals.health==101 and s.vitals.max_health==120,"server percentages and absolute values retained")
    check(s.vitals.sitting and s.vitals.mana==0 and s.vitals.max_mana==0,"sitting bit and power-less character")
    check(s.run_speed_mps(300)==0,"seated movement is disabled")
    var rev:int=s.revision;s.consume("status",status,1,2);check(s.revision==rev,"unchanged status avoids UI rebuild")
    status.sitting=0;s.consume("status",status,1,2)
    check(is_equal_approx(s.run_speed_mps(100),4.775) and is_equal_approx(s.run_speed_mps(300),14.325),"normal and GM server speed")
    check(s.run_speed_mps(0)==0 and s.run_speed_mps(-1)==0,"server zero max speed does not become normal speed")
    check(s.execute(command,c,"npc:7",entities,3),"attack request")
    check(c.calls==[true] and not s.attack_on and s.pending.on,"mode not confirmed optimistically")
    check(s.vitals.health==101 and entities["npc:7"].health==1,"no local damage simulation")
    check(not s.execute(command,c,"npc:7",entities,4),"repeated pending request blocked")
    s.consume("attack_mode",{"on":true},1,5);check(s.attack_on and s.pending.is_empty(),"server confirms attack")
    check(s.execute(command,c,"npc:7",entities,6) and c.calls.size()==1,"confirmed mode request is idempotent")
    check(s.execute({"action":"combat_attack","on":false},c,"",{},7),"stop does not require a target or generation")
    check(c.calls==[true,false] and s.attack_on,"stop waits for actual server mode")
    s.consume("attack_mode",{"on":false},1,8);check(not s.attack_on and s.pending.is_empty(),"server stops attack")
    check(not s.execute(command,c,"npc:9",entities,9),"stale selection blocked")
    check(not s.execute(command,c,"npc:7",{},9),"removed target blocked")
    command.entity_id="";check(s.execute(command,c,"",{},10),"draw weapon with no target matches original client")
    check(s.execute({"action":"combat_attack","on":false},c,"",{},11),"stop can supersede an unconfirmed start")
    s.consume("attack_mode",{"on":false},1,12)
    command.entity_id="npc:7";command.on=1;check(not s.execute(command,c,"npc:7",entities,13),"numeric on is not boolean")
    command.on=true;command.player_generation=generation-1;check(not s.execute(command,c,"npc:7",entities,13),"previous region generation cannot attack")
    command.player_generation=generation
    s.consume("combat",{"attacker":7,"defender":1,"style":0x3E80,"health":0},1,14);check(s.vitals.health_pct==84,"bow prepare does not apply damage")
    s.consume("combat",{"attacker":7,"defender":1,"style":0,"health":255},1,15);check(s.vitals.health_pct==84,"unknown health byte ignored")
    s.consume("combat",{"attacker":7,"defender":2,"style":0,"health":0},1,16);check(s.vitals.health_pct==84,"other defender does not affect local health")
    s.consume("combat",{"attacker":7,"defender":1,"style":0,"health":50},1,17);check(s.vitals.health_pct==50 and not s.vitals.absolute_health_known,"hit updates percentage without inventing exact HP")
    s.consume("status",status,1,18);check(s.vitals.absolute_health_known and s.vitals.health_pct==84,"status restores exact values")
    s.consume("death",{"oid":2},1,19);check(s.vitals.health_pct==84,"other death cannot kill local player")
    s.consume("death",{"oid":1},1,20);check(s.ready and s.vitals.health_pct==0 and not s.attack_on,"actual death stops attack")
    check(s.run_speed_mps(300)==0,"dead player cannot move at GM speed")
    check(not s.execute(command,c,"npc:7",entities,21),"dead player cannot start attacking")
    s.consume("revive",{"oid":1},1,22);check(not s.ready,"revive awaits actual HP packet")
    status.health=20;status.health_pct=16;s.consume("status",status,1,23);check(s.ready and s.vitals.health_pct==16,"revival does not grant fake full health")
    s.consume("revive",{"oid":1},1,23);check(s.ready and s.vitals.health_pct==16,"real Status before Revive remains authoritative")
    check(s.execute(command,c,"npc:7",entities,24),"revived player requests attack")
    var count:int=c.calls.size();s.advance(4025);check(s.pending.is_empty() and not s.attack_on and c.calls.size()==count,"ack timeout never retries or confirms itself")
    check(s.attack_uncertain and not s.execute(command,c,"npc:7",entities,4030),"uncertain mode cannot start another attack")
    check(s.execute({"action":"combat_attack","on":false},c,"",{},4040) and c.calls.size()==count+1,"explicit stop still reaches server after missing acknowledgement")
    s.consume("attack_mode",{"on":false},1,4050);check(not s.attack_uncertain,"server acknowledgement clears uncertainty")
    var sit:Dictionary={"action":"player_sit","on":true,"player_generation":generation}
    check(s.execute(sit,c,"",{},4100),"sit uses original server request")
    check(not s.vitals.sitting and c.calls.back()==["sit",true],"no optimistic seated posture")
    status.sitting=2;s.consume("status",status,1,4101);check(s.vitals.sitting and s.posture_pending.is_empty(),"server confirms posture")
    sit.on=false;check(s.execute(sit,c,"",{},4102),"stand request")
    status.sitting=0;s.consume("status",status,1,4103);check(not s.vitals.sitting and s.posture_pending.is_empty(),"server confirms standing")
    s.consume("region_changed",{},1,5000);check(not s.ready and s.generation>generation and s.last_combat.is_empty(),"region reset clears player state and old handles")
    var f:=FileAccess.open("res://../Reports/player_state/godot_tests.json",FileAccess.WRITE);f.store_string(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures},"  "));f.close();print("PLAYER_STATE_CHECKS ",checks," failures=",failures);c.free();quit(0 if failures.is_empty() else 1)
