extends SceneTree
class Fake:
    extends Node
    var sent:Array=[]
    func Command(text:String)->void:sent.append(text)
var checks:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func _initialize()->void:
    var mode=load("res://player_release.gd").new();var state=load("res://player_combat_state.gd").new();var client:=Fake.new()
    state.generation=7
    check(not mode.request({"player_generation":7},state,client,1),"unknown status blocked")
    state.ready=true;state.vitals={"health_pct":100}
    check(not mode.request({"player_generation":7},state,client,1),"living blocked")
    state.vitals.health_pct=0
    for epoch in [6,"7",true,NAN,INF]:check(not mode.request({"player_generation":epoch},state,client,1),"invalid/stale generation blocked")
    check(client.sent.is_empty(),"invalid requests never reach server")
    check(mode.request({"player_generation":7},state,client,100),"dead release accepted")
    check(client.sent==["&release"],"original raw server command used")
    check(state.vitals.health_pct==0 and state.ready,"no local revival")
    check(not mode.request({"player_generation":7},state,client,101) and client.sent.size()==1,"duplicate blocked")
    mode.consume("status",{"health_pct":0},4);check(mode.pending,"dead status is not release confirmation")
    mode.consume("revive",{"oid":4},4);check(mode.pending,"revive announcement waits for actual health")
    mode.consume("status",{"health_pct":NAN},4);check(mode.pending,"invalid health not confirmation")
    mode.consume("status",{"health_pct":12},4);check(not mode.pending,"real positive status completes")
    mode.request({"player_generation":7},state,client,200);mode.advance(8199);check(mode.pending,"deadline not premature")
    mode.advance(8200);check(not mode.pending and not mode.feedback.is_empty(),"timeout allows manual retry without success")
    check(mode.request({"player_generation":7},state,client,8300),"manual retry allowed")
    mode.consume("region_changed",{},4);check(not mode.pending and mode.feedback.is_empty(),"region resets old request")
    for event in ["you","quit"]:
        mode.request({"player_generation":7},state,client,9000);mode.consume(event,{},4);check(not mode.pending,"session reset")
    check(state.vitals.health_pct==0,"all requests preserve HP")
    var report:={"passed":failures.is_empty(),"checks":checks,"failures":failures,"real_server":false}
    var file:=FileAccess.open(get_script().resource_path.get_base_dir().path_join("../Reports/player_release/godot_tests.json"),FileAccess.WRITE);file.store_string(JSON.stringify(report));file.close();print(JSON.stringify(report));client.free();quit(0 if failures.is_empty() else 1)
