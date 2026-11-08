extends "res://test_classic_ui.gd"
class ChargeServer extends FakeServer:
    var _item_lines:Dictionary={}
func _initialize()->void:
    var model=load("res://classic_ui_state.gd").new();var server:=ChargeServer.new();server._item_lines=server.details;var player:=Node3D.new()
    var inv:={"ready":true,"items":[{"slot":40,"name":"Potion","icon":1,"count":1,"token":"original-potion","item_type":40}],"money":{"copper":3}}
    model.capture_lists(server);model.sync(server,inv,Time.get_ticks_msec());var e:Dictionary=model.entries['srv:40']
    var command:={"action":"ui_use","entry_id":e.id,"entry_token":e.token}
    model.request({"action":"ui_hover","entry_id":e.id,"entry_token":e.token},server,player,207,true,true)
    model.request({"action":"ui_detail","entry_id":e.id,"entry_token":e.token},server,player,207,true,true)
    server.details[40]={"caption":"Potion","lines":["- 2 Charges"]};server.details[model.detail.key]=server.details[40].duplicate(true);model.sync(server,inv,Time.get_ticks_msec())
    check(model.request(command,server,player,207,true,true),"validated item use retains original request")
    check(server.calls==[e.id],"charge refresh cannot issue another use")
    check(not server.details.has(40) and not server.details.has(model.detail.key),"item use discards both old detail caches")
    check(model.hover.status=="pending" and model.hover.lines.is_empty() and model.detail.status=="pending" and model.detail.lines.is_empty(),"old charges disappear while awaiting original response")
    var key:String=model.item_detail_refresh[40].key
    check(key.begins_with('bridge-use-refresh:40:') and server.queries.back()==[key,1,40,'Potion'],"post-use detail uses separate original queue request")
    server.details[40]={"caption":"Potion","lines":["- 2 Charges"]};model.sync(server,inv,Time.get_ticks_msec())
    check(model.hover.status=="pending" and model.hover.lines.is_empty(),"older in-flight response cannot restore pre-use charges")
    server.details[key]={"caption":"Potion","lines":["- 1 Charges","Can use again in: 59 sec"]};model.sync(server,inv,Time.get_ticks_msec())
    check(model.hover.status=="ready" and model.hover.lines[0]=='- 1 Charges' and model.detail.lines==model.hover.lines,"hover and inspection share fresh authoritative reply")
    check(not server.details.has(key) and model.item_detail_refresh.is_empty(),"completed private response key is discarded")
    model.request(command,server,player,207,true,true);key=model.item_detail_refresh[40].key
    inv.items[0].token='replacement';model.sync(server,inv,Time.get_ticks_msec());server.details[key]={"caption":"Potion","lines":["Old item reply"]};model.sync(server,inv,Time.get_ticks_msec())
    check(model.hover.is_empty() and model.detail.is_empty() and not server.details.has(key),"late refresh cannot describe a replacement item or leak response keys")
    e=model.entries['srv:40'];model.request({"action":"ui_hover","entry_id":e.id,"entry_token":e.token},server,player,207,true,true)
    model.request({"action":"ui_use","entry_id":e.id,"entry_token":e.token},server,player,207,true,true);var until:int=model.item_detail_refresh[40].until_ms;model.sync(server,inv,until+1)
    check(model.hover.status=='unavailable' and model.hover.lines.is_empty(),"missing reply cannot invent a remaining charge count")
    check(inv.money.copper==3 and inv.items[0].count==1,"description refresh never changes money or item count")
    model.observe('quit',{},server)
    check(model.item_detail_refresh.is_empty(),"logout removes pending item refresh identities")
    server.free();player.free();print(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures}));quit(0 if failures.is_empty() else 1)
