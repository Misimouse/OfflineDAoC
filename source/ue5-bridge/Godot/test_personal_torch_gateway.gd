extends SceneTree
var checks:=0
var failures:Array=[]
class Client extends Node:
    var positions:Array=[]
    var headings:Array=[]
    func Position(_x:float,_y:float,_z:float,_s:float,_v:float,_zone:int,_state:int,_floor:bool,_h:int,flags:int,_hp:int,_oid:int)->void:positions.append(flags)
    func Heading(_h:int,_oid:int,flags:int,_state:int)->void:headings.append(flags)
class Server extends Node:
    var client:Node
    var playing:=true
    var me_oid:=10
    var entry:Dictionary={"zone":207}
class Interaction extends RefCounted:
    var selected_id:=""
class Adapter extends Node:
    var entities:Dictionary={}
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func _initialize()->void:
    var folder:String=get_script().resource_path.get_base_dir()
    var gateway:Node=load(folder.path_join("live_gateway.gd")).new()
    var server:=Server.new();var client:=Client.new();server.client=client;gateway.server=server
    gateway.personal_torch=load(folder.path_join("personal_torch_state.gd")).new()
    gateway.player_state=load(folder.path_join("player_combat_state.gd")).new()
    gateway.movement_flags=load(folder.path_join("movement_flags_state.gd")).new()
    gateway.ground_target=load(folder.path_join("ground_target_state.gd")).new()
    gateway.live_riding=load(folder.path_join("live_riding_state.gd")).new()
    gateway.interaction=Interaction.new();var adapter:=Adapter.new();gateway.adapter=adapter
    gateway.send_position(0);gateway.sync_attack_visibility()
    check(client.positions.back()==0x80 and client.headings.back()==0x80,"both original packet APIs include default torch")
    gateway.player_state.ready=true
    var generation:int=gateway.player_state.generation
    gateway.command({"action":"personal_torch","on":false,"player_generation":generation})
    gateway.sync_attack_visibility()
    check(client.positions.back()==0 and client.headings.back()==0,"toggle immediately reaches position and next heading")
    var n:int=client.positions.size()
    for request in [{"on":true,"player_generation":generation-1},{"on":1,"player_generation":generation},{"on":true,"player_generation":true}]:
        request.action="personal_torch";gateway.command(request)
    check(client.positions.size()==n and not gateway.personal_torch.enabled,"malformed or stale generation cannot toggle")
    server.playing=false;gateway.command({"action":"personal_torch","on":true,"player_generation":generation})
    check(not gateway.personal_torch.enabled,"lobby cannot toggle personal torch")
    server.playing=true;gateway.command({"action":"personal_torch","on":true,"player_generation":generation})
    check(client.positions.back()==0x80,"next valid request restores torch")
    for flags in range(256):check((gateway.personal_action_flags(flags)&~0x80)==(flags&~0x80),"preserve other position/heading bits")
    gateway.free();adapter.free();server.free();client.free()
    print(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures,"real_server":false}));quit(0 if failures.is_empty() else 1)
