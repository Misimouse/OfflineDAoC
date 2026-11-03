extends SceneTree
class FakeServer extends Node:
    const RACE_BY_NAME={"Celt":9,"Firbolg":10,"Elf":11,"Lurikeen":12,"Sylvan":15}
    var playing:=false
    var characters:Array=[{"name":"Existinghero","slot":0,"race":"Celt","gender":"male","level":1,"class_name":"Naturalist","prefix":"cel_m"}]
    var calls:Array=[]
    var list_pending:=false
    func character_list_pending()->bool:return list_pending
    func characters_in(_realm:String)->Array:return characters
    func classes_for(_realm:String,race:int,_female:bool)->Array:return [[53,"Naturalist"]] if race==9 else []
    func name_error(name:String)->String:return "Invalid name." if not RegEx.create_from_string("^[A-Z][a-zA-Z]{2,22}$").search(name) else ""
    func create_character(realm:String,race:String,female:bool,cls:int,name:String,look:Dictionary)->String:calls.append([realm,race,female,cls,name,look]);return ""
    func request_characters(realm:String)->void:calls.append(["refresh",realm])
var checks:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func _initialize()->void:run.call_deferred()
func run()->void:
    var server:=FakeServer.new();root.add_child(server)
    var folder:String=get_script().resource_path.get_base_dir()
    var lobby=load(folder.path_join("character_lobby.gd")).new()
    lobby.enabled=true;server.list_pending=true;lobby.refresh(server)
    check(not lobby.ready,"creation remains disabled until all initial realm replies finish")
    server.list_pending=false;lobby.refresh(server)
    check(lobby.ready and lobby.roster.size()==1,"server list supplies existing characters")
    check(lobby.choices.size()==2,"creation choices obey original race and class rules")
    check(not lobby.execute({"action":"character_create","lobby_revision":-1},server,0) and server.calls.is_empty(),"stale selection sends no creation packet")
    check(not lobby.execute({"action":"character_create","lobby_revision":lobby.revision,"choice_id":"Celt:m:999","name":"Newhero"},server,0) and server.calls.is_empty(),"unsupported class cannot be requested")
    check(not lobby.execute({"action":"character_create","lobby_revision":lobby.revision,"choice_id":"Celt:m:53","name":"bad name"},server,0) and server.calls.is_empty(),"invalid name rejected before packet")
    check(not lobby.execute({"action":"character_create","lobby_revision":lobby.revision,"choice_id":"Celt:m:53","name":"Existinghero"},server,0) and server.calls.is_empty(),"existing name does not create duplicate")
    check(lobby.execute({"action":"character_create","lobby_revision":lobby.revision,"choice_id":"Celt:f:53","name":"Newhero"},server,100),"valid creation forwarded")
    check(server.calls.size()==1 and server.calls[0][0]=="hib" and server.calls[0][1]=="Celt" and server.calls[0][2] and server.calls[0][3]==53,"race gender and class reach original server API")
    check(lobby.roster.size()==1 and lobby.pending,"new character is not invented before server confirmation")
    check(not lobby.execute({"action":"character_create","lobby_revision":lobby.revision,"choice_id":"Celt:f:53","name":"Newhero"},server,101) and server.calls.size()==1,"double creation is blocked while pending")
    lobby.creation_result(false,"Server rejected name.")
    check(not lobby.pending and lobby.feedback=="Server rejected name.","server rejection releases pending state")
    lobby.execute({"action":"character_create","lobby_revision":lobby.revision,"choice_id":"Celt:m:53","name":"Otherhero"},server,1000)
    lobby.tick(31001,server)
    check(not lobby.pending and server.calls[-1]==["refresh","hib"],"timeout requests authoritative refreshed list")
    var entered:Array=[];lobby.enter_requested.connect(func(c):entered.append(c))
    check(lobby.execute({"action":"character_enter","lobby_revision":lobby.revision,"name":"Existinghero"},server,32000) and entered.size()==1,"enter uses exact server character")
    lobby.tick(999999,server)
    check(lobby.pending,"entering the world does not trigger creation timeout")
    server.playing=true
    check(not lobby.execute({"action":"character_create","lobby_revision":lobby.revision,"name":"Ignored"},server,0),"no creation while playing")
    var out:String=ProjectSettings.globalize_path(folder.path_join("../Reports/character_lobby")).simplify_path();DirAccess.make_dir_recursive_absolute(out)
    var file:=FileAccess.open(out.path_join("godot_tests.json"),FileAccess.WRITE);file.store_string(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures},"  "));file.close()
    print("CHARACTER_LOBBY_TEST passed=",failures.is_empty()," checks=",checks);quit(0 if failures.is_empty() else 1)
