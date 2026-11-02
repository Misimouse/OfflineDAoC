extends SceneTree
class Client extends Node:
    var packets:Array=[]
    func Position(a,b,c,d,e,f,g,h,i,j,k,l):packets.append([a,b,c,d,i])
class FakeServer extends Node:
    var client:Node
    var playing:=true
    var entry:Dictionary={"zone":207}
    var max_speed_pct:=100
    var me_oid:=4
    var commands:Array=[]
    func command(text:String):commands.append(text)
class Selection extends RefCounted:
    var selected_id:=""
class Adapter extends Node:
    var entities:Dictionary={}
var checks:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func _initialize()->void:
    var gateway=load("res://live_gateway.gd").new();var server:=FakeServer.new();var client:=Client.new();server.client=client;gateway.server=server
    gateway.classic_ui=load("res://classic_ui_state.gd").new()
    gateway.player_state=load("res://player_combat_state.gd").new();gateway.player_state.ready=true;gateway.player_state.vitals={"health_pct":0};gateway.position=Vector3(1300,130,1200);gateway.heading=777;gateway.last_position_send=Time.get_ticks_msec()
    var original:Vector3=gateway.position
    gateway.command({"action":"move","position_m":[1300,130,1200],"forward_xz":[1,0],"speed_mps":0})
    check(gateway.heading==777,"dead same-position camera packet cannot rotate server heading")
    check(gateway.position==original and client.packets.is_empty(),"dead same-position packet does not move or transmit")
    gateway.command({"action":"move","position_m":[1300.05,130,1200],"forward_xz":[0,-1],"speed_mps":0})
    check(gateway.position==original and gateway.heading==777,"dead small movement cannot drift corpse")
    gateway.command({"action":"chat","text":"/release"});check(server.commands==["/release"],"dead player can use original release command through chat")
    for text in ["bad\ncommand","bad\rcommand","a".repeat(241)]:gateway.command({"action":"chat","text":text})
    check(server.commands.size()==1,"gateway rejects multiline and overlong chat")
    var adapter:=Adapter.new();gateway.adapter=adapter;gateway.interaction=Selection.new();gateway.player_state.vitals.health_pct=25
    gateway.command({"action":"move","position_m":[1300.05,130,1200],"forward_xz":[1,0],"speed_mps":0})
    check(gateway.heading!=777 and client.packets.size()==1,"authoritative positive health restores live movement")
    var transport=load("res://visual_bridge.gd").new();transport.snapshot_metadata={"messages":["Server reply"]};transport.publish([]);check(transport.last_snapshot.get("messages",[])==["Server reply"],"server replies included in actual bridge frame");transport.free()
    var report:={"passed":failures.is_empty(),"checks":checks,"failures":failures,"real_server":false}
    var file:=FileAccess.open(get_script().resource_path.get_base_dir().path_join("../Reports/chat_death_fix/godot_tests.json"),FileAccess.WRITE);file.store_string(JSON.stringify(report));file.close();print(JSON.stringify(report));gateway.free();adapter.free();server.free();client.free();quit(0 if failures.is_empty() else 1)
