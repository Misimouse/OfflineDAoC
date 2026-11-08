extends "res://test_classic_ui.gd"
func _initialize()->void:
    var model=load("res://classic_ui_state.gd").new();var server:=FakeServer.new();var player:=Node3D.new()
    var inv:={"ready":true,"items":[{"slot":40,"name":"Training sword","icon":1,"count":1,"token":"original-item","item_type":10}],"money":{"copper":3}}
    model.capture_lists(server);model.sync(server,inv,Time.get_ticks_msec())
    var item:Dictionary=model.entries["srv:40"]
    var command:={"action":"ui_hover","entry_id":item.id,"entry_token":item.token}
    model.server_window={"caption":"Original server window","token":"preserved"};model.feedback="Existing feedback";model.sync(server,inv,Time.get_ticks_msec())
    check(model.request(command,server,player,207,true,false),"information remains readable while dead")
    check(server.queries.back()[1]==1 and server.queries.back()[2]==40,"original item detail mapping uses real slot")
    check(model.hover.status=="pending" and model.hover.lines.is_empty(),"no invented item information")
    check(model.detail.is_empty() and model.server_window.token=="preserved","hover does not open or replace information windows")
    check(model.feedback=="Existing feedback" and server.calls.is_empty(),"hover cannot use item or overwrite action feedback")
    var count:int=server.queries.size()
    check(model.request(command,server,player,207,true,true) and server.queries.size()==count,"same pending hover does not flood original detail requests")
    var revision_before:int=model.revision
    var key:Variant=model.hover.key;server.details[key]={"caption":"Training sword","lines":["Condition: 81%","Durability: 97%","Original server description"]}
    check(key is int and key==40,"inventory hover shares original integer slot cache key")
    model.sync(server,inv,Time.get_ticks_msec())
    check(model.revision==revision_before,"hover-only response does not rebuild panels or close the tooltip")
    check(model.hover.status=="ready" and model.hover.lines[0]=="Condition: 81%","only original server reply supplies condition")
    check(model.snapshot().hover.lines.size()==3,"tooltip includes full original text")
    var copy:Dictionary=model.snapshot();copy.hover.lines[0]="changed copy"
    check(model.hover.lines[0]=="Condition: 81%" and server.details[key].lines[0]=="Condition: 81%","snapshot and response arrays cannot mutate authoritative hover cache")
    check(model.request(command,server,player,207,true,true) and server.queries.size()==count,"ready tooltip reuses current response")
    var stale:Dictionary=command.duplicate();stale.entry_token="stale"
    check(not model.request(stale,server,player,207,true,true) and server.queries.size()==count,"stale item cannot inspect replacement")
    check(not model.request(command,server,player,202,true,true),"outside current supported zone cannot request hover")
    server.details.erase(key);model.sync(server,inv,Time.get_ticks_msec())
    check(model.hover.status=="pending" and model.hover.lines.is_empty() and server.queries.size()==count+1,"original cache invalidation clears stale description and requeues once")
    model.sync(server,inv,Time.get_ticks_msec())
    check(server.queries.size()==count+1,"waiting for invalidated detail cannot flood requests")
    server.details[key]={"caption":"Training sword","lines":["Condition: 75%"]};model.sync(server,inv,Time.get_ticks_msec())
    check(model.hover.lines==["Condition: 75%"] and model.revision==revision_before,"updated original cache refreshes tooltip without rebuilding panels")
    model.catalog_loading=true;check(not model.request(command,server,player,207,true,true),"partial catalogue cannot query stale indices");model.catalog_loading=false
    inv.items[0].token="replacement";model.sync(server,inv,Time.get_ticks_msec())
    check(model.hover.is_empty(),"inventory change invalidates hover identity")
    check(not model.request(command,server,player,207,true,true),"old item token remains invalid after refresh")
    var spell:Dictionary=model.entries["srv:spell:0:1"]
    check(model.request({"action":"ui_hover","entry_id":spell.id,"entry_token":spell.token},server,player,207,true,true),"spell hover uses original list entry")
    check(server.queries.back()[1]==2 and server.queries.back()[2]==1,"spell request preserves original server mapping")
    check(model.hover.key=="sk:2:1","skill hover shares original skill cache invalidation")
    model.sync(server,inv,Time.get_ticks_msec()+4100)
    check(model.hover.status=="unavailable" and model.hover.lines.is_empty(),"missing reply cannot invent skill properties")
    check(model.server_window.token=="preserved" and model.detail.is_empty(),"missing hover response does not create a modal")
    var macro:Dictionary=model.register_macro("Face","/face")
    count=server.queries.size()
    check(model.request({"action":"ui_hover","entry_id":macro.id,"entry_token":macro.token},server,player,207,true,true),"local macro tooltip resolves exact identity")
    check(model.hover.lines==["/face"] and server.queries.size()==count,"macro text stays local and never executes")
    model.observe("quit",{},server)
    check(model.hover.is_empty(),"logout clears hover")
    server.free();player.free();print(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures}));quit(0 if failures.is_empty() else 1)
