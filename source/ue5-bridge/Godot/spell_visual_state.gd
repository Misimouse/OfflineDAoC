extends RefCounted
## Transient visual announcements from original packets. No hit, damage, cost or AI simulation.
var events:Array=[]
var sequence:=0
var entered_at:=0
var active:Dictionary={}
func reset(now:int=0)->void:events.clear();active.clear();entered_at=now
func identify(oid:int,me:int,ids:Dictionary)->String:return "player:local" if oid>0 and oid==me else String(ids.get(oid,""))
func consume(kind:String,d:Dictionary,me:int,ids:Dictionary,now:int)->void:
    if kind in ["you","region_changed","quit"]:reset(now);return
    if kind in ["remove","death"]:
        var gone:=identify(int(d.get("oid",0)),me,ids)
        active.erase(gone)
        if not gone.is_empty():append({"kind":"cancel","caster":gone},now)
        return
    if kind not in ["cast","spell_effect","interrupt"]:return
    var caster:=identify(int(d.get("caster",0)),me,ids)
    if caster.is_empty():return
    if kind=="interrupt":active.erase(caster);append({"kind":"cancel","caster":caster},now);return
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
        append({"kind":"release","caster":caster,"target":target,"effect_id":effect,"resisted":int(d.get("success",1))==0,"bolt":int(d.get("bolt",0))},now)
func append(row:Dictionary,now:int)->void:
    sequence+=1;row["seq"]=sequence;row["at_ms"]=now;events.append(row)
    if events.size()>96:events.pop_front()
func snapshot(now:int)->Array:
    var out:Array=[]
    while not events.is_empty() and now-int(events[0].at_ms)>8000:events.pop_front()
    for row in events:
        var copy:Dictionary=row.duplicate(true);copy["age_ms"]=maxi(0,now-int(copy.at_ms));copy.erase("at_ms");out.append(copy)
    return out
