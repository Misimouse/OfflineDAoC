extends SceneTree
var checks:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func packet()->Dictionary:return {"oid":12,"action":4,"effect":2202,"timer":1500,"x":35*8192+40000,"y":51*8192+40000,"z":5200}
func _initialize()->void:run.call_deferred()
func run()->void:
    var state=load(get_script().resource_path.get_base_dir().path_join("spell_visual_state.gd")).new()
    state.configure_siege({"2645":{"siege":true},"2598":{"siege":true},"2607":{"siege":true}},{"2202":{"target":373},"2204":{"target":381},"2209":{"target":401}})
    var ids:Dictionary={12:"npc:12"};var rows:Dictionary={"npc:12":{"model_id":2645}};var zone:Dictionary={"x":35,"y":51}
    check(state.snapshot(0).is_empty(),"No impact invented before FIRE")
    state.consume_siege(packet(),ids,rows,zone,100)
    var event:Dictionary=state.snapshot(120)[0]
    check(event.kind=="world_impact" and event.effect_id==2202,"Original spells namespace retained for stage resolution")
    check(event.position_m==[1000.0,130.0,1000.0],"Original absolute region point converts to scene metres")
    check(event.delay_ms==1500 and event.age_ms==20,"DOL fire timer retained as milliseconds")
    check(not event.has("ttl_ms") and not event.has("at_ms"),"Internal expiry fields stay out of transport")
    check(state.snapshot(130)[0].seq==event.seq,"Repeated snapshots retain one visual identity")
    for key in ["action","oid","effect","timer","x","y","z"]:
        var value:=packet();value[key]=2.5;var count:int=state.sequence;state.consume_siege(value,ids,rows,zone,200);check(state.sequence==count,"Malformed integer field rejected: "+key)
    for action in [0,1,2,3,5]:
        var value:=packet();value.action=action;var count:int=state.sequence;state.consume_siege(value,ids,rows,zone,200);check(state.sequence==count,"Non-FIRE does not produce an impact: "+str(action))
    var wrong:=packet();wrong.effect=373;state.consume_siege(wrong,ids,rows,zone,200);check(state.sequence==1,"Raw speffect index cannot be mistaken for a siege client effect")
    state.consume_siege(packet(),{},rows,zone,200);check(state.sequence==1,"Unknown source identity refused")
    var long_timer:=packet();long_timer.timer=60000;state.consume_siege(long_timer,ids,rows,zone,300)
    check(state.snapshot(10300).size()==1 and state.snapshot(10300)[0].delay_ms==60000,"Pending delayed impact survives ordinary eight-second event expiry")
    check(state.snapshot(68301).is_empty(),"Delayed event still has a bounded expiry")
    for kind in ["you","region_changed","quit"]:
        state.consume_siege(packet(),ids,rows,zone,70000);state.consume(kind,{},0,{},70001);check(state.snapshot(70002).is_empty(),"Session transition clears scheduled impact: "+kind)
    var report:Dictionary={"passed":failures.is_empty(),"checks":checks,"failures":failures}
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--report="):
            var file:=FileAccess.open(arg.trim_prefix("--report="),FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close()
    print(JSON.stringify(report));quit(0 if failures.is_empty() else 1)
