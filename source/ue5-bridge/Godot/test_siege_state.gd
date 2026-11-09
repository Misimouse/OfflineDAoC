extends SceneTree
class Client extends Node:
    var calls:Array=[]
    func SiegeCommand(action:int,ammo:int)->void:calls.append([action,ammo])
var checks:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func packet()->Dictionary:
    return {"oid":37,"ammo_type":24,"time":50,"action":2,"ammo_slot":20,"effect":2202,"can_move":true,"name":"Field ballista (Inactive)","ammo":[{"index":2,"level":1,"object_type":45,"count":4,"model":12,"name":"Ballista bolt"}]}
func command(state:RefCounted,id:int=2,ammo:int=0)->Dictionary:
    return {"action":"siege_command","oid":37,"revision":state.revision,"command":id,"ammo":ammo}
func _initialize()->void:run.call_deferred()
func run()->void:
    var state=load(get_script().resource_path.get_base_dir().path_join("siege_state.gd")).new();var client:=Client.new()
    check(not state.snapshot(0).controlled,"no control without server grant")
    check(not state.request(command(state),client,true,1000),"no commands without control")
    check(not state.consume("siege_anim",packet(),0),"nearby animations do not grant control")
    check(state.consume("siege_window",packet(),1000) and state.visible,"original interface grants control")
    check(is_equal_approx(state.snapshot(2500).time_left,3.5),"presentation timer uses original tenths")
    check(state.snapshot(9000).weapon.action==2 and state.snapshot(9000).time_left==0,"elapsed timer does not invent readiness")
    for spec in [["oid",0],["oid",65536],["oid",true],["time",256],["action",5],["ammo_type",-1],["effect",1.5],["can_move",1],["name",""]]:
        var bad:=packet();bad[spec[0]]=spec[1];var before:Dictionary=state.snapshot(1000)
        check(not state.consume("siege_window",bad,1200) and state.snapshot(1000)==before,"reject malformed interface %s"%str(spec))
    var bad:=packet();bad.ammo.append(bad.ammo[0].duplicate());check(not state.consume("siege_window",bad,1200),"duplicate ammo index rejected atomically")
    check(not state.request(command(state),client,false,2000),"lobby cannot send siege commands")
    var stale:=command(state);stale.oid=38;check(not state.request(stale,client,true,2000),"wrong controlled weapon rejected")
    stale=command(state);stale.revision-=1;check(not state.request(stale,client,true,2000),"stale window revision rejected")
    for id in [0,11,1.5,true,"2",NAN]:
        var invalid:=command(state);invalid.command=id;check(not state.request(invalid,client,true,2000),"invalid command %s"%str(id))
    check(not state.request(command(state,1,1),client,true,2000),"LOAD cannot invent ammunition")
    check(state.request(command(state,1,2),client,true,2000) and client.calls.back()==[1,2],"LOAD preserves original ammunition index")
    check(not state.request(command(state,4),client,true,2001),"duplicate command rate bounded")
    for id in [2,3,4,5,6,7,8,9,10]:check(state.request(command(state,id),client,true,3000+id*200) and client.calls.back()==[id,0],"original command identity %d"%id)
    check(state.snapshot(7000).controlled,"RELEASE request cannot fabricate server close")
    var no_move:=packet();no_move.can_move=false;state.consume("siege_window",no_move,8000)
    check(not state.request(command(state,5),client,true,9000),"server immobility disables MOVE")
    check(not state.request(command(state,2,2),client,true,9000),"ammo only permitted for LOAD")
    var view:Dictionary=state.snapshot(9000);view.weapon.ammo.clear();check(state.current.ammo.size()==1,"UI snapshot cannot alter ammunition cache")
    var hide:={"action":"siege_hide","oid":37,"revision":state.revision};var count:=client.calls.size()
    check(state.request(hide,client,true,9000) and not state.visible and state.snapshot(9000).controlled and client.calls.size()==count,"close hides without implicitly releasing server control")
    for event in ["siege_close","you","quit","region_changed"]:
        state.consume("siege_window",packet(),10000);check(state.consume(event,{},11000) and not state.snapshot(11000).controlled and not state.visible,"server/session reset %s"%event)
    print(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures,"real_server":false}));client.free();quit(0 if failures.is_empty() else 1)
