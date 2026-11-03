extends SceneTree
class FakeServer extends Node:
    const RACE_BY_NAME={"Celt":9,"Firbolg":10,"Elf":11,"Lurikeen":12,"Sylvan":15}
    var playing:=false
    var list_pending:=false
    var characters:Array=[{"name":"Existinghero","slot":0,"race":"Celt","gender":"male","level":1,"class_name":"Naturalist","prefix":"cel_m"}]
    var calls:Array=[]
    func character_list_pending()->bool:return list_pending
    func characters_in(_realm:String)->Array:return characters
    func classes_for(_realm:String,race:int,_female:bool)->Array:return [[53,"Naturalist"]] if race==9 else []
    func name_error(name:String)->String:return "Invalid name." if not RegEx.create_from_string("^[A-Z][a-zA-Z]{2,22}$").search(name) else ""
    func check_name(name:String)->void:calls.append(["check_name",name])
    func create_character(realm:String,race:String,female:bool,cls:int,name:String,look:Dictionary)->String:calls.append([realm,race,female,cls,name,look]);return ""
    func request_characters(realm:String)->void:calls.append(["refresh",realm])
    func creations()->Array:return calls.filter(func(c):return c.size()==6)
var checks:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func create(lobby:RefCounted,server:Node,name:String,now:int=100)->bool:
    return lobby.execute({"action":"character_create","lobby_revision":lobby.revision,"choice_id":"Celt:f:53","name":name},server,now)
func _initialize()->void:run.call_deferred()
func run()->void:
    var server:=FakeServer.new();root.add_child(server)
    var folder:String=get_script().resource_path.get_base_dir()
    var lobby=load(folder.path_join("character_lobby.gd")).new()
    lobby.enabled=true;server.list_pending=true;lobby.refresh(server)
    check(not lobby.ready,"creation waits for all initial realm replies")
    server.list_pending=false;lobby.refresh(server)
    check(lobby.ready and lobby.roster.size()==1,"server list supplies existing characters")
    server.characters[0]["class_name"]="";server.characters[0]["class_id"]=51;lobby.refresh(server)
    check(lobby.roster[0].class_name=="Magician","missing base-class overview caption uses the server class id")
    server.characters[0]["class_name"]="Naturalist";lobby.refresh(server)
    check(lobby.choices.size()==2,"creation choices obey original race and class rules")
    check(not lobby.execute({"action":"character_create","lobby_revision":-1},server,0) and server.calls.is_empty(),"stale selection sends no creation packet")
    check(not lobby.execute({"action":"character_create","lobby_revision":lobby.revision,"choice_id":"Celt:m:999","name":"Newhero"},server,0) and server.calls.is_empty(),"unsupported class cannot be requested")
    check(not create(lobby,server,"bad name") and server.calls.is_empty(),"invalid name rejected before packet")
    check(not create(lobby,server,"Existinghero") and server.calls.is_empty(),"own duplicate name is rejected locally")
    check(create(lobby,server,"Newhero"),"valid request starts authoritative name check")
    check(server.calls==[["check_name","Newhero"]] and server.creations().is_empty(),"no creation packet before the name is approved")
    check(lobby.roster.size()==1 and lobby.pending,"name check does not invent a character")
    check(not create(lobby,server,"Newhero") and server.calls.size()==1,"double submission is blocked while checking")
    lobby.name_result("Otherhero",0,server,150)
    check(server.creations().is_empty() and lobby.pending,"unrelated name reply cannot approve this request")
    lobby.name_result("Newhero",2,server,160)
    check(not lobby.pending and "already in use" in lobby.feedback and server.creations().is_empty(),"globally occupied name is explained without creating")
    create(lobby,server,"Rejectedhero");lobby.name_result("Rejectedhero",1,server,180)
    check(not lobby.pending and "does not allow" in lobby.feedback and server.creations().is_empty(),"server name rules are authoritative")
    create(lobby,server,"Freehero");lobby.name_result("freehero",0,server,200)
    check(server.creations().size()==1,"matching approval creates exactly once, ignoring letter case")
    var request:Array=server.creations()[0]
    check(request[0]=="hib" and request[1]=="Celt" and request[2] and request[3]==53 and request[4]=="Freehero","race gender class and original spelling reach original creation API")
    lobby.name_result("Freehero",0,server,201)
    check(server.creations().size()==1,"duplicate approval cannot send another creation")
    lobby.creation_result(false,"Server rejected name.")
    check(not lobby.pending and lobby.feedback=="Server rejected name.","creation rejection releases pending state")
    create(lobby,server,"Timeoutname",1000);var count:int=server.calls.size();lobby.tick(31001,server)
    check(not lobby.pending and server.calls.size()==count and "name check" in lobby.feedback,"name-check timeout does not send a character or roster request")
    lobby.name_result("Timeoutname",0,server,31002)
    check(server.creations().size()==1,"late approval after timeout is ignored")
    create(lobby,server,"Waitinghero",40000);lobby.name_result("Waitinghero",0,server,40001);lobby.tick(70002,server)
    check(not lobby.pending and not lobby.ready and server.calls[-1]==["refresh","hib"],"creation timeout refreshes the roster before another attempt")
    server.list_pending=true
    check(not create(lobby,server,"Toosoon"),"refreshing prevents a second creation from stale data")
    server.list_pending=false;lobby.refresh(server)
    var entered:Array=[];lobby.enter_requested.connect(func(c):entered.append(c))
    check(lobby.execute({"action":"character_enter","lobby_revision":lobby.revision,"name":"Existinghero"},server,80000) and entered.size()==1,"enter uses exact server character")
    lobby.tick(999999,server)
    check(lobby.pending,"entering the world does not trigger creation timeout")
    server.playing=true
    check(not create(lobby,server,"Ignored"),"no creation while playing")
    var out:String=ProjectSettings.globalize_path(folder.path_join("../Reports/character_lobby")).simplify_path();DirAccess.make_dir_recursive_absolute(out)
    var file:=FileAccess.open(out.path_join("godot_tests.json"),FileAccess.WRITE);file.store_string(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures},"  "));file.close()
    print("CHARACTER_LOBBY_TEST passed=",failures.is_empty()," checks=",checks);quit(0 if failures.is_empty() else 1)
