extends RefCounted
## Transient visual announcements from original packets. No hit, damage, cost or AI simulation.
var events:Array=[]
var sequence:=0
var entered_at:=0
var active:Dictionary={}
const SIEGE_EFFECTS:={2645:[2202],2604:[2202],2598:[2204],2599:[2204],2606:[2204],2607:[2209]}
var siege_models:Dictionary={}
var siege_effects:Dictionary={}
func configure_siege(models:Dictionary,effects:Dictionary)->void:siege_models=models;siege_effects=effects
func siege_integer(value:Variant)->int:
    if typeof(value) not in [TYPE_INT,TYPE_FLOAT] or not is_finite(float(value)) or float(value)!=floor(float(value)) or float(value)<0 or float(value)>4294967295:return -1
    return int(value)
func consume_siege(data:Dictionary,ids:Dictionary,entities:Dictionary,zone:Dictionary,now:int)->void:
    if siege_integer(data.get("action",-1))!=4:return
    var oid:=siege_integer(data.get("oid",-1));var id:String=String(ids.get(oid,""))
    if id.is_empty() or not entities.has(id):return
    var row:Dictionary=entities[id];var model:=int(row.get("model_id",0));var effect:=siege_integer(data.get("effect",-1));var delay:=siege_integer(data.get("timer",-1))
    if not bool(siege_models.get(str(model),{}).get("siege",false)) or effect not in SIEGE_EFFECTS.get(model,[]) or delay<0 or delay>65535:return
    var definition:Dictionary=siege_effects.get(str(effect),{})
    if int(definition.get("target",0))<=0:return
    var x:=siege_integer(data.get("x",-1));var y:=siege_integer(data.get("y",-1));var z:=siege_integer(data.get("z",-1))
    if not zone.has("x") or not zone.has("y"):return
    var origin_x:float=float(zone.x)*8192.0;var origin_y:float=float(zone.y)*8192.0
    if not is_finite(origin_x) or not is_finite(origin_y):return
    if x<origin_x or x>origin_x+65536 or y<origin_y or y>origin_y+65536 or z<0 or z>65535:return
    var point:Array=[(x-origin_x)*.025,z*.025,(y-origin_y)*.025]
    append({"kind":"world_impact","caster":id,"effect_id":effect,"position_m":point,"delay_ms":delay,"ttl_ms":delay+8000},now)

func reset(now:int=0)->void:events.clear();active.clear();entered_at=now
func identify(oid:int,me:int,ids:Dictionary)->String:return "player:local" if oid>0 and oid==me else String(ids.get(oid,""))
func consume(kind:String,d:Dictionary,me:int,ids:Dictionary,now:int)->void:
    if kind in ["you","region_changed","quit"]:reset(now);return
    if kind in ["remove","death"]:
        var gone:=identify(int(d.get("oid",0)),me,ids)
        active.erase(gone)
        if not gone.is_empty():append({"kind":"cancel","caster":gone,"reason":kind},now)
        return
    if kind not in ["cast","spell_effect","interrupt"]:return
    var caster:=identify(int(d.get("caster",0)),me,ids)
    if caster.is_empty():return
    if kind=="interrupt":active.erase(caster);append({"kind":"cancel","caster":caster,"reason":"interrupt"},now);return
    var effect:=int(d.get("spell",0))
    if effect<=0:return
    if kind=="cast":
        var duration:=int(d.get("time",0))*100
        if duration<0 or duration>3600000:return
        active[caster]=effect
        append({"kind":"cast","caster":caster,"effect_id":effect,"duration_ms":duration},now)
    else:
        var target:=identify(int(d.get("target",0)),me,ids)
        var was_cast:=active.has(caster)
        active.erase(caster)
        if not was_cast and caster=="player:local" and target==caster and now-entered_at<3000:return
        append({"kind":"release","caster":caster,"target":target,"effect_id":effect,"resisted":int(d.get("success",1))==0,"bolt":int(d.get("bolt",0)),"no_sound":int(d.get("no_sound",0))!=0},now)
func append(row:Dictionary,now:int)->void:
    sequence+=1;row["seq"]=sequence;row["at_ms"]=now;events.append(row)
    if events.size()>96:events.pop_front()
func snapshot(now:int)->Array:
    var out:Array=[]
    for i in range(events.size()-1,-1,-1):
        if now<int(events[i].at_ms) or now-int(events[i].at_ms)>int(events[i].get("ttl_ms",8000)):events.remove_at(i)
    for row in events:
        var copy:Dictionary=row.duplicate(true);copy["age_ms"]=maxi(0,now-int(copy.at_ms));copy.erase("at_ms");copy.erase("ttl_ms");out.append(copy)
    return out
