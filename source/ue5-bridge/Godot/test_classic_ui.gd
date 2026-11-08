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
    var model=load("res://classic_ui_state.gd").new();var server:=FakeServer.new();var player:=Node3D.new();model.open_character("Bridge UI Test",get_script().resource_path.get_base_dir().path_join("../Reports/ui_integration/test_save"));model.capture_lists(server)
    var inv:={"ready":true,"revision":1,"state_revision":1,"items":[{"slot":10,"name":"Training sword","icon":1,"count":1,"token":"test-item","item_type":10}],"money":{"copper":3},"weight_now":2,"weight_max":70,"pending":false}
    model.sync(server,inv,100)
    check(model.bars.size()==3 and model.bars[2].size()==10 and model.bars[2][9].size()==10,"three bars, ten pages, ten slots")
    check(model.specs.size()==1 and model.entries.size()==7,"original server skill offsets and spell lines assembled")
    check(model.entries["srv:skill:0"].name=="Sprint" and model.entries["srv:skill:1"].kind=="style","specs do not offset use-skill index")
    check(model.entries["srv:spell:0:1"].name=="Heal","spell identifiers preserve line and level")
    check(model.entries["srv:spell:0:256"].kind=="spell","line abilities stay on the original magic sheet")
    check(model.entries["srv:spell:0:512"].kind=="style","line styles keep their original use-spell identifier")
    check(model.entries["srv:skill:2"].line=="Blades","hybrid spell grouped by actual specialization")
    var e:Dictionary=model.entries["srv:skill:0"];var v:={"action":"ui_assign","bar":0,"bank":0,"slot":0,"entry_id":e.id,"entry_token":e.token}
    check(model.request(v,server,player,207,true,true),"assign known server entry")
    check(server.calls.is_empty(),"assignment cannot execute an ability")
    var bad:Dictionary=v.duplicate();bad.entry_token="stale";check(not model.request(bad,server,player,207,true,true),"stale catalog cannot replace shortcut")
    var use:={"action":"ui_use_slot","bar":0,"slot":0};check(model.request(use,server,player,207,true,true) and server.calls==["srv:skill:0"],"quickbar executes original server identifier")
    var count:int=server.calls.size();check(not model.request(use,server,player,207,true,false) and server.calls.size()==count,"dead cannot execute bar")
    check(not model.request(use,server,player,202,true,true),"outside-region action blocked")
    server.cooldown=2;check(not model.request(use,server,player,207,true,true),"server cooldown blocks repeat")
    server.cooldown=0;model.catalog_loading=true;check(not model.request(use,server,player,207,true,true),"partial server lists cannot execute stale index");model.catalog_loading=false
    var move:Dictionary=v.duplicate();move.bar=2;move.bank=9;move.slot=9;move.from_bar=0;move.from_bank=0;move.from_slot=0
    check(model.request(move,server,player,207,true,true) and model.bars[0][0][0].is_empty() and model.bars[2][9][9].id==e.id,"drag moves shortcut atomically between bars/pages")
    check(model.request({"action":"ui_bank","bar":2,"bank":9},server,player,207,true,true),"page change accepted")
    var restored=load("res://classic_ui_state.gd").new();restored.open_character("Bridge UI Test",model.save_folder);check(restored.banks[2]==9 and restored.bars[2][9][9].id==e.id,"shortcuts and pages persist per character")
    for invalid in [true,"1",0.5,NAN,INF,-1,3]:check(not model.request({"action":"ui_bank","bar":invalid,"bank":0},server,player,207,true,true),"malformed bar index cannot mutate bindings")
    server.skills[1].icon=411;model.capture_lists(server);model.sync(server,inv,150);check(model.bars[2][9][9].name=="Sprint","same named skill survives server icon refresh")
    server.group_members=[{"oid":7,"name":"Member","class_name":"Hero","level":4}];model.observe("group",{},server);model.observe("group_update",{"list":[{"index":0,"hp":37,"power":21,"end":80}]},server);model.sync(server,inv,180);check(model.snapshot().group[0].hp==37,"group displays actual update percentages")
    var item:Dictionary=model.entries["srv:10"];var inspect:={"action":"ui_detail","entry_id":item.id,"entry_token":item.token}
    check(model.request(inspect,server,player,207,true,true) and server.queries.back()[1]==1 and server.queries.back()[2]==10,"item inspection uses original Detail type and real slot")
    check(model.snapshot().detail.status=="pending" and server.calls.size()==count,"inspection never uses or moves item")
    var key:String=model.detail.key;server.details[key]={"caption":"Training sword","lines":["Damage: 2.3","Condition: 100%"]};model.sync(server,inv,Time.get_ticks_msec())
    check(model.snapshot().detail.status=="ready" and model.detail.lines[0]=="Damage: 2.3","only actual server detail response populates lines")
    var stale:Dictionary=inspect.duplicate();stale.entry_token="stale";var nq:int=server.queries.size();check(not model.request(stale,server,player,207,true,true) and server.queries.size()==nq,"stale object cannot request information about replacement")
    inv.items[0].token="replacement";model.sync(server,inv,Time.get_ticks_msec());check(model.detail.is_empty(),"changing inspected item invalidates its information window")
    e=model.entries["srv:skill:0"];check(model.request({"action":"ui_detail","entry_id":e.id,"entry_token":e.token},server,player,207,true,false) and server.queries.back()[1]==8,"skill details use original mapping and remain readable while dead")
    model.sync(server,inv,Time.get_ticks_msec()+4100);check(model.detail.status=="unavailable" and model.detail.lines.is_empty(),"missing server response cannot invent properties")
    check(model.request({"action":"ui_detail_close"},server,player,207,true,true) and model.detail.is_empty(),"close clears information state")
    server.effects={2:{"icon":11,"name":"Timed buff","negative":0,"until":10000},7:{"icon":12,"name":"Permanent debuff","negative":1,"until":0}};model.sync(server,inv,4000)
    check(model.snapshot().effects.size()==2 and model.data.effects_remaining_ms["srv:effect:2"]==6000 and model.data.effects_remaining_ms["srv:effect:7"]==-1,"only server effects are shown with actual timed or permanent duration")
    var re:int=model.revision;model.sync(server,inv,5000);check(model.revision==re and model.data.effects_remaining_ms["srv:effect:2"]==5000,"timer ticks without rebuilding the UI catalog")
    var fx:Dictionary=model.effects["srv:effect:2"];var fquery:={"action":"ui_detail","entry_id":fx.id,"entry_token":fx.token};check(model.request(fquery,server,player,207,true,true) and server.queries.back()[1]==5 and server.queries.back()[2]==11,"effect description requests original type 5 and effect icon rather than slot")
    check(not model.request({"action":"ui_assign","bar":0,"bank":0,"slot":0,"entry_id":fx.id,"entry_token":fx.token},server,player,207,true,true),"effects cannot be assigned as usable skills")
    server.effects[2].until=15000;model.sync(server,inv,5000);check(model.detail.is_empty() and not model.request(fquery,server,player,207,true,true),"refresh invalidates previous effect description identity")
    server.effects.erase(2);model.sync(server,inv,5000);check(model.effects.size()==1 and not model.effects.has("srv:effect:2"),"server removal removes effect rather than leaving stale icon")
    server.effects[2]={"icon":11,"name":"Timed buff","negative":0,"until":10000};model.sync(server,inv,4000)
    model.feedback=""
    var original:Dictionary=server.info.duplicate(true);server.skills[1].name="Different skill";model.capture_lists(server);model.sync(server,inv,200)
    check(not model.request({"action":"ui_use_slot","bar":2,"slot":9},server,player,207,true,true),"reordered or renamed server entry cannot activate wrong ability")
    check(server.info==original and inv.items.size()==1,"UI does not change character points or inventory")
    var snapshot:Dictionary=model.snapshot();snapshot.character="Bridge UI Test";var f:=FileAccess.open(get_script().resource_path.get_base_dir().path_join("../Reports/ui_integration/fixture.json"),FileAccess.WRITE);f.store_string(JSON.stringify({"classic_ui":snapshot,"inventory":inv,"player_status":{"ready":true,"revision":1,"generation":1,"vitals":{"health_pct":100,"max_health":58,"mana_pct":0,"endurance_pct":100},"gm_mode":{"ready":true,"combat_test":false}}}));f.close()
    var report:={"passed":failures.is_empty(),"checks":checks,"failures":failures,"real_server":false};var out:=FileAccess.open(get_script().resource_path.get_base_dir().path_join("../Reports/ui_integration/godot_tests.json"),FileAccess.WRITE);out.store_string(JSON.stringify(report));out.close();print(JSON.stringify(report));server.free();player.free();quit(0 if failures.is_empty() else 1)
