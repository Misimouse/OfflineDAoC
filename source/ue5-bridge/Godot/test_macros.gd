extends SceneTree
class Server extends Node:
    var commands:Array=[]
    func command(text:String)->void:commands.append(text)
var failures:Array=[]
var checks:=0
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func _initialize()->void:run.call_deferred()
func run()->void:
    var folder:String=get_script().resource_path.get_base_dir();var Model=load(folder.path_join("classic_ui_state.gd"));var model=Model.new();var server:=Server.new();var player:=Node3D.new()
    model.banks=[2,3,4];model.bars[0][2][0]={"id":"existing","name":"Existing","token":"keep"}
    check(not model.create_macro("/macron LOC /loc"),"unrelated server commands are not intercepted")
    check(model.create_macro("/macro"),"incomplete macro syntax is handled locally")
    check(model.macros.is_empty() and server.commands.is_empty(),"bad syntax neither creates nor executes a command")
    check(model.create_macro("/macro LOC /loc"),"original macro command is recognized")
    var macro:Dictionary=model.macros.values()[0]
    check(macro.name=="LOC" and macro.kind=="macro" and macro.macro_command=="/loc" and macro.id.begins_with("macro:"),"macro preserves command and canonical local identity")
    check(model.bars[0][2][0].id=="existing" and model.bars[0][2][1].id==macro.id,"macro uses first free slot on shown pages without overwriting")
    check(server.commands.is_empty(),"creating a macro never executes its command")
    check(model.create_macro('/macro Name012345678901234 /send Name "a quoted phrase"'),"macro may contain original command arguments")
    var named:Dictionary=model.macros.values()[1]
    check(named.name.length()==14 and named.macro_command=='/send Name "a quoted phrase"',"original fourteen-character label limit preserves command arguments")
    check(model.register_macro("X","a".repeat(241)).is_empty() and model.register_macro("X","/loc\n/say bad").is_empty(),"overlong and multiline protocol commands are rejected")
    check(model.request({"action":"ui_use","entry_id":macro.id,"entry_token":macro.token},server,player,207,true,true) and server.commands.back()=="/loc","using catalog macro calls original Server.command")
    check(not model.request({"action":"ui_use","entry_id":macro.id,"entry_token":"stale"},server,player,207,true,true),"stale macro identity cannot execute")
    model.catalog_loading=true
    check(model.request({"action":"ui_use_slot","bar":0,"slot":1},server,player,207,false,false) and server.commands.back()=="/loc","command macro remains usable while dead or spell catalog reloads")
    model.catalog_loading=false
    check(model.request({"action":"ui_detail","entry_id":macro.id,"entry_token":macro.token},server,player,207,true,true) and model.detail.lines==["/loc"] and model.detail.status=="ready","macro inspection is local literal command text")
    var altered:Dictionary=macro.duplicate(true);altered.macro_command="/wrong";model.bars[0][2][1]=altered
    check(model.request({"action":"ui_use_slot","bar":0,"slot":1},server,player,207,true,true) and server.commands.back()=="/loc","shortcut payload cannot override canonical macro command")
    model.entries[macro.id].macro_command="/wrong"
    check(not model.request({"action":"ui_use","entry_id":macro.id,"entry_token":macro.token},server,player,207,true,true),"modified catalog payload cannot execute a different command")
    model.entries[macro.id]=macro.duplicate(true)
    var routed:Array=[];var count_before:int=server.commands.size();model.macro_request=func(text:String)->bool:routed.append(text);return true
    check(model.request({"action":"ui_use","entry_id":macro.id,"entry_token":macro.token},server,player,207,true,true) and routed==["/loc"] and server.commands.size()==count_before,"client macro command uses the same dispatch route as typed chat")
    var storage:String=folder.path_join("../Reports/macros/unit-storage/"+Crypto.new().generate_random_bytes(6).hex_encode());model.open_character("Macro Test",storage);check(model.macros.is_empty() and model.bars[0][2][0].is_empty(),"switching characters clears previous shortcuts and macros")
    model.create_macro("/macro SAVE /loc");var saved:Dictionary=model.macros.values()[0];var before:int=server.commands.size()
    var restored=Model.new();restored.open_character("Macro Test",storage)
    check(restored.macros.has(saved.id) and restored.bars[0][int(restored.banks[0])][0].id==saved.id,"macro definitions and shown-page binding survive a new session")
    check(server.commands.size()==before,"loading saved macro definitions never executes commands")
    check(restored.request({"action":"ui_use_slot","bar":0,"slot":0},server,player,207,true,true) and server.commands.back()=="/loc","restored macro resolves against its canonical definition")
    restored.request({"action":"ui_clear","bar":0,"bank":int(restored.banks[0]),"slot":0},server,player,207,true,true)
    check(restored.macros.has(saved.id) and restored.bars[0][int(restored.banks[0])][0].is_empty(),"clearing a shortcut leaves macro available for another page")
    var legacy=Model.new();var old:Array=legacy.bars.duplicate(true);old[1][0][3]={"kind":"macro","id":"/loc","name":"LEGACY","icon":-1};old[1][0][4]={"kind":"macro","id":"macro:missing-command","name":"BAD","icon":-1}
    var file:=FileAccess.open(storage.path_join("legacy.json"),FileAccess.WRITE);file.store_string(JSON.stringify({"quickbars":old,"bank":[0,0,0]}));file.close();legacy.open_character("Legacy Macro",storage,storage.path_join("legacy.json"))
    check(legacy.bars[1][0][3].id.begins_with("macro:") and legacy.bars[1][0][3].macro_command=="/loc","old Godot raw-command macro shortcuts migrate without losing their slot")
    check(legacy.bars[1][0][4].is_empty(),"malformed new-format shortcut cannot reinterpret its id as chat text")
    var full=Model.new()
    for b in 3:
        for i in 10:full.bars[b][0][i]={"id":"occupied"}
    full.create_macro("/macro FULL /loc")
    check(full.macros.size()==1 and full.bars[2][0][9].id=="occupied","full visible bars keep macro in catalog and preserve every occupied slot")
    var fixture_model=Model.new();fixture_model.create_macro("/macro LOC /loc");var e:Dictionary=fixture_model.macros.values()[0]
    var fixture:Dictionary=JSON.parse_string(FileAccess.get_file_as_string(folder.path_join("../Reports/ui_integration/fixture.json")));fixture.macro_fixture=true;fixture.classic_ui.character="Bridge Macro Fixture";fixture.classic_ui.entries.append(e);fixture.classic_ui.bars[2][int(fixture.classic_ui.banks[2])][9]=e
    file=FileAccess.open(folder.path_join("../Reports/macros/fixture.json"),FileAccess.WRITE);file.store_string(JSON.stringify(fixture));file.close()
    var report:={"passed":failures.is_empty(),"checks":checks,"failures":failures,"real_server":false};file=FileAccess.open(folder.path_join("../Reports/macros/godot_tests.json"),FileAccess.WRITE);file.store_string(JSON.stringify(report));file.close();print(JSON.stringify(report));server.free();player.free();quit(0 if failures.is_empty() else 1)
