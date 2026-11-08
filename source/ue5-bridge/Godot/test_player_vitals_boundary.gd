extends SceneTree
class Fake:
    extends Node
    var calls:Array=[]
    func Attack(on:bool)->void:calls.append(["attack",on])
    func Sit(on:bool)->void:calls.append(["sit",on])
    func Command(text:String)->void:calls.append(["command",text])
var checks:=0
var failures:Array=[]
func check(value:bool,label:String)->void:
    checks+=1
    if not value:failures.append(label)
func _initialize()->void:
    var state=load("res://player_combat_state.gd").new();var release=load("res://player_release.gd").new();var client:=Fake.new()
    var status:Dictionary={"health_pct":0,"health":1,"max_health":336,"mana_pct":100,"endurance_pct":100}
    state.consume("status",status,1,10)
    check(state.ready and state.alive(),"one real HP is alive even when its percentage rounds to zero")
    check(state.vitals.health_pct==0 and state.vitals.health==1,"original server values are preserved exactly")
    check(is_equal_approx(state.health_fraction(),1.0/336.0),"world health fraction uses the confirmed original points")
    check(is_equal_approx(state.run_speed_mps(100),4.775),"living zero-percent player retains normal movement")
    var epoch:int=state.generation
    check(state.execute({"action":"combat_attack","on":true,"entity_id":"","player_generation":epoch},client,"",{},20),"living zero-percent player can request drawing a weapon")
    state.consume("attack_mode",{"on":true},1,21)
    check(state.attack_on,"attack still waits for original mode acknowledgement")
    check(not release.request({"player_generation":epoch},state,client,22) and release.requests==0,"living zero-percent player cannot request release")
    check(state.execute({"action":"player_sit","on":true,"player_generation":epoch},client,"",{},23),"sitting is allowed for an actually living player")
    status.sitting=2;state.consume("status",status,1,24)
    check(state.vitals.sitting and state.run_speed_mps(100)==0,"confirmed sitting still blocks movement")
    status.sitting=0;status.health=68;status.health_pct=20;state.consume("status",status,1,25)
    state.consume("combat",{"attacker":2,"defender":1,"style":0,"health":0},1,26)
    check(state.alive() and state.ready,"rounded combat zero waits for actual status or death")
    check(not state.vitals.absolute_health_known and state.vitals.health_pct==0,"combat does not invent exact remaining HP")
    check(state.attack_on,"ambiguous combat percentage cannot cancel a confirmed attack")
    var audio=load("res://combat_audio_state.gd").new();audio.configure({"310":8,"123":9},{"445":{"sound_set":25}})
    var rows:Dictionary={"player:local":{"model_id":310,"position_m":[1,2,3],"health":0.0,"alive":true,"state":"idle"},"npc:2":{"model_id":123,"position_m":[2,2,3],"health":1.0}}
    audio.consume("combat",{"attacker":2,"defender":1,"weapon":445,"style":0,"result":10,"health":0},1,{2:"npc:2"},rows,100)
    check(not audio.dead.has("player:local") and not audio.events.any(func(e):return e.owner=="player:local" and e.event=="die"),"rounded local combat percentage cannot play a false death")
    audio.consume("combat",{"attacker":1,"defender":2,"weapon":445,"style":0,"result":10,"health":99},1,{2:"npc:2"},rows,101)
    check(audio.events.any(func(e):return e.owner=="player:local" and e.event=="use"),"confirmed living zero-percent player retains attack audio")
    var visual=load("res://combat_visual_state.gd").new()
    check(visual._living("player:local",rows),"visual state accepts explicit living state without inventing HP")
    state.consume("death",{"oid":1},1,200);audio.consume("death",{"oid":1},1,{},rows,200);audio.consume("death",{"oid":1},1,{},rows,201)
    check(not state.alive() and state.vitals.health==0 and state.run_speed_mps(100)==0,"actual death clears life and freezes movement")
    check(not state.attack_on and state.pending.is_empty(),"actual death cancels attack state")
    check(audio.events.filter(func(e):return e.owner=="player:local" and e.event=="die").size()==1,"actual death packet plays its death sound once")
    check(not state.execute({"action":"combat_attack","on":true,"entity_id":"","player_generation":epoch},client,"",{},202),"actual dead character cannot draw a weapon")
    check(release.request({"player_generation":epoch},state,client,203),"actual dead character can request original release")
    state.consume("combat",{"attacker":2,"defender":1,"style":0,"health":50},1,204)
    check(not state.alive(),"late combat percentage cannot revive a confirmed death")
    status.health=1;status.health_pct=0;state.consume("status",status,1,205);release.consume("status",status,1,state);state.consume("revive",{"oid":1},1,206)
    check(state.ready and state.alive() and state.vitals.health==1,"real low-HP status before revive remains authoritative")
    check(not release.pending,"real positive points confirm release even at rounded zero percent")
    for bad in [NAN,INF,-1,0.5,true,"1"]:
        var malformed:Dictionary=status.duplicate();malformed.health=bad;state.consume("status",malformed,1,300)
        check(not state.vitals.absolute_health_known and not state.alive(),"malformed absolute HP cannot grant life")
    state.ready=true;state.vitals={"health_pct":100};check(state.alive(),"legacy percent-only living snapshots remain supported")
    state.vitals.health_pct=0;check(not state.alive(),"legacy percent-only dead snapshots remain supported")
    state.consume("region_changed",{},1,400);check(not state.ready and not state.alive(),"region reset discards old life state")
    var report:Dictionary={"passed":failures.is_empty(),"checks":checks,"failures":failures,"server_started":false}
    print(JSON.stringify(report));client.free();quit(0 if failures.is_empty() else 1)
