extends SceneTree
class Client extends RefCounted:
    var calls:Array=[]
    func EmblemChoice(a:int,b:int,c:int,d:int)->void:calls.append([a,b,c,d])
class Server extends Node:
    var playing:=true
    var info:Dictionary={"guild":"QA Guild"}
    var client:RefCounted=Client.new()
var checks:=0
var failures:Array=[]
func check(value:bool,label:String)->void:
    checks+=1
    if not value:failures.append(label)
func _initialize()->void:
    var script:Script=load("res://live_gateway.gd");check(script!=null and script.can_instantiate(),"full gateway parses with original emblem integration")
    var gateway:Node=script.new();var server:=Server.new();gateway.server=server;gateway.character_name="QaPlayer";gateway.emblem_picker=load("res://emblem_picker_state.gd").new()
    var state:RefCounted=gateway.emblem_picker;state.sync(server,"QaPlayer")
    gateway.command({"action":"emblem_submit","token":""});check(server.client.calls.is_empty(),"gateway cannot submit before original server dialogue")
    state.consume("emblem_dialog",{},server,[]);var tok:String=state.token
    gateway.command({"action":"emblem_select","token":tok,"logo":255,"primary":15,"secondary":7,"pattern":3})
    check(state.snapshot().emblem==131071 and server.client.calls.is_empty(),"gateway updates preview without sending a server choice")
    gateway.leaving=true;gateway.command({"action":"emblem_submit","token":tok});check(server.client.calls.is_empty(),"logout boundary prevents emblem purchase request")
    gateway.leaving=false;server.playing=false;gateway.command({"action":"emblem_submit","token":tok});check(server.client.calls.is_empty(),"character menu prevents emblem request")
    server.playing=true;gateway.command({"action":"emblem_submit","token":"stale"});check(server.client.calls.is_empty(),"gateway retains picker token guard")
    gateway.command({"action":"emblem_submit","token":tok});check(server.client.calls==[[15,7,3,255]],"actual route uses existing four-byte EmblemChoice API")
    gateway.command({"action":"emblem_submit","token":tok});check(server.client.calls.size()==1,"closed picker cannot submit twice")
    state.consume("emblem_dialog",{},server,[]);gateway.command({"action":"emblem_close","token":state.token});check(not state.visible and server.client.calls.size()==1,"actual close route cancels without another packet")
    var bridge:Node=load("res://visual_bridge.gd").new();bridge.snapshot_metadata={"emblem_picker":state.snapshot()}
    check(bridge.publish([],207,"emblem-qa"),"existing transport accepts emblem metadata in supported zone")
    check(bridge.last_snapshot.has("emblem_picker") and bridge.last_snapshot.emblem_picker.guild=="QA Guild","actual snapshot preserves picker state")
    check(not bridge.publish([],999,"emblem-qa"),"emblem integration does not widen world-zone authority")
    gateway.free();server.free();bridge.free();print(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures}));quit(0 if failures.is_empty() else 1)
