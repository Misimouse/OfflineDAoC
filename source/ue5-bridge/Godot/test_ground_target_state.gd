extends SceneTree
class Client extends Node:
    var calls:Array=[]
    func GroundTarget(x:int,y:int,z:int,flag:int)->void:calls.append([x,y,z,flag])
class Server extends Node:
    var playing:=true
    var client:Node
    var entry:Dictionary={"zone":207}
    func to_region(_zone:int,p:Vector3)->Vector3:return Vector3(p.x*40+35*8192,p.z*40+51*8192,p.y*40)
var checks:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func request(point:Variant=[1365.0,130.0,1264.0],seen:Variant=true)->Dictionary:return {"action":"ground_target","position_m":point,"visible":seen}
func _initialize()->void:run.call_deferred()
func run()->void:
    var state=load(get_script().resource_path.get_base_dir().path_join("ground_target_state.gd")).new();var client:=Client.new();var server:=Server.new();server.client=client;var position:=Vector3(1364,130,1263)
    check(not state.snapshot(0).has_point and state.flags(0)==0,"no invented ground target or visibility")
    server.playing=false;check(not state.request(request(),server,position,1000),"lobby cannot set a world ground target");server.playing=true
    for raw in [[],[1,2],[NAN,130,1264],[1365,INF,1264],[true,130,1264],["1365",130,1264],[2000,130,1264]]:check(not state.request(request(raw),server,position,1000),"invalid or out-of-range point %s"%str(raw))
    check(not state.request(request([1365,130,1264],1),server,position,1000),"visibility must be a boolean")
    check(state.request(request(),server,position,1000) and client.calls.back()==[341320,468352,5200,256],"point round trip uses original server region conversion")
    check(state.flags(1000)==8 and state.flags(2500)==8 and state.flags(2501)==0,"ground visibility expires independently of selected-object visibility")
    check(not state.request(request(),server,position,1001) and client.calls.size()==1,"duplicate ground input rate bounded")
    check(not state.snapshot(1000).server_acknowledged,"marker does not invent server navigation acknowledgement")
    var rev:int=state.revision
    check(not state.update_visibility({"ground_target_revision":rev-1,"ground_target_in_view":true},2600),"stale ground point cannot receive another point visibility")
    check(not state.update_visibility({"ground_target_revision":true,"ground_target_in_view":true},2600),"boolean revision is not accepted")
    check(not state.update_visibility({"ground_target_revision":rev,"ground_target_in_view":1},2600),"malformed geometry visibility refused")
    check(state.update_visibility({"ground_target_revision":rev,"ground_target_in_view":true},2600) and state.flags(2600)==8,"fresh geometry report restores only ground visibility")
    check(state.update_visibility({"ground_target_revision":rev,"ground_target_in_view":false},2700) and state.flags(2700)==0,"wall clears ground target visibility")
    check(state.flags(2500)==0,"time reversal cannot make a later geometry result visible")
    check(state.request(request([1365,130,1264],false),server,position,3000) and client.calls.back()[3]==0,"out-of-view point retains original flag semantics")
    server.entry={"zone":-1};check(not state.request(request(),server,position,4000),"missing current zone refused");server.entry={"zone":207}
    var view:Dictionary=state.snapshot(4000);view.position_m.clear();check(state.snapshot(4000).position_m.size()==3,"UI snapshot cannot clear the current point")
    for event in ["you","quit","region_changed"]:
        state.request(request(),server,position,5000);state.consume(event);check(not state.snapshot(5000).has_point and state.flags(5000)==0,"ground target resets on %s"%event)
    print(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures,"real_server":false}));server.free();client.free();quit(0 if failures.is_empty() else 1)
