extends SceneTree
class FakeServer extends Node:
    const RACE_BY_NAME={"Celt":9,"Firbolg":10,"Elf":11,"Lurikeen":12,"Sylvan":15,"Shar":18}
    var playing:=false
    var list_pending:=false
    var characters:Array=[{"name":"Existinghero","slot":0,"race":"Celt","gender":"male","level":1,"class_name":"Naturalist","prefix":"cel_m"}]
    var calls:Array=[]
    var classes:Dictionary={"classes":{"39":{"gender":"female"}}}
    var offer_bainshee:=false
    var offer_shar:=false
    func character_list_pending()->bool:return list_pending
    func characters_in(_realm:String)->Array:return characters
    func classes_for(_realm:String,race:int,_female:bool)->Array:
        var out:Array=[[53,"Naturalist"]] if race==9 else []
        if offer_bainshee and race in [9,11,12]:out.append([39,"Bainshee"])
        if offer_shar and race==18:out.append_array([[42,"Mentalist"],[43,"Blademaster"],[44,"Heroine" if _female else "Hero"],[45,"Champion"],[50,"Ranger"]])
        return out
    func name_error(name:String)->String:return "Invalid name." if not RegEx.create_from_string("^[A-Z][a-zA-Z]{2,22}$").search(name) else ""
    func check_name(name:String)->void:calls.append(["check_name",name])
    func create_character(realm:String,race:String,female:bool,cls:int,name:String,look:Dictionary)->String:calls.append([realm,race,female,cls,name,look]);return ""
    func request_characters(realm:String)->void:calls.append(["refresh",realm])
    func save_look(char_name:String,look:Dictionary)->void:
        calls.append(["save_look",char_name,look.duplicate(true)])
        for c in characters:
            if String(c.name)==char_name:c["look"]=look.duplicate(true)
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
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--bridge-module-folder="):folder=arg.trim_prefix("--bridge-module-folder=")
    var lobby=load(folder.path_join("character_lobby.gd")).new()
    lobby.enabled=true;server.list_pending=true;lobby.refresh(server)
    check(not lobby.ready,"creation waits for all initial realm replies")
    server.list_pending=false;lobby.refresh(server)
    check(lobby.ready and lobby.roster.size()==1,"server list supplies existing characters")
    server.characters[0]["look"]={"face":2,"hair":1,"sliders":[2,6,4,3]};lobby.refresh(server)
    var preview:Dictionary=lobby.snapshot();preview.characters[0].look.sliders[0]=8
    check(lobby.roster[0].look.face==2 and lobby.roster[0].look.hair==1 and lobby.roster[0].look.sliders[0]==2,"server appearance reaches preview without sharing mutable character state")
    server.characters[0]["class_name"]="";server.characters[0]["class_id"]=51;lobby.refresh(server)
    check(lobby.roster[0].class_name=="Magician","missing base-class overview caption uses the server class id")
    server.characters[0]["class_name"]="Naturalist";lobby.refresh(server)
    check(lobby.choices.size()==2,"creation choices obey original race and class rules")
    server.offer_bainshee=true;lobby.refresh(server)
    var forms:Array=lobby.choices.filter(func(c):return int(c.class_id)==39)
    check(forms.size()==3 and forms.all(func(c):return c.female),"server female-only restriction applies to all three Bainshee races")
    check(not lobby.execute({"action":"character_create","lobby_revision":lobby.revision,"choice_id":"Celt:m:39","name":"Invalidmale"},server,0) and server.calls.is_empty(),"stale or crafted male Bainshee choice cannot request creation")
    server.classes.classes["39"].gender="unknown";lobby.refresh(server)
    check(not lobby.choices.any(func(c):return int(c.class_id)==39),"invalid gender metadata never enables an unsupported choice")
    server.offer_bainshee=false;lobby.refresh(server)
    check(not lobby.choices.any(func(c):return c.race=="Shar"),"transport metadata alone cannot enable Shar without server class choices")
    server.offer_shar=true;lobby.refresh(server)
    var shar_choices:Array=lobby.choices.filter(func(c):return c.race=="Shar")
    check(shar_choices.size()==10 and shar_choices.all(func(c):return int(c.class_id) in [42,43,44,45,50]),"Shar exposes exactly the five authorized classes for both sexes")
    check(not lobby.execute({"action":"character_create","lobby_revision":lobby.revision,"choice_id":"Shar:f:46","name":"Deniedshar"},server,0) and server.calls.is_empty(),"crafted Shar Warden cannot bypass server eligibility")
    if "--bridge-shar-test" in OS.get_cmdline_user_args():
        for female in [false,true]:
            var prefix:String="sha_f" if female else "sha_m"
            var shar_look:Dictionary={"face":1,"eyes":7,"skin":3,"hair":1,"hair_color":2,"tattoo":1,"size":2,"sliders":[1,6,2,7]}
            check(lobby.validated_look(shar_look,prefix).ok,"original Shar metadata validates a full distinct look for "+prefix)
            check(not lobby.validated_look({"eyes":8},prefix).ok,"Shar eye index remains bounded by original choices")
            var name:String="Sharwoman" if female else "Sharman"
            check(lobby.execute({"action":"character_create","lobby_revision":lobby.revision,"choice_id":"Shar:"+("f" if female else "m")+":42","name":name,"look":shar_look},server,100),"Shar creation starts the original name check")
            lobby.name_result(name,0,server,101)
            var packet:Array=server.creations()[-1] if not server.creations().is_empty() else []
            check(packet.size()==6 and packet[1]=="Shar" and packet[2]==female and packet[3]==42 and packet[5]==shar_look,"Shar sex, class and complete appearance reach the original creation API")
            lobby.creation_result(true,"");server.calls.clear()
    server.offer_shar=false;lobby.refresh(server)
    check(not lobby.choices.any(func(c):return c.race=="Shar"),"withdrawn Shar eligibility immediately removes all expansion choices")
    for prefix in ["cel_m","cel_f","elf_m","elf_f","fir_m","fir_f","lur_m","lur_f","syl_m","syl_f"]:
        check(lobby.validated_look({},prefix).ok,"original default appearance exists for "+prefix)
    check(not lobby.validated_look({"sliders":[NAN]},"cel_m").ok,"nonfinite facial features cannot enter a packet")
    check(not lobby.validated_look({"face":999},"cel_m").ok,"face must exist in the selected race")
    check(not lobby.validated_look({"model":1984},"cel_m").ok,"look cannot inject a model or unrelated packet field")
    check(not lobby.execute({"action":"character_customize","lobby_revision":lobby.revision,"name":"Otherhero","look":{}},server,0) and server.calls.is_empty(),"customization requires an exact character from the current server roster")
    var chosen:Dictionary={"face":1,"hair":0,"eyes":2,"sliders":[1,2,3,4]}
    check(lobby.execute({"action":"character_customize","lobby_revision":lobby.revision,"name":"Existinghero","look":chosen},server,0),"existing character uses the original appearance persistence API")
    check(server.calls.size()==1 and server.calls[0][0]=="save_look" and lobby.roster[0].look.face==1 and lobby.roster[0].look.sliders==[1,2,3,4],"saved look returns through roster instead of an NPC preset")
    chosen.sliders[0]=8
    check(lobby.roster[0].look.sliders[0]==1,"saved appearance does not share the incoming command arrays")
    server.calls.clear()
    var legacy:Dictionary={"face":15,"hair":15,"hair_color":15,"skin":15,"eyes":15,"sliders":[15,-1,4,8,12],"old_format":true}
    server.characters[0]["look"]=legacy.duplicate(true);lobby.refresh(server)
    check(server.characters[0].look==legacy and server.calls.is_empty(),"opening an old character never rewrites its original look store")
    check(lobby.roster[0].look.sliders==[8,0,4,8] and not lobby.roster[0].look.has("old_format"),"legacy server face bytes become an editable bounded view")
    check(lobby.validated_look(lobby.roster[0].look,"cel_m").ok,"unchanged compatibility view can be saved by the current editor")
    check(not lobby.execute({"action":"character_customize","lobby_revision":lobby.revision,"name":"Existinghero","look":legacy},server,0) and server.calls.is_empty(),"client commands cannot opt into legacy normalization")
    check(lobby.execute({"action":"character_customize","lobby_revision":lobby.revision,"name":"Existinghero","look":lobby.roster[0].look},server,0) and server.calls.size()==1,"old character saves only after an explicit valid customization action")
    check(lobby.validated_look(lobby.stored_look({"prefix":"cel_m","look":null}),"cel_m").ok,"malformed local look storage falls back to valid original defaults without a crash")
    server.calls.clear()
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
