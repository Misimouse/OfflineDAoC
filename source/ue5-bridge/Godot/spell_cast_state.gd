extends RefCounted
## Presentation of actual SpellCastAnimation/Interrupt/SpellEffectAnimation. No spell rules or local results.
var casts:Dictionary={}
var dead:Dictionary={}
var definitions:Dictionary={}
var sequence:=0
var packets:=0
func configure(source:Dictionary)->void:definitions=source.get("effects",{})
func reset()->void:casts.clear();dead.clear()
func entity(oid:int,me:int,ids:Dictionary)->String:return "player:local" if oid>0 and oid==me else String(ids.get(oid,""))
func consume(kind:String,d:Dictionary,me:int,ids:Dictionary,now:int)->void:
    if kind in ["you","region_changed","quit"]:reset();return
    if kind in ["death","remove","revive"]:
        var changed:=entity(int(d.get("oid",0)),me,ids);casts.erase(changed)
        if kind=="death":dead[changed]=true
        else:dead.erase(changed)
        return
    if kind not in ["cast","spell_effect","interrupt"]:return
    var id:=entity(int(d.get("caster",0)),me,ids)
    if id.is_empty() or bool(dead.get(id,false)):return
    packets+=1
    if kind=="cast":
        var effect:=int(d.get("spell",0));var tenths:=int(d.get("time",0))
        if effect<=0 or tenths<0 or tenths>36000:return
        sequence+=1;var def:Dictionary=definitions.get(str(effect),{})
        casts[id]={"seq":sequence,"effect_id":effect,"name":String(def.get("name","Spell")),"anims":def.get("anims",[]).duplicate(),"phase":"casting" if tenths>0 else "instant","duration_ms":tenths*100,"at_ms":now,"instant":tenths==0}
    elif kind=="interrupt":
        if not casts.has(id) or casts[id].phase not in ["casting","instant"]:return
        sequence+=1;casts[id].seq=sequence;casts[id].phase="interrupted";casts[id].at_ms=now
    elif casts.has(id) and int(casts[id].effect_id)==int(d.get("spell",0)) and casts[id].phase in ["casting","instant"]:
        sequence+=1;casts[id].seq=sequence;casts[id].phase="released";casts[id].at_ms=now;casts[id]["resisted"]=int(d.get("success",1))==0
func snapshot(id:String,now:int)->Dictionary:
    if not casts.has(id):return {}
    var c:Dictionary=casts[id].duplicate(true);var age:=maxi(0,now-int(c.at_ms));c.erase("at_ms");c["age_ms"]=age
    if c.phase=="casting" and age>int(c.duration_ms)+1500:c.phase="unconfirmed"
    if c.phase in ["interrupted","released","instant"] and age>2500:return {}
    if c.phase=="unconfirmed" and age>int(c.duration_ms)+4000:return {}
    return c
