extends SceneTree
class Server extends Node:
    var conc_list:Array=[]
    var raw_seen:Dictionary={}
class Client extends Node:
    var calls:Array=[]
    func RemoveConcentration(index:int)->void:calls.append(index)
var checks:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:checks+=1;if not ok:failures.append(label)
func _initialize()->void:
    var model=load("res://concentration_state.gd").new();var server:=Server.new();var client:=Client.new();var vitals:={"max_mana":50,"max_conc":100,"conc":72}
    model.sync(server,vitals,false,0);check(not model.visible and model.maximum==0,"unready player does not invent a concentration pool")
    model.sync(server,{"max_mana":0,"max_conc":16960,"conc":16960},true,10);check(not model.visible,"physical GM with an administrative concentration pool does not get a caster window")
    model.sync(server,vitals,true,20);check(model.visible and model.maximum==100 and model.remaining==72 and model.entries.is_empty(),"caster pool is actual status data even with no maintained spells")
    server.conc_list=[{"index":2,"name":"Buff A","owner":"BridgeCaster","conc":16,"icon":409,"border":-1},{"index":5,"name":"Buff B","owner":"Companion","conc":12,"icon":410,"border":1}];server.raw_seen[0x75]=1;model.sync(server,vitals,true,100)
    var first:Dictionary=model.entries[0].duplicate(true);var second:Dictionary=model.entries[1].duplicate(true)
    check(first.index==2 and second.index==5 and first.name=="Buff A" and second.owner=="Companion" and second.icon==410,"original concentration indices owners cost and mapped icons preserved")
    vitals.conc=70;model.sync(server,vitals,true,150);check(model.entries[0].token==first.token and model.remaining==70,"pool changes do not invalidate unchanged spell list identity")
    var request:={"concentration_index":2,"concentration_token":first.token}
    check(model.request(request,client,200) and client.calls==[2],"cancel sends original RemoveConcentration index")
    check(model.entries.size()==2 and model.remaining==70,"cancel never removes an icon or restores points optimistically")
    check(not model.request({"concentration_index":5,"concentration_token":second.token},client,250) and client.calls.size()==1,"second cancellation waits to avoid renumbered list targeting wrong buff")
    server.conc_list=[{"index":2,"name":"Buff B","owner":"Companion","conc":12,"icon":410,"border":1}];server.raw_seen[0x75]=2;model.sync(server,vitals,true,300)
    check(model.entries.size()==1 and model.pending.is_empty() and model.entries[0].name=="Buff B","only authoritative list removes old effect")
    check(not model.request(request,client,350),"reused list position cannot cancel replacement effect with old token")
    check(not model.request({"concentration_index":5,"concentration_token":second.token},client,360),"old position of renumbered effect is rejected")
    var current:Dictionary=model.entries[0].duplicate(true);check(model.request({"concentration_index":2,"concentration_token":current.token},client,400),"current renumbered effect can request cancellation")
    model.sync(server,vitals,true,4500);check(model.stale and model.pending.is_empty() and model.entries.size()==1,"missing authoritative reply marks list stale without deleting effect")
    check(not model.request({"concentration_index":2,"concentration_token":current.token},client,4600),"timeout cannot enable blind retry against possibly shifted server index")
    server.raw_seen[0x75]=3;model.sync(server,vitals,true,4700);check(not model.stale and model.entries[0].token!=current.token,"fresh identical server packet re-establishes current list identity")
    for bad in [true,"2",.5,NAN,INF,-1,256]:check(not model.request({"concentration_index":bad,"concentration_token":model.entries[0].token},client,4800),"malformed cancellation index rejected")
    check(not model.request({"concentration_index":2,"concentration_token":""},client,4900),"missing concentration identity rejected")
    var unsupported:=Node.new();check(not model.request({"concentration_index":2,"concentration_token":model.entries[0].token},unsupported,4950),"missing protocol method never fabricates cancellation");unsupported.free()
    var old_token:String=model.entries[0].token;model.observe("quit");check(model.entries.is_empty() and not model.visible and not model.stale,"session lifecycle clears concentration state")
    model.sync(server,vitals,true,5000);check(not model.request({"concentration_index":2,"concentration_token":old_token},client,5100),"old session token cannot cancel new session effect")
    server.conc_list=[]
    for i in 20:server.conc_list.append({"index":i,"name":"Maintained spell %02d" % i,"owner":"Companion %02d" % i,"conc":2,"icon":409,"border":-1})
    server.raw_seen[0x75]=10;model.sync(server,{"max_mana":80,"max_conc":100,"conc":60},true,5200);model.feedback=""
    var fixture=JSON.parse_string(FileAccess.get_file_as_string(get_script().resource_path.get_base_dir().path_join("../Reports/ui_integration/fixture.json")));fixture.concentration_fixture=true;fixture.classic_ui.character="Bridge Concentration Fixture";fixture.classic_ui.concentration=model.snapshot()
    var f:=FileAccess.open(get_script().resource_path.get_base_dir().path_join("../Reports/concentration/fixture.json"),FileAccess.WRITE);f.store_string(JSON.stringify(fixture));f.close()
    var report:={"passed":failures.is_empty(),"checks":checks,"failures":failures,"real_server":false,"real_buffs_cancelled":0};var out:=FileAccess.open(get_script().resource_path.get_base_dir().path_join("../Reports/concentration/godot_tests.json"),FileAccess.WRITE);out.store_string(JSON.stringify(report));out.close();print(JSON.stringify(report));server.free();client.free();quit(0 if failures.is_empty() else 1)
