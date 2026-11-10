extends SceneTree
class Client extends Node:
    var calls:Array=[]
    func Target(oid:int,flags:int)->void:calls.append(["Target",oid,flags])
    func PickUp(x:int,y:int,oid:int)->void:calls.append(["PickUp",x,y,oid])
    func Interact(oid:int,x:int,y:int)->void:calls.append(["Interact",oid,x,y])
class Server extends Node:
    var playing:=true
    var client:Node
    var entry:={"zone":207}
class Gateway extends "live_gateway.gd":
    var feedbacks:Array=[]
    func _ready()->void:pass
    func local_chat(text:String,_channel:String="help")->void:feedbacks.append(text)
var checks:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func _initialize()->void:run.call_deferred()
func run()->void:
    var folder:String=get_script().resource_path.get_base_dir()
    var gateway:=Gateway.new();root.add_child(gateway);var server:=Server.new();var client:=Client.new();server.client=client;root.add_child(server);root.add_child(client);gateway.server=server
    gateway.adapter=load(folder.path_join("decoded_world_adapter.gd")).new();gateway.adapter.zone_info={"x":35,"y":51}
    gateway.interaction=load(folder.path_join("interaction_state.gd")).new();gateway.ground_objects=load(folder.path_join("ground_object_state.gd")).new()
    gateway.player_state=load(folder.path_join("player_combat_state.gd")).new();gateway.player_state.ready=true;gateway.player_state.vitals={"alive":true};gateway.position=Vector3(1364,130,1263)
    var me:={"oid":1,"x":341280,"y":468312,"z":5200,"region":200,"model":0};gateway.ground_objects.observe("you",me);gateway.adapter.consume_world("you",me)
    var packet:={"oid":2,"x":341320,"y":468312,"z":5200,"model":488,"heading":0,"flags":0,"emblem":0,"door":-1,"name":"Private bag"};gateway.ground_objects.observe("object",packet);gateway.adapter.consume_world("object",packet)
    var token:String=gateway.ground_objects.objects["object:2"].object_token;var generation:int=gateway.ground_objects.generation
    var select:={"action":"target_object","entity_id":"object:2","object_token":token,"world_generation":generation};gateway.command(select)
    check(client.calls==[["Target",2,0xE000]] and gateway.interaction.selected_id=="object:2","actual gateway click selects without pickup")
    gateway.interaction.maintain(client,gateway.ground_objects.entities(gateway.adapter.entities),gateway.position);check(gateway.interaction.selected_id=="object:2","living target maintenance retains a current ground target")
    check(gateway.interaction.snapshot(gateway.ground_objects.entities(gateway.adapter.entities),gateway.position).target.kind=="object","existing target UI receives actual ground target name and identity")
    client.calls.clear();var get:Dictionary=select.duplicate();get.action="get_object";gateway.command(get);check(client.calls==[["Target",2,0xE000],["PickUp",341280,468312,2]],"actual gateway forwards original pickup coordinates and pins target")
    check(gateway.ground_objects.objects.has("object:2"),"gateway does not remove object before server deletion")
    client.calls.clear();get.object_token="old";gateway.command(get);check(client.calls.is_empty() and not gateway.feedbacks.is_empty(),"actual gateway refuses stale identity and provides feedback")
    get.object_token=token;gateway.player_state.vitals={"alive":false};gateway.command(get);check(client.calls.is_empty(),"actual gateway refuses dead pickup")
    gateway.player_state.vitals={"alive":true};gateway.leaving=true;gateway.command(get);check(client.calls.is_empty(),"actual gateway refuses logout pickup")
    gateway.leaving=false;server.playing=false;gateway.command(get);check(client.calls.is_empty(),"actual gateway refuses lobby pickup")
    server.playing=true;server.entry.zone=206;gateway.command(get);check(client.calls.is_empty(),"actual gateway refuses wrong-zone pickup")
    server.entry.zone=207;gateway.command({"action":"target_loot","world_generation":generation});check(client.calls==[["Target",2,0xE000]],"actual nearest-loot route only selects")
    gateway.ground_objects.observe("remove",{"oid":2,"type":9});gateway.interaction.maintain(client,gateway.ground_objects.entities(gateway.adapter.entities),gateway.position);check(gateway.interaction.selected_id.is_empty(),"server deletion clears selected ground target through ordinary maintenance")
    var living:={"oid":3,"session":17,"x":341280,"y":468312,"z":5200,"heading":0,"model":318,"name":"Old player","level":10,"flags":12};gateway.adapter.consume_world("player",living)
    check(gateway.adapter.entities.has("player:3"),"adapter initially holds a living identity")
    packet.oid=3;gateway.adapter.consume_world("object",packet);check(not gateway.adapter.entities.has("player:3") and not gateway.adapter.oid_to_id.has(3),"decoded object reuse removes previous living body")
    var transport=load(folder.path_join("visual_bridge.gd")).new();transport.snapshot_metadata={"world_objects":{"generation":generation,"objects":gateway.ground_objects.view(gateway.position)}};check(transport.publish([],207,"isolated-ground") and transport.last_snapshot.has("world_objects"),"transport carries independently bounded ground metadata without consuming NPC entity budget")
    transport.free();gateway.adapter.free();gateway.queue_free();server.queue_free();client.queue_free()
    print(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures,"real_server":false}));quit(0 if failures.is_empty() else 1)
