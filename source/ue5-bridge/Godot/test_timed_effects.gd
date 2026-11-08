extends SceneTree
class FakeServer extends Node:
    var skills:Array=[{"page":0,"name":"Blades","level":2,"bonus":1},{"page":1,"name":"Sprint","icon":409,"level":1},{"page":2,"name":"Style","icon":1,"level":2},{"page":3,"name":"Hybrid spell","icon":2,"level":1,"special":0}]
    var spell_lines:Array=[{"name":"Magic line","spells":[{"name":"Heal","level":1,"icon":3},{"name":"Line ability","level":256,"icon":4,"kind":"ability"},{"name":"Line style","level":512,"icon":5,"kind":"style"}]}]
    var info:Dictionary={"level":5,"class_name":"Test class","race_name":"Celt","base_class":"Guardian","profession":"Hero","title":"","realm_spec_points":2}
    var points:Dictionary={"spec_points":3,"realm_points":10,"xp":1200}
    var stats:Array=[60,61,62,63,64,65,66,67]
    var stat_buffs:Array=[0,-1,2,0,0,0,0,0]
    var resists:Array=[1,2,3,4,5,6,7,8,9]
    var con_lost:=1
    var weapon_stats:Dictionary={"weapon_skill":12,"weapon_damage":2.3,"armor_factor":10}
    var group_members:Array=[]
    var calls:Array=[]
    var cooldown:=0.0
    var effects:Dictionary={}
    var consume_details:=true
    var details:Dictionary={}
    var queries:Array=[]
    func skill_detail(e:Dictionary)->Array:return [8,100] if e.id=="srv:skill:0" else [2,1]
    func prefetch_detail(key:Variant,type:int,id:int,caption:String)->void:queries.append([key,type,id,caption])
    func item_lines(key:Variant)->Dictionary:return details.get(key,{})
    func take_detail(d:Dictionary)->bool:return consume_details
    func skill_icon(kind:String,icon:int)->Array:return [409,-1]
    func reuse_left(id:String)->float:return cooldown
    func use_entry(id:String,player:Node3D,zone:int,visible:bool)->bool:calls.append(id);return true
var checks:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func _initialize()->void:
    var model=load("res://classic_ui_state.gd").new()
    var server:=FakeServer.new();var player:=Node3D.new()
    model.open_character("Private Timed Effects", "user://timed_effects")
    model.capture_lists(server)
    var inv:={"ready":true,"items":[],"money":{},"weight_now":0,"weight_max":70,"pending":false}
    server.effects={2:{"icon":11,"name":"Timed buff","negative":0,"until":10000},7:{"icon":12,"name":"Permanent debuff","negative":1,"until":0}}
    model.sync(server,inv,4000)
    var first:Dictionary=model.effects["srv:effect:2"].duplicate(true)
    check(model.effects.size()==2,"only original server effects appear")
    check(model.data.effects_remaining_ms[first.id]==6000,"timed duration is actual deadline minus current time")
    check(model.data.effects_remaining_ms["srv:effect:7"]==-1,"permanent effect has no invented timer")
    check(not first.negative and model.effects["srv:effect:7"].negative,"beneficial and negative flags preserve original polarity")
    var revision:int=model.revision
    model.sync(server,inv,9500)
    check(model.data.effects_remaining_ms[first.id]==500,"countdown advances without server effect replacement")
    check(model.revision==revision,"countdown alone does not rebuild effect catalog")
    model.sync(server,inv,11000)
    check(model.data.effects_remaining_ms[first.id]==0,"overdue displayed timer clamps to zero")
    check(model.effects.has(first.id),"timer does not invent server effect removal")
    var query:={"action":"ui_detail","entry_id":first.id,"entry_token":first.token}
    check(model.request(query,server,player,207,true,true),"current effect is inspectable")
    check(server.queries.back()[1]==5 and server.queries.back()[2]==11,"description uses original effect icon detail request")
    var query_count:int=server.queries.size()
    server.effects[2].until=20000;model.sync(server,inv,12000)
    var renewed:Dictionary=model.effects[first.id].duplicate(true)
    check(model.effects.size()==2 and model.data.effects_remaining_ms[first.id]==8000,"renewal updates one icon and real remaining time")
    check(renewed.token!=first.token,"renewal invalidates prior effect identity")
    check(model.detail.is_empty(),"renewal closes outdated description")
    check(not model.request(query,server,player,207,true,true) and server.queries.size()==query_count,"outdated effect cannot request description of replacement")
    var renewed_query:={"action":"ui_detail","entry_id":renewed.id,"entry_token":renewed.token}
    check(model.request(renewed_query,server,player,207,true,false),"actual effects remain readable while dead")
    server.effects.erase(2);model.sync(server,inv,13000)
    check(not model.effects.has(first.id) and not model.data.effects_remaining_ms.has(first.id),"original server removal drops both icon and timer")
    check(model.detail.is_empty(),"removed effect closes its description")
    check(not model.request(renewed_query,server,player,207,true,true),"removed effect identity is unusable")
    server.effects[2]={"icon":19,"name":"Different buff","negative":0,"until":30000};model.sync(server,inv,14000)
    check(model.effects[first.id].name=="Different buff" and model.effects[first.id].token!=renewed.token,"reused server index is a new effect")
    check(not model.request(renewed_query,server,player,207,true,true),"old index cannot inspect a different buff")
    var replacement:Dictionary=model.effects[first.id]
    check(not model.request({"action":"ui_assign","bar":0,"bank":0,"slot":0,"entry_id":replacement.id,"entry_token":replacement.token},server,player,207,true,true),"active effects cannot become usable quickbar skills")
    check(server.calls.is_empty(),"effect inspection never casts or cancels a spell locally")
    var snapshot:Dictionary=model.snapshot()
    var root:String=get_script().resource_path.get_base_dir().path_join("../Reports/timed_effects")
    var fixture:={"classic_ui":snapshot,"inventory":inv,"player_status":{"ready":true,"revision":1,"generation":1,"vitals":{"health_pct":100,"max_health":58,"mana_pct":100,"endurance_pct":100},"gm_mode":{"ready":true,"combat_test":false}}}
    var f:=FileAccess.open(root.path_join("fixture.json"),FileAccess.WRITE);f.store_string(JSON.stringify(fixture));f.close()
    var report:={"passed":failures.is_empty(),"checks":checks,"failures":failures,"real_server":false}
    f=FileAccess.open(root.path_join("godot_tests.json"),FileAccess.WRITE);f.store_string(JSON.stringify(report));f.close()
    print(JSON.stringify(report));server.free();player.free();quit(0 if failures.is_empty() else 1)
