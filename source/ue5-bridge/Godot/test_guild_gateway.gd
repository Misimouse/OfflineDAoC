extends SceneTree
class Server extends Node:
    var playing:=true
    var info:Dictionary={"guild":"QA Guild"}
    var commands:Array=[]
    func command(text:String)->void:commands.append(text)
    func class_name_of(id:int)->String:return "Class %d" % id
var checks:=0
var failures:Array=[]
func check(value:bool,label:String)->void:
    checks+=1
    if not value:failures.append(label)
func _initialize()->void:
    var script:Script=load("res://live_gateway.gd")
    check(script!=null and script.can_instantiate(),"full original gateway parses with guild integration")
    var gateway:Node=script.new();var server:=Server.new();gateway.server=server;gateway.character_name="QaPlayer";gateway.guild_state=load("res://guild_state.gd").new()
    gateway.command({"action":"guild_open","open":true})
    check(server.commands==["/gc who window 1 1 0"],"real gateway routes guild open through original server command")
    var state:RefCounted=gateway.guild_state;state.consume("message",{"type":0x64,"text":"TE,1,1,1"},server,100);state.consume("message",{"type":0x64,"text":'E,1,1,QaOak,10,42,2,1,"Connacht","Guard"'},server,100)
    var token:String=state.token
    gateway.command({"action":"guild_info","guild_token":token})
    check(server.commands.back()=="/gc info","real gateway routes guild info")
    gateway.command({"action":"guild_motd","guild_token":token})
    check(server.commands.back()=="/gc motd","real gateway routes MOTD")
    var before:=server.commands.size()
    gateway.command({"action":"guild_member","guild_token":token,"member_token":state.members[0].token,"verb":"remove"})
    check(server.commands.size()==before,"gateway never bypasses removal confirmation")
    gateway.leaving=true;gateway.command({"action":"guild_info","guild_token":token})
    check(server.commands.size()==before,"logout boundary suppresses guild commands")
    gateway.leaving=false;server.playing=false;gateway.command({"action":"guild_info","guild_token":token})
    check(server.commands.size()==before,"character menu cannot send in-world guild commands")
    var bridge:Node=load("res://visual_bridge.gd").new();bridge.snapshot_metadata={"guild":state.snapshot()}
    check(bridge.publish([],207,"guild-test"),"original transport publishes bounded guild state")
    check(bridge.last_snapshot.guild.guild=="QA Guild" and bridge.last_snapshot.guild.members.size()==1,"guild payload is preserved across actual snapshot contract")
    check(not bridge.publish([],999,"guild-test"),"guild work cannot widen allowed world zone")
    gateway.free();server.free();bridge.free();print(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures}));quit(0 if failures.is_empty() else 1)
