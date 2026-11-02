extends SceneTree
class Server extends Node:
    var info:Dictionary={"level":8}
    var points:Dictionary={"spec_points":20}
    var trainer_skills:Dictionary={0:[{"name":"Learned spell","level":1,"page":3,"icon":409},{"name":"Next spell","level":3,"page":3,"icon":409}]}
    func skill_icon(kind:String,icon:int)->Array:return [icon,-1]
class Client extends Node:
    var calls:Array=[]
    func TrainWindow()->void:calls.append(["window"])
    func TrainSpec(index:int,level:int)->void:calls.append(["spec",index,level])
    func TrainRealmAbility(index:int,level:int)->void:calls.append(["realm",index,level])
var count:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:count+=1;if not ok:failures.append(label)
func _initialize()->void:
    var model=load("res://trainer_state.gd").new();var server:=Server.new();var client:=Client.new()
    model.sync(server,client,0);check(not model.ready and model.specs.is_empty(),"no class database invents trainable lines")
    check(not model.request({"action":"trainer_train"},client,1,true),"training requires a server window")
    check(model.request({"action":"trainer_refresh"},client,10,true) and client.calls==[["window"]],"window query cannot spend skill points")
    model.observe("trainer",{"points":20,"specs":[{"index":0,"name":"Arboreal Path","level":2,"next":3},{"index":2,"name":"Blades","level":8,"next":9}]},server);model.sync(server,client,100)
    check(model.ready and model.spec_points==20 and model.specs.size()==2 and model.pending.is_empty(),"server window opens actual lines and points")
    check(model.previews.is_empty(),"old character preview is not exposed before a new server preview")
    model.observe("trainer_skills",{},server);model.sync(server,client,150);check(model.previews["0"][1].name=="Next spell" and model.previews["0"][1].icon==409,"preview uses actual names levels and original icons")
    var first:Dictionary=model.specs[0].duplicate(true);var request:={"action":"trainer_train","training_kind":"spec","training_index":0,"training_token":first.token}
    check(not model.request(request,client,200,false),"dead character cannot train")
    check(not model.request({"action":"trainer_train","training_kind":"spec","training_index":2,"training_token":model.specs[1].token},client,210,true),"specialization cannot exceed actual character level")
    check(model.request(request,client,300,true) and client.calls.back()==["spec",0,3],"original packet asks exactly one next specialization level")
    check(model.specs[0].level==2 and model.spec_points==20,"no optimistic level or point subtraction")
    check(not model.request(request,client,350,true),"pending training cannot repeat")
    model.sync(server,client,899);check(client.calls.back()==["spec",0,3],"no early refresh or repeated training")
    model.sync(server,client,900);check(client.calls.back()==["window"],"original delayed window refresh queries authoritative result")
    model.observe("trainer",{"points":17,"specs":[{"index":0,"name":"Arboreal Path","level":3,"next":4},{"index":2,"name":"Blades","level":8,"next":9}]},server);server.points.spec_points=17;model.sync(server,client,1000)
    check(model.specs[0].level==3 and model.spec_points==17 and model.pending.is_empty(),"only server confirms trained level and remaining points")
    check(not model.request(request,client,1100,true),"old confirmation cannot train another level")
    for bad in [true,"0",.5,NAN,INF,-1,256]:check(not model.request({"action":"trainer_train","training_kind":"spec","training_index":bad,"training_token":model.specs[0].token},client,1200,true),"malformed training index rejected")
    model.observe("trainer_ra",{"points":5,"list":[{"index":0,"name":"Augmented Strength","level":0,"cost":1,"available":true},{"index":1,"name":"Not yet available","level":0,"cost":1,"available":false},{"index":2,"name":"Expensive ability","level":0,"cost":10,"available":true}]},server);model.sync(server,client,1300)
    check(model.realm_points==5 and model.realm[0].can_train and not model.realm[1].can_train and not model.realm[2].can_train,"realm costs availability and points are actual server values")
    check(not model.request({"action":"trainer_train","training_kind":"realm","training_index":1,"training_token":model.realm[1].token},client,1400,true),"unavailable realm ability cannot be requested")
    check(model.request({"action":"trainer_train","training_kind":"realm","training_index":0,"training_token":model.realm[0].token},client,1500,true) and client.calls.back()==["realm",0,1],"realm ability uses original train packet and exact next level")
    model.sync(server,client,6600);check(model.pending.is_empty() and model.realm[0].level==0 and model.realm_points==5,"rejected training expires without granting an ability or spending points")
    var stale:Dictionary=model.specs[0].duplicate(true);server.points.spec_points=10;model.sync(server,client,6700);check(not model.request({"action":"trainer_train","training_kind":"spec","training_index":0,"training_token":stale.token},client,6800,true),"point changes invalidate stale training confirmation")
    var before:Dictionary=model.specs[0].duplicate(true);model.observe("you",{},server);model.sync(server,client,6900);check(not model.ready and model.specs.is_empty() and model.previews.is_empty() and not model.request({"action":"trainer_train","training_kind":"spec","training_index":0,"training_token":before.token},client,7000,true),"new session clears trainer previews and old confirmations")
    server.points.spec_points=20;model.observe("trainer",{"points":20,"specs":[{"index":0,"name":"Arboreal Path","level":2,"next":3},{"index":1,"name":"Blades","level":1,"next":2},{"index":2,"name":"Parry","level":1,"next":2}]},server);model.observe("trainer_ra",{"points":5,"list":[{"index":0,"name":"Augmented Strength","level":0,"cost":1,"available":true},{"index":1,"name":"Purge","level":0,"cost":5,"available":false}]},server);model.observe("trainer_skills",{},server);model.sync(server,client,7100);model.feedback=""
    var fixture=JSON.parse_string(FileAccess.get_file_as_string(get_script().resource_path.get_base_dir().path_join("../Reports/ui_integration/fixture.json")));fixture.trainer_fixture=true;fixture.classic_ui.character="Bridge Trainer Fixture";fixture.classic_ui.trainer=model.snapshot()
    var f:=FileAccess.open(get_script().resource_path.get_base_dir().path_join("../Reports/trainer/fixture.json"),FileAccess.WRITE);f.store_string(JSON.stringify(fixture));f.close()
    var report:={"passed":failures.is_empty(),"checks":count,"failures":failures,"real_server":false,"real_points_spent":0};var out:=FileAccess.open(get_script().resource_path.get_base_dir().path_join("../Reports/trainer/godot_tests.json"),FileAccess.WRITE);out.store_string(JSON.stringify(report));out.close();print(JSON.stringify(report));server.free();client.free();quit(0 if failures.is_empty() else 1)
