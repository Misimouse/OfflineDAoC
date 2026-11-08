extends SceneTree
var checks:=0
class Client:
    extends Node
    var requests:=0
    func Dismount()->void:requests+=1
func check(value:bool,label:String)->void:
    checks+=1
    if not value:push_error(label);quit(1);assert(false,label)
func _initialize()->void:
    var r=load(get_script().resource_path.get_base_dir().path_join("live_riding_state.gd")).new()
    var c:=Client.new();var ids:={20:"npc:20",30:"player:30"};var entities:={"npc:20":{"kind":"npc","health":1.0},"player:30":{"kind":"player"}}
    check(not r.request_dismount(c,0),"not mounted cannot send request")
    check(r.consume("you",{"oid":10},0) and r.local_oid==10,"local identity comes from original entry")
    var packet:={"rider":10,"steed":20,"mount":1,"slot":0}
    for key in packet:
        for bad in [null,"1",NAN,INF,-1,0.5,65536]:
            var d:=packet.duplicate();d[key]=bad;check(not r.consume("riding",d,100),"invalid unsigned packet field rejected")
    check(not r.consume("riding",{"rider":0,"steed":20,"mount":1,"slot":0},100),"zero rider rejected")
    check(not r.consume("riding",{"rider":10,"steed":0,"mount":1,"slot":0},100),"zero steed rejected")
    check(not r.consume("riding",{"rider":10,"steed":10,"mount":1,"slot":0},100),"self mount rejected")
    check(r.consume("riding",packet,100) and r.local_steed==20,"server mount acknowledged")
    var rev:int=r.revision
    check(r.consume("riding",packet,200) and r.revision==rev,"duplicate mount does not restart generation")
    check(not r.snapshot({},{}).steed_ready and r.snapshot({},{}).mounted,"mount can arrive before steed spawn")
    check(not r.unavailable({}, {},5100) and r.unavailable({}, {},5101),"missing steed has bounded grace")
    check(r.snapshot(ids,entities).steed_ready and r.snapshot(ids,entities).state_flags==0x18,"resolved mount uses original state bits")
    for hp in [0,-1,NAN,INF,"1"]:
        entities["npc:20"].health=hp;check(not r.snapshot(ids,entities).steed_ready,"dead or malformed steed cannot carry player")
    entities["npc:20"].health=1;entities["npc:20"].kind="player"
    check(not r.snapshot(ids,entities).steed_ready,"another player cannot masquerade as a mount")
    entities["npc:20"].kind="npc"

    check(r.request_dismount(c,6000) and c.requests==1 and r.local_steed==20,"dismount request does not fake acknowledgement")
    check(not r.request_dismount(c,6001) and c.requests==1,"duplicate request throttled")
    check(r.request_dismount(c,7500) and c.requests==2,"unacknowledged dismount can retry")
    check(not r.consume("riding",{"rider":10,"steed":21,"mount":0,"slot":0},7600) and r.local_steed==20,"old different-steed dismount ignored")
    check(r.consume("riding",{"rider":10,"steed":20,"mount":0,"slot":0},7600) and r.local_steed==0 and not r.pending_dismount,"actual dismount acknowledgement clears local seat")
    check(r.consume("riding",{"rider":30,"steed":20,"mount":1,"slot":1},8000) and r.local_steed==0,"remote rider cannot mount local player")
    check(r.snapshot(ids,entities).remote.size()==1,"resolved remote rider relationship exported")
    check(r.snapshot({},{}).remote.is_empty(),"unresolved remote relationship not exported")
    r.consume("remove",{"oid":99,"type":9},8100);check(r.riders.size()==1,"different ground OID cannot erase living mount")
    r.consume("remove",{"oid":20,"type":9},8100);check(r.riders.is_empty(),"original generic ObjectDelete clears deleted steed relationship")
    r.consume("riding",packet,9000);r.consume("death",{"oid":30},9100);check(r.local_steed==20,"remote death leaves local mount alone")
    r.consume("death",{"oid":10},9200);check(r.local_steed==0,"local death clears visual seat")
    for event in ["you","region_changed","quit"]:
        r.reset(10);r.consume("riding",packet,10000);r.consume(event,{"oid":10},10001)
        check(r.local_steed==0 and r.riders.is_empty(),"session boundary clears all riding state")
    r.reset(10)
    for i in range(128):r.consume("riding",{"rider":100+i,"steed":500,"mount":1,"slot":0},11000)
    check(r.riders.size()==128 and not r.consume("riding",{"rider":300,"steed":500,"mount":1,"slot":0},11001),"remote rider memory bounded")
    r.reset(10);r.consume("riding",packet,12000)
    entities["npc:20"].position_m=[100,130,100];entities["npc:20"].forward_xz=[1,0];entities["npc:20"].speed_mps=37.5
    entities["npc:20"].motion={"at_ms":12000,"interval_ms":500,"destination_m":[200,130,100]}
    check(r.speed_limit(entities,ids)==37.5,"mounted speed comes from original steed")
    check(r.position_allowed(Vector3(137.5,131.6,100),entities,ids,13000),"native saddle prediction near actual server trajectory accepted")
    check(not r.position_allowed(Vector3(500,131.6,100),entities,ids,13000),"unrelated native teleport rejected")
    check(not r.position_allowed(Vector3(137.5,160,100),entities,ids,13000),"unsupported mounted flight rejected")
    check(not r.position_allowed(Vector3(NAN,130,100),entities,ids,13000),"invalid mounted position rejected")
    entities["npc:20"].speed_mps=100;check(r.speed_limit(entities,ids)==37.5,"ground taxi original speed cap")
    entities["npc:20"].speed_mps=INF;check(r.speed_limit(entities,ids)==0,"malformed steed speed cannot accelerate player")
    check(not r.position_allowed(Vector3.ZERO,{},ids,13000),"missing steed cannot authorize mounted input")
    c.free();print(JSON.stringify({"passed":true,"checks":checks}));quit()
