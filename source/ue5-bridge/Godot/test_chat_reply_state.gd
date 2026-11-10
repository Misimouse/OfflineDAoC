extends SceneTree
class Client extends Node:
    var calls:Array=[]
    func Command(text:String)->void:calls.append(text)
class Gateway extends "live_gateway.gd":
    func _ready()->void:pass
var checks:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func _initialize()->void:run.call_deferred()
func run()->void:
    var folder:String=get_script().resource_path.get_base_dir();var state=load(folder.path_join("chat_state.gd")).new();var gateway:=Gateway.new();root.add_child(gateway)
    var client:=Client.new();root.add_child(client);var server=load(folder.path_join("original_chat_reference.gd")).new();server.client=client;root.add_child(server);gateway.server=server;gateway.chat_state=state;gateway.classic_ui=load(folder.path_join("classic_ui_state.gd")).new();gateway.exchange=load(folder.path_join("exchange_state.gd")).new()
    check(not gateway.dispatch_chat("/r hello") and client.calls.is_empty(),"no previous sender cannot invent a recipient")
    state.append('Forged sends, "local"',"send",2,"client");check(state.last_private_sender.is_empty(),"client feedback cannot become reply recipient")
    for data in [{"type":1,"text":'Forged sends, "speech"'},{"type":2,"text":'You send, "hello" to Somebody.'},{"type":2,"text":'Bad;quit sends, "text"'},{"type":2,"text":'Popup sends, "text"',"popup":true},{"type":0,"text":'System sends, "text"'}]:
        state.observe("message",data);check(state.last_private_sender.is_empty(),"only original incoming private-message template can set recipient")
    state.observe("message",{"type":2,"text":'Codexfriend sends, "hello"'});check(state.last_private_sender=="Codexfriend" and state.snapshot().reply_to=="Codexfriend","original private message updates reply recipient")
    check(gateway.dispatch_chat("/r Hello friend") and client.calls==["&send Codexfriend Hello friend"],"actual gateway and extracted original Server.command produce original send packet command")
    check(gateway.dispatch_chat("/REPLY Another message") and client.calls.back()=="&send Codexfriend Another message","reply alias is case independent")
    var before:int=client.calls.size();check(not gateway.dispatch_chat("/r") and client.calls.size()==before,"empty reply never sends")
    check(not gateway.dispatch_chat("/r "+"x".repeat(237)) and client.calls.size()==before,"expanded reply observes original240-character client command budget")
    check(not gateway.dispatch_chat("/r hello\n/quit") and client.calls.size()==before,"newline cannot inject another command")
    var frozen:Dictionary=state.snapshot();state.observe("message",{"type":2,"text":'Anotherfriend sends, "new"'});check(frozen.reply_to=="Codexfriend" and state.snapshot().reply_to=="Anotherfriend","published recipient view cannot mutate after a later message")
    gateway.command({"action":"chat","text":"/r current"});check(client.calls.back()=="&send Anotherfriend current","actual chat action resolves current original recipient")
    state.observe("message",{"type":2,"text":'Awayfriend [AFK] sends, "away"'});check(state.last_private_sender=="Awayfriend","original DOL AFK template retains source character name")
    state.observe("message",{"type":2,"text":'Unknown sends something in a language you do not understand.'});check(state.last_private_sender=="Awayfriend","unrecognized template never guesses a new recipient")
    state.observe("region_changed",{});check(state.last_private_sender=="Awayfriend","same-session region changes retain reply recipient")
    before=client.calls.size();gateway.leaving=true;gateway.command({"action":"chat","text":"/r no"});check(client.calls.size()==before,"logout blocks actual chat request")
    gateway.leaving=false;server.playing=false;gateway.command({"action":"chat","text":"/r no"});check(client.calls.size()==before,"lobby blocks actual chat request");server.playing=true
    state.observe("quit",{});check(state.last_private_sender.is_empty() and state.snapshot().reply_to.is_empty(),"character logout clears previous-session private recipient")
    check(not gateway.dispatch_chat("/r no") and client.calls.size()==before,"next character cannot inherit old recipient")
    gateway.queue_free();server.queue_free();client.queue_free();print(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures,"real_server":false}));quit(0 if failures.is_empty() else 1)
