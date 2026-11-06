extends RefCounted
## Audio announcements from authoritative packets. Never changes HP, AI or gear.
const SPELL_RESULT:=0x14
const BOW_PREPARE:=0x3E80
const BOW_SHOOT:=0x3E83
const WEAPONLESS:=19
const PAIN_MS:=700
var model_sets:Dictionary={}
var weapon_models:Dictionary={}
var events:Array=[]
var sequence:=0
var health:Dictionary={}
var pain_at:Dictionary={}
var dead:Dictionary={}

func configure(models:Dictionary,weapons:Dictionary)->void:
    model_sets=models;weapon_models=weapons
func reset()->void:
    events.clear();health.clear();pain_at.clear();dead.clear()
func identify(oid:int,me:int,ids:Dictionary)->String:
    if oid<=0 or oid>65535:return ""
    return "player:local" if oid==me else String(ids.get(oid,""))
func percentage(value)->int:
    if not (value is int or value is float) or not is_finite(float(value)):return -1
    if float(value)!=floor(float(value)) or value<0 or value>100:return -1
    return int(value)
func weapon_set(model:int)->int:
    return int(weapon_models.get(str(model),{}).get("sound_set",0))
func emit(owner:String,entities:Dictionary,sheet:String,set_id:int,event:String,now:int)->void:
    if owner.is_empty() or not entities.has(owner) or set_id<=0:return
    var row:Dictionary=entities[owner]
    if not row.has("position_m"):return
    sequence+=1
    events.append({"seq":sequence,"at_ms":now,"owner":owner,"sheet":sheet,"set":set_id,
        "event":event,"position_m":row.position_m.duplicate(),"model_id":int(row.get("model_id",0))})
    if events.size()>128:events.pop_front()
func creature(owner:String,entities:Dictionary,event:String,now:int)->void:
    if not entities.has(owner):return
    emit(owner,entities,"creatures",int(model_sets.get(str(int(entities[owner].get("model_id",0))),0)),event,now)
func pain(owner:String,entities:Dictionary,event:String,now:int)->void:
    if now-int(pain_at.get(owner,-100000))<PAIN_MS:return
    pain_at[owner]=now;creature(owner,entities,event,now)
func death(owner:String,entities:Dictionary,now:int)->void:
    if owner.is_empty() or dead.has(owner):return
    dead[owner]=true;health[owner]=0
    creature(owner,entities,"die",now)
func before_health(owner:String,entities:Dictionary)->int:
    if health.has(owner):return int(health[owner])
    var row:Dictionary=entities.get(owner,{})
    if not bool(row.get("health_known",false)):return -1
    return percentage(roundi(float(row.get("health",1))*100))

## Call before adapters overwrite the defender's health from this packet.
func consume(kind:String,data:Dictionary,me:int,ids:Dictionary,entities:Dictionary,now:int)->void:
    if kind in ["you","region_changed","quit"]:reset();return
    var owner:=identify(int(data.get("oid",0)),me,ids)
    if kind in ["npc","player","revive"]:
        var oid:=int(data.get("oid",0))
        if kind in ["npc","player"] and oid>0 and oid<=65535 and oid!=me:owner=kind+":"+str(oid)
        if not owner.is_empty():
            dead.erase(owner);pain_at.erase(owner)
            var value:=percentage(data.get("health",-1))
            if value>=0:health[owner]=value
            else:health.erase(owner)
        return
    if kind=="death":death(owner,entities,now);return
    if kind=="remove":
        # Despawn is never invented as a death. Queued sounds retain their location.
        health.erase(owner);pain_at.erase(owner);return
    if kind!="combat":return
    if int(data.get("style",0))==BOW_PREPARE:return
    var attacker:=identify(int(data.get("attacker",0)),me,ids)
    var defender:=identify(int(data.get("defender",0)),me,ids)
    var result:=int(data.get("result",0))
    var spell:bool=(result&0x7F)==SPELL_RESULT
    var weapon:=int(data.get("weapon",0));var ws:=weapon_set(weapon)
    var style:=int(data.get("style",0))
    var styled:bool=style>0 and style not in [BOW_SHOOT,0x3E81,0x3E82] and result==11
    var attacker_row:Dictionary=entities.get(attacker,{})
    var attacker_dead:bool=String(attacker_row.get("state",""))=="dead" or float(attacker_row.get("health",1))<=0
    if not spell and not dead.has(attacker) and not attacker_dead:
        if ws>0:emit(attacker,entities,"weapons",ws,"style_use" if styled else "use",now)
        else:creature(attacker,entities,"attack",now)
    var after:=percentage(data.get("health",-1))
    var before:=before_health(defender,entities)
    var heavy:bool=before>=0 and after>=0 and before-after>=10
    if not dead.has(defender):
        if spell:
            if after>0:pain(defender,entities,"pain_medium" if heavy else "pain_light",now)
        elif result in [1,2]:
            var defence:=weapon_set(int(data.get("shield",0)))
            emit(defender,entities,"weapons",defence if defence>0 else WEAPONLESS,"parried" if result==1 else "blocked",now)
        elif result==3:creature(defender,entities,"evade",now)
        elif result in [10,11]:
            emit(defender,entities,"weapons",ws if ws>0 else WEAPONLESS,"style_hit" if result==11 else ("hit_medium" if heavy else "hit_light"),now)
            if after>0:pain(defender,entities,"pain_heavy" if result==11 else ("pain_medium" if heavy else "pain_light"),now)
        if after==0:death(defender,entities,now)
    if after>=0 and not defender.is_empty():health[defender]=after

func snapshot(now:int)->Array:
    var out:Array=[]
    for value in events:
        var age:int=now-int(value.at_ms)
        if age<0 or age>2000:continue
        var row:Dictionary=value.duplicate(true);row.erase("at_ms");row.age_ms=age;out.append(row)
    return out
