extends SceneTree
var checks:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func _initialize()->void:run.call_deferred()
func run()->void:
    var state=load(get_script().resource_path.get_base_dir().path_join("siege_visual_state.gd")).new()
    state.configure({"2645":{"siege":true,"idle":"original-idle","load":"original-load","fire":"original-fire"},"2598":{"siege":true},"118":{"load":"monster"}})
    var ids:Dictionary={12:"npc:12",13:"npc:13",14:"npc:14"};var rows:Dictionary={"npc:12":{"model_id":2645,"health":1.0,"state":"idle"},"npc:13":{"model_id":2598,"health":1.0},"npc:14":{"model_id":118,"health":1.0}}
    check(state.snapshot("npc:12",2645,0).events.is_empty(),"No invented announcement before server packet")
    state.consume("siege_anim",{"oid":12,"action":2,"timer":999},ids,rows,100)
    var load_event:Dictionary=state.snapshot("npc:12",2645,120).events[0]
    check(load_event.clip=="load" and load_event.age_ms==20,"Server ARM uses original load clip and actual packet age")
    check(not load_event.has("timer") and rows["npc:12"].health==1.0,"Body animation cannot change timer readiness or health")
    check(state.snapshot("npc:12",2645,120).events[0].seq==load_event.seq,"Repeated snapshots preserve identity without replay announcement")
    state.consume("siege_anim",{"oid":12,"action":3},ids,rows,200)
    check(state.snapshot("npc:12",2645,200).events[0].clip=="load" and state.sequence==2,"Original LOAD shares load clip")
    state.consume("siege_anim",{"oid":12,"action":4},ids,rows,300)
    check(state.snapshot("npc:12",2645,300).events[0].clip=="fire" and state.sequence==3,"Original FIRE uses original one-shot body clip")
    for action in [0,1,5,8,255,2.5,"2",INF]:state.consume("siege_anim",{"oid":12,"action":action},ids,rows,350)
    check(state.sequence==3,"Unmapped malformed and aiming actions cannot invent a body animation")
    state.consume("combat",{"oid":12,"action":4},ids,rows,350)
    check(state.sequence==3,"Generic combat packets are not misread as siege announcements")
    state.consume("siege_anim",{"oid":99,"action":4},ids,rows,350)
    check(state.sequence==3,"Unknown source identity refused")
    state.consume("siege_anim",{"oid":14,"action":2},ids,rows,350)
    check(state.sequence==3,"Ordinary monster cannot use object siege clips")
    state.consume("siege_anim",{"oid":13,"action":4},ids,rows,350)
    check(state.sequence==3 and state.snapshot("npc:13",2598,350).events.is_empty(),"Original static catapult retains missing body clip instead of invented motion")
    check(state.snapshot("npc:12",2645,8301).events.is_empty(),"Expired announcement discarded")
    state.consume("siege_anim",{"oid":12,"action":4},ids,rows,9000)
    check(state.snapshot("npc:12",2645,8999).events.is_empty(),"Backwards time cannot replay a future announcement")
    for kind in ["remove","death","you","region_changed","quit"]:
        state.consume("siege_anim",{"oid":12,"action":4},ids,rows,10000)
        state.consume(kind,{"oid":12},ids,rows,10001)
        check(state.snapshot("npc:12",2645,10002).events.is_empty(),"Lifecycle clears previous body event: "+kind)
    state.consume("siege_anim",{"oid":12,"action":4},ids,rows,11000)
    check(state.snapshot("npc:12",118,11000).events.is_empty(),"Reused OID with another model cannot inherit a siege fire")
    state.consume("siege_anim",{"oid":12,"action":4},ids,rows,12000);state.prune({})
    check(state.events.is_empty(),"Vanished source queues are pruned")
    rows["npc:12"].state="dead";state.consume("siege_anim",{"oid":12,"action":4},ids,rows,13000)
    check(state.events.is_empty(),"Dead siege body ignores subsequent action")
    check(state.supports(2645) and state.supports(2598) and not state.supports(118),"Only explicitly installed original siege catalogue enables this path")
    var report:Dictionary={"passed":failures.is_empty(),"checks":checks,"failures":failures}
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--report="):
            var file:=FileAccess.open(arg.trim_prefix("--report="),FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close()
    print(JSON.stringify(report));quit(0 if failures.is_empty() else 1)
