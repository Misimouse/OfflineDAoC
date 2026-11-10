extends SceneTree
const Fixture=preload("res://test_trainer_state.gd")
var count:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:
    count+=1
    if not ok:failures.append(label)
func _initialize()->void:
    var model=load("res://trainer_state.gd").new();var server=Fixture.Server.new();var client=Fixture.Client.new()
    server.info.level=2;server.points.spec_points=2
    model.observe("trainer",{"points":2,"specs":[{"index":0,"name":"Regrowth","level":1,"next":2}]},server);model.sync(server,client,100)
    check(model.specs[0].can_train,"exact server point balance permits next rank")
    var old:Dictionary=model.specs[0].duplicate(true)
    server.points.spec_points=1;model.sync(server,client,200)
    check(not model.specs[0].can_train,"one point below cost disables training")
    var before:int=client.calls.size()
    check(not model.request({"action":"trainer_train","training_kind":"spec","training_index":0,"training_token":old.token},client,201,true),"point change invalidates prior confirmation")
    check(not model.request({"action":"trainer_train","training_kind":"spec","training_index":0,"training_token":model.specs[0].token},client,202,true) and client.calls.size()==before,"current unaffordable entry sends no training packet")
    check(model.pending.is_empty() and model.specs[0].level==1 and model.spec_points==1,"refusal cannot change rank points or pending state")
    for points in [0,-1]:
        server.points.spec_points=points;model.sync(server,client,300)
        check(not model.specs[0].can_train,"zero or unknown point balance cannot enable training")
    server.points.spec_points=2;model.sync(server,client,400)
    check(model.specs[0].can_train,"new authoritative points enable the existing row")
    check(model.request({"action":"trainer_train","training_kind":"spec","training_index":0,"training_token":model.specs[0].token},client,401,true) and client.calls.back()==["spec",0,2],"affordable entry uses original exact next-rank request")
    check(model.spec_points==2 and model.specs[0].level==1,"accepted request never subtracts points optimistically")
    model.observe("trainer",{"points":0,"specs":[{"index":0,"name":"Regrowth","level":2,"next":3},{"index":1,"name":"Nurture","level":1,"next":2}]},server);server.points.spec_points=0;model.sync(server,client,500)
    check(not model.specs[0].can_train and not model.specs[1].can_train and model.pending.is_empty(),"server-spent points disable both level-capped and unaffordable rows")
    server.info.level=50;server.points.spec_points=50
    model.observe("trainer",{"points":50,"specs":[{"index":0,"name":"Regrowth","level":49,"next":50}]},server);model.sync(server,client,600)
    check(model.specs[0].can_train,"last ordinary rank accepts its exact point cost")
    server.info.level=49;model.sync(server,client,610)
    check(not model.specs[0].can_train,"sufficient points do not bypass character level")
    server.info.level=50;model.specs[0].level=50;model.specs[0].next=51;model.sync(server,client,620)
    check(not model.specs[0].can_train,"sufficient points do not bypass rank fifty cap")
    model.specs[0].level=1
    for cost in [0,-2,51]:
        model.specs[0].next=cost;model.sync(server,client,700)
        check(not model.specs[0].can_train,"invalid or unaffordable server cost remains unavailable")
    model.observe("trainer_ra",{"points":1,"list":[{"index":0,"name":"Realm ability","level":0,"cost":2,"available":true}]},server);model.sync(server,client,800)
    check(not model.realm[0].can_train,"existing realm point affordability remains enforced")
    var report:={"passed":failures.is_empty(),"checks":count,"failures":failures,"real_server":false};print(JSON.stringify(report));server.free();client.free();quit(0 if failures.is_empty() else 1)
