extends SceneTree
class Wire extends Node:
    var requests:Array=[]
    func RequestCharacters(realm:int)->void:requests.append(realm)
var failures:Array=[]
var checks:=0
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func _initialize()->void:run.call_deferred()
func run()->void:
    var server=load("res://game/net/server.gd").new()
    var wire:=Wire.new()
    server.client=wire;server.logged=true;server._asking="alb";server._want=["hib"]
    check(server.character_list_pending(),"initial requests keep the list pending")
    server._on_characters(1,[{"name":"Existinghero","realm":3,"race":9}])
    check(server._asking=="","a realm-locked Hibernia response completes the outstanding Albion request")
    check(server.characters_in("hib").size()==1 and server.characters_in("alb").is_empty(),"characters remain in their authoritative realm")
    server._pump()
    check(server._asking=="hib" and wire.requests==[3],"queued Hibernia refresh is no longer blocked")
    var confirmations:Array=[]
    server.created.connect(func(ok:bool,why:String):confirmations.append([ok,why]))
    server._pending={"op":"create","realm":"hib","name":"Newhero"}
    server._on_characters(3,[{"name":"Newhero","realm":3,"race":9}])
    check(server._asking=="" and server._pending.is_empty(),"creation refresh clears the queue and pending operation")
    check(not server.character_list_pending(),"list becomes ready after the final server response")
    check(confirmations==[[true,""]],"creation is confirmed only from the server roster")
    await process_frame
    server.free();wire.free()
    print(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures}))
    quit(0 if failures.is_empty() else 1)
