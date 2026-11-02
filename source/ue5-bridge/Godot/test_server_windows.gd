extends SceneTree
const Base=preload("res://test_classic_ui.gd")
var checks:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:checks+=1;if not ok:failures.append(label)
func _initialize()->void:
    var model=load("res://classic_ui_state.gd").new();var server=Base.FakeServer.new();var player:=Node3D.new()
    server.consume_details=false
    model.observe("detail",{"mode":0,"caption":"Realm Status","lines":["[Hibernia] <literal> status","Second line"]},server)
    check(model.server_window.caption=="Realm Status" and model.server_window.lines[0]=="[Hibernia] <literal> status","unconsumed custom window keeps original caption and literal lines")
    var old:Dictionary=model.server_window.duplicate(true);server.consume_details=true
    model.observe("detail",{"mode":0,"caption":"Training sword","lines":["Item detail"]},server);check(model.server_window==old,"quiet cached item response cannot replace a visible server window")
    server.consume_details=false;model.detail={"entry_id":"srv:skill:0","status":"pending","key":"pending-item"}
    model.observe("detail",{"mode":1,"caption":"Player Statistics","lines":["Original statistics"]},server);check(model.server_window.caption=="Player Statistics" and model.detail.status=="pending","server statistics do not erase pending bound item details")
    check(model.server_window.token!=old.token,"new window gets a distinct close identity")
    check(not model.request({"action":"ui_server_window_close","window_token":old.token},server,player,207,true,true) and model.server_window.caption=="Player Statistics","stale close cannot dismiss a newer announcement")
    model.data["server_window"]=model.server_window.duplicate(true)
    check(model.request({"action":"ui_server_window_close","window_token":model.server_window.token},server,player,207,true,true) and model.server_window.is_empty() and not model.detail.is_empty(),"close only dismisses the actual displayed server window")
    check(model.snapshot().server_window.is_empty(),"closed announcement cannot reappear from the previous published frame")
    check(server.calls.is_empty() and server.queries.is_empty(),"closing informational windows sends no game command")
    check(model.request({"action":"ui_server_window_close","window_token":"already closed"},server,player,207,true,true),"close is idempotent when window no longer exists")
    model.observe("detail",{"mode":0,"caption":"New window","lines":["Read only"]},server);model.observe("region_changed",{},server);check(model.server_window.is_empty() and model.detail.is_empty(),"region lifecycle clears both forms of information")
    var before:int=model.window_serial;model.observe("detail",{"mode":0,"caption":"New session window","lines":["Read only"]},server);check(int(model.server_window.token)>before,"session change cannot reuse a previous close token")
    model.capture_lists(server);model.sync(server,{"items":[]},100);var entry:Dictionary=model.entries["srv:skill:0"]
    check(model.request({"action":"ui_detail","entry_id":entry.id,"entry_token":entry.token},server,player,207,true,true) and model.server_window.is_empty() and model.detail.status=="pending","new explicit inspection replaces informational announcement without bypassing bound entry identity")
    model.observe("detail",{"mode":0,"caption":"Realm Status","lines":["[Hibernia] Original text from a server window.","A new information window must remain readable alongside the character sheets.","No action is attached to [bracketed] text or <tags>."]},server);model.feedback="";model.detail.clear();model.character="Bridge Server Window Fixture";model.sync(server,{"items":[]},200)
    var fixture=JSON.parse_string(FileAccess.get_file_as_string(get_script().resource_path.get_base_dir().path_join("../Reports/ui_integration/fixture.json")));fixture.server_window_fixture=true;fixture.classic_ui.server_window=model.server_window;fixture.classic_ui.character=model.character
    var f:=FileAccess.open(get_script().resource_path.get_base_dir().path_join("../Reports/server_windows/fixture.json"),FileAccess.WRITE);f.store_string(JSON.stringify(fixture));f.close()
    var report:={"passed":failures.is_empty(),"checks":checks,"failures":failures,"real_server":false,"game_commands_sent":server.calls.size()};var out:=FileAccess.open(get_script().resource_path.get_base_dir().path_join("../Reports/server_windows/godot_tests.json"),FileAccess.WRITE);out.store_string(JSON.stringify(report));out.close();print(JSON.stringify(report));server.free();player.free();quit(0 if failures.is_empty() else 1)
