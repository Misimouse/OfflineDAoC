extends SceneTree
var checks:=0
func check(value:bool,label:String)->void:
    checks+=1
    if not value:push_error(label);quit(1);assert(false,label)
func _initialize()->void:
    var t=load(get_script().resource_path.get_base_dir().path_join("target_tracking_state.gd")).new()
    var rows:={"npc:1":{"kind":"npc","name":"Witness","health":1.0,"targetable":true,"position_m":[25.0,0.0,0.0]},"player:local":{"kind":"player","position_m":[0,0,0]}}
    check(not t.request("follow","",rows,Vector3.ZERO,true,100),"no selection rejected")
    check(t.take_feedback()=="You must select a target to follow!","original missing-target message")
    check(not t.request("follow","player:local",rows,Vector3.ZERO,true,100),"self rejected")
    check(not t.request("other","npc:1",rows,Vector3.ZERO,true,100),"unsupported mode rejected")
    check(not t.request("follow","npc:1",rows,Vector3.ZERO,false,100),"unavailable player rejected")
    rows["npc:1"].health=0;check(not t.request("follow","npc:1",rows,Vector3.ZERO,true,100),"dead target rejected");rows["npc:1"].health=1
    rows["npc:1"].targetable=false;check(not t.request("follow","npc:1",rows,Vector3.ZERO,true,100),"untargetable entity rejected");rows["npc:1"].targetable=true
    for bad in [[1,2],[NAN,0,0],[INF,0,0],["1",0,0]]:
        rows["npc:1"].position_m=bad;check(not t.request("follow","npc:1",rows,Vector3.ZERO,true,100),"invalid target position rejected")
    rows["npc:1"].position_m=[25.0,0.0,0.0]
    check(t.request("follow","npc:1",rows,Vector3.ZERO,true,100),"exact original start range accepted")
    var seq:int=t.serial;check(t.pending and not t.active and t.mode=="follow","request awaits native result")
    check(not t.consume({"request_seq":seq,"target_entity_id":"npc:2","result":"started"}),"wrong-target result rejected")
    check(not t.consume({"request_seq":seq-1,"target_entity_id":"npc:1","result":"started"}),"stale result rejected")
    for bad in [NAN,INF,null,"1",seq+0.5]:
        check(not t.consume({"request_seq":bad,"target_entity_id":"npc:1","result":"started"}),"invalid request sequence rejected")
    check(t.consume({"request_seq":seq,"target_entity_id":"npc:1","result":"started"}) and t.active and not t.pending,"native start confirmed")
    check(t.take_feedback()=="You are now following Witness.","original following feedback")
    check(t.take_feedback().is_empty(),"feedback consumed once")
    check(not t.consume({"request_seq":seq,"target_entity_id":"npc:1","result":"started"}),"repeated start silent")
    check(t.consume({"request_seq":seq,"target_entity_id":"npc:1","result":"stopped"}) and t.mode.is_empty(),"native cancellation clears state")
    check(t.take_feedback()=="You are no longer following Witness.","original stop feedback")
    check(t.serial>seq,"cancel advances generation")
    rows["npc:1"].position_m=[25.001,0,0];check(not t.request("stick","npc:1",rows,Vector3.ZERO,true,100),"outside original start range rejected")
    check(t.request("face","npc:1",rows,Vector3.ZERO,true,100),"face retains original exemption from follow range")
    seq=t.serial;t.maintain(rows,true,5101);check(t.mode.is_empty() and t.serial>seq,"unacknowledged request expires")
    rows["npc:1"].position_m=[3,0,0];check(t.request("stick","npc:1",rows,Vector3.ZERO,true,200),"near stick request accepted")
    seq=t.serial;check(t.consume({"request_seq":seq,"target_entity_id":"npc:1","result":"rejected"}) and t.mode.is_empty(),"native resource failure rejected")
    check(t.request("face","npc:1",rows,Vector3.ZERO,true,200),"new request after rejection works")
    t.maintain({},true,201);check(t.mode.is_empty(),"despawn cancels request")
    check(t.request("follow","npc:1",rows,Vector3.ZERO,true,200),"follow requested again")
    t.maintain(rows,false,201);check(t.mode.is_empty(),"death posture or logout cancels")
    seq=t.serial;t.reset();check(t.serial>seq and t.mode.is_empty(),"session reset cannot replay request")
    print(JSON.stringify({"passed":true,"checks":checks}));quit()
