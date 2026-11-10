extends SceneTree
class Inventory extends RefCounted:
    var inventory_events:=1
    var fingerprint:="ready"
    var pending:Dictionary={}
    var state_revision:=5
    var items:Dictionary={10:{"token":"a"},12:{"token":"b"},13:{"token":"c"}}
    var weapon_set:="standard"
class PlayerState extends RefCounted:
    var ready:=true
    var generation:=7
    var dead:=false
    func alive()->bool:return not dead
var checks:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func _initialize()->void:
    call_deferred("run")
func run()->void:
    var folder:String=get_script().resource_path.get_base_dir()
    var state=load(folder.path_join("weapon_sprint_state.gd")).new()
    var server=load(folder.path_join("original_weapon_reference.gd")).new();root.add_child(server)
    var pose=load(folder.path_join("ui_player_pose.gd")).new();root.add_child(pose)
    pose.global_position=Vector3(12,13,14);pose.heading=321
    var inv:=Inventory.new();var player:=PlayerState.new();var now:=1000
    var before:Dictionary=inv.items.duplicate(true)
    for spec in [["standard",10,"a"],["twohand",12,"b"],["ranged",13,"c"]]:
        var value:={"action":"weapon_select","mode":spec[0],"player_generation":7,"inventory_revision":5,"item_token":spec[2]}
        check(state.request(value,server,inv,player,pose,207,now),"current original weapon request")
        check(server.slots[-1][6]==spec[1] and server.slots[-1][7]==0,"actual original switch_weapon chooses UseSlot slot and type")
        check(server.slots[-1][0]==12 and server.slots[-1][1]==13 and server.slots[-1][2]==14,"original switch uses pose position")
        check(not state.request(value,server,inv,player,pose,207,now+100),"repeat key is bounded")
        check(inv.weapon_set=="standard" and inv.items==before,"request does not fabricate acknowledged equipment")
        # A different weapon set is legitimate immediately after acknowledgement.
        # Repetition of the same request alone is throttled.
    var sprint:={"action":"player_sprint","player_generation":7}
    check(state.request(sprint,server,inv,player,pose,207,now),"original sprint command requested")
    check(server.commands==["/sprint"],"only original DOL-authorized command sent")
    now+=300
    for epoch in [null,6,8,7.1,NAN,INF,"7",true,[],{}]:
        var value:Dictionary=sprint.duplicate();value.player_generation=epoch
        check(not state.request(value,server,inv,player,pose,207,now),"malformed or stale character")
    player.ready=false;check(not state.request(sprint,server,inv,player,pose,207,now),"loading character");player.ready=true
    player.dead=true;check(not state.request(sprint,server,inv,player,pose,207,now),"dead player");player.dead=false
    server.playing=false;check(not state.request(sprint,server,inv,player,pose,207,now),"lobby");server.playing=true
    check(not state.request(sprint,server,inv,player,pose,208,now),"unavailable zone")
    check(not state.request(sprint,server,inv,player,null,207,now),"missing pose")
    var weapon:={"action":"weapon_select","mode":"twohand","player_generation":7,"inventory_revision":5,"item_token":"b"}
    for mode in [null,10,"plate","STANDARD",true,[],{}]:
        var value:Dictionary=weapon.duplicate();value.mode=mode
        check(not state.request(value,server,inv,player,pose,207,now),"invalid weapon mode")
    for rev in [null,4,6,5.1,NAN,INF,"5",true]:
        var value:Dictionary=weapon.duplicate();value.inventory_revision=rev
        check(not state.request(value,server,inv,player,pose,207,now),"invalid or stale inventory")
    for token in [null,"","a",true,12]:
        var value:Dictionary=weapon.duplicate();value.item_token=token
        check(not state.request(value,server,inv,player,pose,207,now),"replaced item token")
    inv.pending={"op":"move"};check(not state.request(weapon,server,inv,player,pose,207,now),"pending inventory operation");inv.pending={}
    inv.inventory_events=0;check(not state.request(weapon,server,inv,player,pose,207,now),"missing server inventory");inv.inventory_events=1
    inv.fingerprint="";check(not state.request(weapon,server,inv,player,pose,207,now),"incomplete inventory");inv.fingerprint="ready"
    inv.items.erase(12);check(not state.request(weapon,server,inv,player,pose,207,now),"empty weapon slot");inv.items=before
    check(server.slots.size()==3 and server.commands.size()==1,"all rejected requests leave transport untouched")
    state.reset();check(state.request(sprint,server,inv,player,pose,207,0),"new session resets old request time")
    var result:={"passed":failures.is_empty(),"checks":checks,"failures":failures,"installed":false,"original_switch_weapon_executed":true,"real_server":false}
    FileAccess.open(folder.path_join("state_tests.json"),FileAccess.WRITE).store_string(JSON.stringify(result));print(JSON.stringify(result));quit(0 if failures.is_empty() else 1)
