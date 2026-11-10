extends SceneTree
class Gateway extends "live_gateway.gd":
    var inventory_syncs:=0
    func _ready()->void:pass
    func sync_inventory(_now:int)->void:inventory_syncs+=1
var checks:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func _initialize()->void:call_deferred("run")
func run()->void:
    var folder:String=get_script().resource_path.get_base_dir()
    var gateway:=Gateway.new();root.add_child(gateway)
    var server=load(folder.path_join("original_weapon_reference.gd")).new();root.add_child(server);gateway.server=server
    gateway.weapon_sprint=load(folder.path_join("weapon_sprint_state.gd")).new()
    gateway.player_state=load(folder.path_join("player_combat_state.gd")).new();gateway.player_state.ready=true;gateway.player_state.generation=7;gateway.player_state.vitals={"alive":true}
    gateway.inventory=load(folder.path_join("inventory_state.gd")).new();gateway.inventory.inventory_events=1;gateway.inventory.fingerprint="ready";gateway.inventory.state_revision=5;gateway.inventory.items={12:{"token":"staff"}}
    gateway.ui_pose=load(folder.path_join("ui_player_pose.gd")).new();root.add_child(gateway.ui_pose)
    gateway.position=Vector3(12,13,14);gateway.heading=321
    gateway.command({"action":"weapon_select","mode":"twohand","item_token":"staff","inventory_revision":5,"player_generation":7})
    check(server.slots.size()==1 and server.slots[0][6]==12,"actual gateway dispatches original weapon packet")
    check(gateway.ui_pose.global_position==gateway.position and gateway.ui_pose.heading==321,"gateway refreshes authoritative pose")
    check(gateway.inventory_syncs==1 and gateway.inventory.weapon_set=="standard","gateway refreshes inventory without optimistic switch")
    gateway.weapon_sprint.reset();gateway.command({"action":"player_sprint","player_generation":7})
    check(server.commands==["/sprint"],"actual gateway sends original sprint command")
    gateway.weapon_sprint.reset();gateway.command({"action":"weapon_select","mode":"twohand","item_token":"old","inventory_revision":5,"player_generation":7})
    check(server.slots.size()==1,"actual gateway refuses replaced item")
    gateway.player_state.vitals={"alive":false};gateway.command({"action":"player_sprint","player_generation":7})
    check(server.commands.size()==1,"actual gateway refuses dead sprint")
    gateway.player_state.vitals={"alive":true};gateway.leaving=true;gateway.command({"action":"player_sprint","player_generation":7})
    check(server.commands.size()==1,"actual gateway refuses logout sprint")
    gateway.leaving=false;server.playing=false;gateway.command({"action":"player_sprint","player_generation":7})
    check(server.commands.size()==1,"actual gateway refuses lobby sprint")
    gateway.ui_pose.queue_free();gateway.queue_free();server.queue_free()
    print(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures,"real_server":false}));quit(0 if failures.is_empty() else 1)
