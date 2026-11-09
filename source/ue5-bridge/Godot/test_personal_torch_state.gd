extends SceneTree
var checks:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func _initialize()->void:
    var folder:String=get_script().resource_path.get_base_dir()
    var t=load(folder.path_join("personal_torch_state.gd")).new()
    check(t.snapshot().enabled and not t.snapshot().clock_known,"original on default, no invented clock")
    for on in [false,true]:
        check(t.apply_request({"on":on,"player_generation":7},7,true),"current character toggle accepted")
        for flags in [0,1,2,4,8,16,32,64,127,128,255,0x1000,0xB000]:
            var result:int=t.action_flags(flags)
            check((result&~0x80)==(flags&~0x80) and bool(result&0x80)==on,"torch preserves every other action or visibility bit")
    for value in [null,1,"true",0.0,[],{}]:check(not t.apply_request({"on":value,"player_generation":7},7,true),"malformed enabled flag rejected")
    for epoch in [null,6,8,7.1,NAN,INF,"7",true]:check(not t.apply_request({"on":false,"player_generation":epoch},7,true),"stale or malformed character generation rejected")
    check(not t.apply_request({"on":false,"player_generation":7},7,false),"menu cannot toggle in-world light")
    for spec in [[0.0,1.0],[4.5,1.0],[6.0,0.5],[7.5,0.0],[12.0,0.0],[16.5,0.0],[18.0,0.5],[19.5,1.0],[23.999,1.0]]:
        t.advance(spec[0],0.0,0.0);check(is_equal_approx(t.snapshot().night_level,spec[1]),"existing Godot phase key retained")
    for hour in [-1.0,24.0,NAN,INF]:
        t.advance(hour,0.0,0.0);check(not t.snapshot().clock_known and is_equal_approx(t.snapshot().energy_scale,0.15),"invalid clock retains conservative daylight factor")
    t.reset_session()
    for n in range(45):t.advance(12.0,1.0,1.0)
    check(is_equal_approx(t.storm,1.0) and is_equal_approx(t.night_level,0.3),"original45-second storm ramp and daylight contribution")
    t.advance(0.0,1.0,1.0);check(t.night_level==1.0,"night plus storm remains bounded")
    var reference=load(folder.path_join("original_phase_reference.gd")).new()
    t.reset_session()
    for minute in range(1440):
        var hour:float=minute/60.0;var weights:Dictionary=reference._phase_weights(hour)
        var expected:float=clampf(float(weights.night)+0.5*(float(weights.dawn)+float(weights.dusk)),0.0,1.0)
        t.advance(hour,0.0,0.0);check(is_equal_approx(t.night_level,expected),"actual original phase implementation:"+str(minute))
    t.storm=1.0
    var saved:float=t.storm
    for bad in [NAN,INF,-1.0]:t.advance(12.0,1.0,bad)
    check(t.storm==saved,"invalid elapsed time cannot jump lighting")
    t.reset_session();t.advance(12.0,1.0,1000000.0);check(t.storm<0.023,"stalled frame cannot instantly flash a full storm")
    t.apply_request({"on":false,"player_generation":7},7,true);t.reset_session();check(t.enabled and t.storm==0.0 and not t.clock_known,"session reset leaves no stale light or storm state")
    var result:={"passed":failures.is_empty(),"checks":checks,"failures":failures,"candidate_only":true,"installed":false}
    FileAccess.open(folder.path_join("state_tests.json"),FileAccess.WRITE).store_string(JSON.stringify(result));print(JSON.stringify(result));quit(0 if failures.is_empty() else 1)
