extends SceneTree
var checks:=0
class Client:
    extends Node
    var requests:=0
    var position_state:=-1
    var heading_state:=-1
    func Position(_x:float,_y:float,_z:float,_speed:float,_vertical:float,_zone:int,state:int,_ground:bool,_heading:int,_flags:int,_health:int,_oid:int)->void:position_state=state
    func Heading(_heading:int,_oid:int,_flags:int,state:int)->void:heading_state=state
    func Dismount()->void:requests+=1
class UI:
    extends RefCounted
    func create_macro(_text:String)->bool:return false
class Adapter:
    extends Node
    var entities:Dictionary={}
class Interaction:
    extends RefCounted
    var selected_id:=""
class Player:
    extends "res://player_combat_state.gd"
class Server:
    extends Node
    var client:Node
    var me_oid:=10
func check(value:bool,label:String)->void:
    checks+=1
    if not value:push_error(label);quit(1);assert(false,label)
func _initialize()->void:
    var folder:String=get_script().resource_path.get_base_dir()
    var script:Script=load(folder.path_join("live_gateway.gd"))
    check(script!=null and script.can_instantiate(),"complete gateway parses with riding module")
    var gateway:Node=script.new();var server:=Server.new();var client:=Client.new();server.client=client;gateway.server=server;gateway.classic_ui=UI.new()
    gateway.live_riding=load(folder.path_join("live_riding_state.gd")).new()
    gateway.live_riding.reset(10);gateway.live_riding.consume("riding",{"rider":10,"steed":20,"mount":1,"slot":0},0)
    check(not gateway.dispatch_chat("/dismount\n/quit") and client.requests==0,"line injection rejected before mounted command")
    check(gateway.dispatch_chat("/DiSmOuNt") and client.requests==1,"original dismount dispatch uses protocol request")
    check(gateway.live_riding.local_steed==20,"chat command cannot fake unmount acknowledgement")
    check(gateway.dispatch_chat("/dismount") and client.requests==1,"duplicate chat cannot flood protocol")
    var adapter:=Adapter.new();gateway.adapter=adapter;gateway.interaction=Interaction.new();gateway.player_state=Player.new()
    gateway.movement_flags=load(folder.path_join("movement_flags_state.gd")).new();gateway.movement_flags.swimming=true
    gateway.send_position(0);gateway.sync_attack_visibility()
    check(client.position_state==0x18 and client.heading_state==0x18,"both original position and heading carry server-confirmed riding bits")
    gateway.live_riding.consume("riding",{"rider":10,"steed":20,"mount":0,"slot":0},1);gateway.send_position(0)
    check(client.position_state==0x04,"unmount ACK restores ordinary movement flags")
    gateway.movement_flags.reset();gateway.send_position(0);check(client.position_state==0,"ground movement flag remains original after reset")
    adapter.free();    gateway.free();server.free();client.free();print(JSON.stringify({"passed":true,"checks":checks}));quit()
