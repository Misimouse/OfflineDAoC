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
    var state=load("res://emblem_picker_state.gd").new();var server:=Server.new()
    state.sync(server,"QaPlayer")
    check(not state.visible and server.client.calls.is_empty(),"membership never opens the picker or sends a packet")
    check(not state.request({"action":"emblem_submit","token":""},server),"unsolicited submit cannot bypass server dialogue")
    check(not state.consume("message",{"text":"emblem_dialog"},server,[]),"chat text cannot open the picker")
    check(state.consume("emblem_dialog",{},server,[]) and state.visible,"only original event opens picker in world")
    check(state.draft=={"primary":0,"secondary":0,"pattern":0,"logo":1},"new choice uses original bounded defaults")
    var tok:String=state.token
    check(not state.request({"action":"emblem_select","token":"stale","logo":3},server),"old window token cannot change the draft")
    check(state.request({"action":"emblem_select","token":tok,"primary":15,"secondary":7,"pattern":3,"logo":255},server),"all original maximum choices are available")
    check(state.snapshot().emblem==131071,"original DOL bit layout preserves the high logo bit")
    check(server.client.calls.is_empty(),"preview never changes guild or equipment")
    for bad in [{"primary":16},{"secondary":8},{"pattern":4},{"logo":256},{"logo":0},{"primary":-1},{"logo":1.5},{"logo":"2"},{"logo":true}]:
        var request:Dictionary={"action":"emblem_select","token":tok};request.merge(bad)
        check(not state.request(request,server) and state.draft.logo==255,"invalid/fractional/text choice is rejected atomically: "+str(bad))
    var exported:Dictionary=state.snapshot();exported.draft.logo=2
    check(state.draft.logo==255,"snapshot cannot mutate editable state")
    check(state.request({"action":"emblem_submit","token":tok,"logo":1},server),"authorized current draft can be submitted")
    check(server.client.calls==[[15,7,3,255]],"response sends four original fields, ignoring uncommitted submit fields")
    check(not state.visible and state.feedback=="Request sent to server.","submission closes without claiming a successful payment or guild change")
    check(not state.request({"action":"emblem_submit","token":tok},server) and server.client.calls.size()==1,"repeat submit sends no duplicate packet")
    state.consume("emblem_dialog",{},server,[{"slot":11,"emblem":1024},{"slot":26,"emblem":66059}])
    check(state.snapshot().emblem==66059,"original worn cloak takes priority over shield")
    check(state.token!=tok,"new server dialogue invalidates the old picker")
    tok=state.token;check(state.request({"action":"emblem_close","token":tok},server) and server.client.calls.size()==1,"cancel never sends a choice")
    state.consume("emblem_dialog",{},server,[{"slot":11,"emblem":1024}]);check(state.draft.logo==2,"shield initializes picker when there is no emblem cloak")
    server.client=null;check(not state.request({"action":"emblem_submit","token":state.token},server) and state.visible,"lost connection keeps unsent choice visible")
    server.info.guild="Other Guild";state.sync(server,"QaPlayer");check(not state.visible and state.token.is_empty(),"membership change closes picker and invalidates draft")
    state.consume("emblem_dialog",{},server,[]);state.sync(server,"QaSecond");check(not state.visible,"character switch closes picker")
    server.info.guild="None";state.sync(server,"QaSecond");state.consume("emblem_dialog",{},server,[]);check(not state.visible,"no guild rejects stray dialogue")
    server.info.guild="QA Guild";state.sync(server,"QaSecond");server.playing=false;state.sync(server,"QaSecond");state.consume("emblem_dialog",{},server,[]);check(not state.visible,"character menu cannot open picker")
    server.playing=true;state.sync(server,"QaSecond");state.consume("emblem_dialog",{},server,[]);state.consume("quit",{},server,[]);check(not state.visible and state.token.is_empty(),"logout discards picker")
    server.free();print(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures}));quit(0 if failures.is_empty() else 1)
