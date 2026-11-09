extends RefCounted
## Candidate only: original personal light state; does not alter world or building lighting.
const PHASE_KEYS := [[0.0,"night"],[4.5,"night"],[6.0,"dawn"],[7.5,"day"],[16.5,"day"],[18.0,"dusk"],[19.5,"night"],[24.0,"night"]]
var enabled:=true
var storm:=0.0
var clock_known:=false
var night_level:=0.0
var revision:=0
func reset_session()->void:
    enabled=true;storm=0.0;clock_known=false;night_level=0.0;revision+=1
func apply_request(value:Dictionary,generation:int,ready:bool)->bool:
    if not ready or not value.get("on") is bool:return false
    var epoch:Variant=value.get("player_generation")
    if typeof(epoch) not in [TYPE_INT,TYPE_FLOAT] or not is_finite(float(epoch)) or float(epoch)!=float(generation):return false
    if enabled!=value.on:enabled=value.on;revision+=1
    return true
func action_flags(original:int)->int:
    return (original&~0x80)|(0x80 if enabled else 0)
func advance(hour:float,storm_target:float,delta:float)->void:
    clock_known=is_finite(hour) and hour>=0.0 and hour<24.0
    if not is_finite(storm_target) or storm_target<0.0 or storm_target>1.0:storm_target=0.0
    if not is_finite(delta) or delta<0.0:delta=0.0
    storm=move_toward(storm,storm_target,minf(delta,1.0)/45.0)
    night_level=0.0
    if not clock_known:return
    for i in range(PHASE_KEYS.size()-1):
        var a:Array=PHASE_KEYS[i];var b:Array=PHASE_KEYS[i+1]
        if hour<float(a[0]) or hour>float(b[0]):continue
        var t:float=(hour-float(a[0]))/maxf(float(b[0])-float(a[0]),0.001)
        t=t*t*(3.0-2.0*t)
        var weights:={"night":0.0,"dawn":0.0,"day":0.0,"dusk":0.0}
        weights[a[1]]+=1.0-t;weights[b[1]]+=t
        night_level=clampf(float(weights.night)+0.5*(float(weights.dawn)+float(weights.dusk))+storm*0.3,0.0,1.0)
        break
func snapshot()->Dictionary:
    return {"enabled":enabled,"clock_known":clock_known,"night_level":night_level,"energy_scale":0.15+0.85*night_level,"revision":revision}
