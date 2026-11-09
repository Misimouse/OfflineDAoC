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
    var me:={"oid":1,"x":341280,"y":468312,"z":5200,"region":200,"model":0}
    a.consume_world("you",me)
    var spawn:={"oid":2,"session":17,"x":341280,"y":468312,"z":5200,"heading":0,"model":318,"name":"Other player","level":10,"flags":12}
    a.consume_world("player",spawn)
    var id:="player:2";var row:Dictionary=a.entities[id]
    check(row.realm==3 and row.session_id==17,"original player create realm and session")
    var packet:={"oid":2,"session":17,"zone":207,"x":341320.0,"y":468352.0,"z":5240.0,"speed":240.0,"speed_z":0.0,"heading":1024,"state_flags":0,"action_flags":0x80,"health":70,"combat_active":true}
    a.consume_world("player_move",packet)
    check(row.position_m==[1365.0,131.0,1264.0],"absolute region floats converted once")
    check(is_equal_approx(row.speed_mps,6) and row.state=="run" and row.health==.7,"signed speed and health decoded")
    check(row.torch_on and not row.diving and not row.stealthed and row.combat_active,"output action flag meanings")
    check(row.motion.source_packet=="player_position1127" and not row.motion.has("destination_m"),"reuse interpolation without inventing a waypoint")
    var seq:int=row.motion.seq;a.consume_world("player_move",packet);check(row.motion.seq>seq,"new actual packet advances sample identity")
    var before:Array=row.position_m.duplicate();var changed:Dictionary=packet.duplicate();changed.session=18;changed.x+=400
    a.consume_world("player_move",changed);check(row.position_m==before,"stale reused object session ignored")
    changed=packet.duplicate();changed.oid=1;a.consume_world("player_move",changed);check(a.entities["player:local"].position_m==[1364.0,130.0,1263.0],"remote packet never moves local player")
    for key in ["x","speed","speed_z","heading","oid","session","zone","health","state_flags","action_flags"]:
        for value in [NAN,INF,"1",null]:
            changed=packet.duplicate();changed[key]=value;var count:int=a.motion_sequence;a.consume_world("player_move",changed);check(a.motion_sequence==count,"invalid remote field:"+key)
    for spec in [["health",101],["state_flags",256],["action_flags",256],["session",17.5],["zone",207.5]]:
        changed=packet.duplicate();changed[spec[0]]=spec[1];var count:int=a.motion_sequence;a.consume_world("player_move",changed);check(a.motion_sequence==count,"out of range remote field")
    changed=packet.duplicate();changed.heading=0;changed.speed=-160.0;a.consume_world("player_move",changed)
    check(row.state=="walk_back" and row.motion.direction_xz==[0.0,-1.0] and row.motion.speed_mps==4.0,"backwards prediction does not turn the body")
    changed.speed=160.0;changed.state_flags=0x40;a.consume_world("player_move",changed);check(row.motion.direction_xz==[-1.0,0.0],"left strafe prediction")
    changed.state_flags=0x80;a.consume_world("player_move",changed);check(row.motion.direction_xz==[1.0,0.0],"right strafe prediction")
    changed.speed=0.0;changed.state_flags=0x10;a.consume_world("player_move",changed);check(row.remote_sitting and row.state=="sit_idle" and not row.remote_swimming,"seated pose is not swimming death")
    changed.state_flags=4;changed.action_flags=4;a.consume_world("player_move",changed);check(row.remote_swimming and row.diving and not row.stealthed and row.state=="swim","swimming and outgoing diving")
    changed.action_flags=2;a.consume_world("player_move",changed);check(row.stealthed and not row.diving,"outgoing stealth does not mean diving")
    changed.state_flags=28;changed.speed_z=-85.0;a.consume_world("player_move",changed);check(row.remote_climbing and not row.remote_sitting and row.state=="ladder" and row.remote_ladder_rate==-1.0,"climbing state and original reverse ladder rate")
    var facing:Array=row.forward_xz.duplicate();changed.state_flags=24;changed.heading=40000;a.consume_world("player_move",changed);check(row.remote_riding and row.state=="ride_horse" and row.forward_xz==facing,"steed object ID is not a facing angle")
    changed.state_flags=0;changed.health=0;a.consume_world("player_move",changed);check(row.state=="dead" and row.health==0,"actual zero HP produces death")
    changed.health=100;changed.heading=0;changed.speed=0.0;a.consume_world("player_move",changed);check(row.state=="idle" and row.health==1.0,"server revive state restores living pose")
    changed.zone=208;a.consume_world("player_move",changed);check(not a.entities.has(id),"leaving delivered zone removes remote identity")
    a.consume_world("player",spawn);changed=packet.duplicate();changed.x=1.0;a.consume_world("player_move",changed);check(not a.entities.has(id),"outside current region point removes stale player")
    a.consume_world("player",spawn);a.consume_world("quit",{});check(a.entities.is_empty() and a.oid_to_id.is_empty(),"logout clears remote identities")
    var requests:Array=[];var object_requests:Array=[]
    a.missing_player.connect(func(session):requests.append(session))
    a.missing_entity.connect(func(oid):object_requests.append(oid))
    changed=packet.duplicate();changed.oid=44;changed.session=123
    a.consume_world("player_move",changed)
    check(requests==[123] and object_requests.is_empty(),"unknown player requests original session, never static OID")
    a.consume_world("player_move",changed)
    check(requests==[123],"repeated missing player requests throttled")
    a.clear_world();a.consume_world("player_move",changed)
    check(requests==[123,123],"new login clears player-request throttle")
    a.free()
    var result:={"passed":failures.is_empty(),"checks":checks,"failures":failures}
    FileAccess.open(folder.path_join("state_tests.json"),FileAccess.WRITE).store_string(JSON.stringify(result))
    print(JSON.stringify(result));quit(0 if failures.is_empty() else 1)
