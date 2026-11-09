extends SceneTree
class Client extends Node:
    var calls:Array=[]
    func UseSkill(x:float,y:float,z:float,speed:float,heading:int,visible:bool,index:int,type:int)->void:calls.append([x,y,z,speed,heading,visible,index,type])
class FakeServer extends Node:
    var me_oid:=1
    var playing:=true
    var client:Node
    func to_region(_zone:int,p:Vector3)->Vector3:return Vector3(35*8192+p.x/.025,51*8192+p.z/.025,p.y/.025)
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
    var actions=load("res://original_spec_actions.gd").new();var ui=load("res://classic_ui_state.gd").new()
    var server:=FakeServer.new();var client:=Client.new();server.client=client;var player:=Node3D.new()
    server.skills=[{"page":0,"name":"Blades","level":1},{"page":0,"name":"Stealth","level":1},{"page":1,"name":"Sprint","icon":409,"level":1}]
    server.spell_lines=[]
    ui.open_character("Private Stealth", "user://stealth")
    ui.spec_request=func(e:Dictionary)->bool:return actions.use(e,server,Vector3(1,2,3),1024,2.5,207,false)
    ui.capture_lists(server);ui.sync(server,{"ready":true,"items":[]},0)
    var e:Dictionary=ui.entries["srv:spec:1"].duplicate(true)
    check(e.name=="Stealth" and e.kind=="ability","original specialization is exposed in existing Abilities UI")
    check(ui.entries["srv:skill:0"].name=="Sprint","adding spec action preserves original non-spec indexes")
    check(ui.request({"action":"ui_hover","entry_id":e.id,"entry_token":e.token},server,player,207,false,true) and ui.hover.status=="ready" and ui.hover.lines==["Specialization level: 1"],"hover displays the actual specialization rank")
    check(ui.request({"action":"ui_detail","entry_id":e.id,"entry_token":e.token},server,player,207,false,true) and ui.detail.status=="ready" and ui.detail.caption=="Stealth","original detail panel displays specialization metadata")
    check(server.queries.is_empty(),"specialization details never query an unrelated server ability index")
    check(not ui.request({"action":"ui_detail","entry_id":e.id,"entry_token":"old"},server,player,207,false,true),"stale rank identity cannot open specialization details")
    var use:={"action":"ui_use","entry_id":e.id,"entry_token":e.token}
    check(ui.request(use,server,player,207,false,true),"current original spec action is usable")
    check(client.calls.size()==1 and client.calls[0]==[286760.0,417912.0,80.0,100.0,1024,false,1,0],"exact original type-zero UseSkill packet arguments")
    check(server.calls.is_empty(),"spec request never becomes a type-one ability or fabricated spell")
    var count:int=client.calls.size()
    check(not ui.request({"action":"ui_use","entry_id":e.id,"entry_token":"old"},server,player,207,false,true),"stale UI identity cannot use a specialization")
    check(not ui.request(use,server,player,207,false,false),"dead character cannot activate Stealth")
    check(not ui.request(use,server,player,208,false,true),"unsupported zone cannot activate Stealth")
    check(client.calls.size()==count,"rejected UI requests emit no packets")
    check(not actions.use({"id":"srv:spec:0","name":"Stealth","level":1},server,Vector3.ZERO,0,0,207,false),"unrelated weapon specialization is not made executable")
    check(not actions.use({"id":"srv:spec:-1","name":"Stealth","level":1},server,Vector3.ZERO,0,0,207,false),"negative index rejected")
    check(not actions.use({"id":"srv:spec:999","name":"Stealth","level":1},server,Vector3.ZERO,0,0,207,false),"out-of-list index rejected")
    check(not actions.use(e,server,Vector3(NAN,0,0),0,0,207,false),"nonfinite position rejected")
    check(not actions.use(e,server,Vector3.ZERO,4096,0,207,false),"invalid original heading rejected")
    check(not actions.use(e,server,Vector3.ZERO,0,INF,207,false),"nonfinite movement rejected")
    server.playing=false;check(not actions.use(e,server,Vector3.ZERO,0,0,207,false),"menu cannot use previous world specialization");server.playing=true
    server.skills[1].level=2;ui.capture_lists(server);ui.sync(server,{"ready":true,"items":[]},100)
    check(ui.entries[e.id].token!=e.token and not ui.request(use,server,player,207,false,true),"changed specialization invalidates previous drag identity")
    var current:Dictionary=ui.entries[e.id]
    check(ui.request({"action":"ui_assign","bar":0,"bank":0,"slot":0,"entry_id":current.id,"entry_token":current.token},server,player,207,false,true),"original Stealth action uses existing quickbar assignment")
    check(ui.request({"action":"ui_use_slot","bar":0,"slot":0},server,player,207,false,true),"quickbar uses the same original spec action")
    check(client.calls.back()[6]==1 and client.calls.back()[7]==0,"quickbar preserves specialization packet type")
    server.skills[1].level=0;ui.capture_lists(server);ui.sync(server,{"ready":true,"items":[]},200)
    check(not ui.entries.has(e.id),"zero specialization does not grant Stealth")
    check(not ui.request({"action":"ui_use_slot","bar":0,"slot":0},server,player,207,false,true),"removed specialization cannot be used from old bar")
    server.skills=[{"page":0,"name":"Regrowth","level":1},{"page":1,"name":"Sprint","icon":409,"level":1}];ui.capture_lists(server);ui.sync(server,{"ready":true,"items":[]},300)
    check(not ui.entries.values().any(func(row):return row.name=="Stealth"),"classes without server Stealth never receive the action")
    var gateway=load("res://live_gateway.gd").new()
    var adapter=load("res://decoded_world_adapter.gd").new()
    gateway.server=server;gateway.adapter=adapter;gateway.combat_visual=load("res://combat_visual_state.gd").new()
    adapter.oid_to_id={2:"player:2"}
    gateway.combat_visual.events={"player:2":[{"seq":1}],"player:local":[{"seq":2}]}
    gateway.combat_visual.fighting={"player:2":{"at":1},"player:local":{"at":2}}
    gateway.observe_combat_lifecycle("remove",99)
    check(gateway.combat_visual.events.has("player:2"),"unrelated ground removal preserves living combat pose")
    gateway.observe_combat_lifecycle("remove",2)
    check(not gateway.combat_visual.events.has("player:2") and not gateway.combat_visual.fighting.has("player:2"),"generic hidden-player removal clears combat before rapid reveal")
    check(gateway.combat_visual.events.has("player:local"),"remote hiding does not clear own combat state")
    gateway.observe_combat_lifecycle("quit",-1)
    check(gateway.combat_visual.events.is_empty() and gateway.combat_visual.fighting.is_empty(),"session exit clears both combat caches")
    gateway.adapter=null;gateway.server=null;gateway.free();adapter.free()
    var report:={"passed":failures.is_empty(),"checks":checks,"failures":failures}
    var f:=FileAccess.open("res://verified_stealth_state.json",FileAccess.WRITE);f.store_string(JSON.stringify(report));f.close()
    print(JSON.stringify(report));server.free();client.free();player.free();quit(0 if failures.is_empty() else 1)
