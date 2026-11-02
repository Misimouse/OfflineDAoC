extends RefCounted
## Visual announcements from actual CombatAnimation packets, never damage or AI.
## Body animation only; networking and HP remain in their original authority.
const STANCES:={2:"2h",3:"pole",4:"staff",5:"bow",6:"xbow",7:"1ht",8:"throw",9:"fws",10:"fwm",11:"fwl",13:"h2h",14:"scy"}
var catalog:Dictionary={}
var weapons:Dictionary={}
var style_anims:Dictionary={}
var style_clips:Dictionary={}
var events:Dictionary={}
var fighting:Dictionary={}
var sequence:=0
var packets:=0
var emitted:=0
var suppressed_ranged:=0

func configure(models:Dictionary,weapon_definitions:Dictionary,styles:Dictionary,clips:Dictionary)->void:
    catalog=models;weapons=weapon_definitions;style_anims=styles;style_clips=clips
func reset()->void:events.clear();fighting.clear()
func remove(id:String)->void:events.erase(id);fighting.erase(id)
func prune(entities:Dictionary)->void:
    for id in events.keys():
        if not entities.has(id):events.erase(id)
    for id in fighting.keys():
        if not entities.has(id):fighting.erase(id)
func stance(model:int)->String:return String(STANCES.get(int(weapons.get(str(model),{}).get("stance",1)),""))
func available(model:int,clip:String)->bool:return not clip.is_empty() and catalog.get(str(model),{}).has(clip)
func stance_clip(model:int,weapon_stance:String,base:String)->String:
    if weapon_stance.is_empty():return base
    var variant:=""
    if weapon_stance=="xbow" and base=="combat_idle":variant="xbow_idle"
    elif base.begins_with("attack_"):
        if weapon_stance not in ["bow","xbow","throw"]:variant=base.replace("attack_","attack_"+weapon_stance+"_")
    else:variant=base+"_"+weapon_stance
    return variant if available(model,variant) else base
func attack_clip(model:int,weapon_stance:String,hand:String="")->String:
    var level:String=["med","high","low"][randi()%3]
    var alternate:="attack_"+hand+"_"+level
    if not hand.is_empty() and available(model,alternate):return alternate
    return stance_clip(model,weapon_stance,"attack_"+level)
func defend_clip(model:int,weapon_stance:String,kind:String)->String:
    var height:String=["low","high"][randi()%2]
    var family:String={"2h":"2h","scy":"2h","pole":"pole","staff":"pole"}.get(weapon_stance,"")
    var wanted:=""
    if kind=="parry":wanted="parry_"+weapon_stance if weapon_stance in ["fws","fwm","fwl"] else ("parry_"+family+"_"+height if not family.is_empty() else "parry_"+height)
    elif kind=="evade":wanted="evade_"+family if not family.is_empty() else "evade"
    elif kind=="block":wanted="block_"+height
    if available(model,wanted):return wanted
    var plain:String={"parry":"parry_"+height,"evade":"evade","block":"block_"+height}.get(kind,"")
    return plain if available(model,plain) else ""
func _id(oid:int,me:int,oid_to_id:Dictionary)->String:
    if oid<=0 or oid>65535:return ""
    return "player:local" if oid==me else String(oid_to_id.get(oid,""))
func _living(id:String,entities:Dictionary)->bool:
    var row:Dictionary=entities.get(id,{})
    return not row.is_empty() and String(row.get("state",""))!="dead" and float(row.get("health",1))>0
func _emit(id:String,row:Dictionary,clip:String,kind:String,weapon:int,style:int,now:int,if_idle:bool,packet:Dictionary)->void:
    if not available(int(row.get("model_id",-1)),clip):return
    sequence+=1;emitted+=1
    if not events.has(id):events[id]=[]
    var queue:Array=events[id]
    queue.append({"seq":sequence,"at_ms":now,"clip":clip,"kind":kind,"weapon_model":weapon,"style_id":style,"if_idle":if_idle,"source_attacker":int(packet.get("attacker",0)),"source_defender":int(packet.get("defender",0)),"result":int(packet.get("result",0))})
    if queue.size()>8:queue.pop_front()
func consume(data:Dictionary,me:int,oid_to_id:Dictionary,entities:Dictionary,now:int,local_stance:String="",local_dead:bool=false)->void:
    packets+=1
    var attacker:=_id(int(data.get("attacker",0)),me,oid_to_id)
    var defender:=_id(int(data.get("defender",0)),me,oid_to_id)
    var weapon:=int(data.get("weapon",0));var style:=int(data.get("style",0));var result:=int(data.get("result",0))
    var bow:bool=style in [0x3E80,0x3E83]
    var ranged:bool=int(weapons.get(str(weapon),{}).get("stance",0)) in [5,6,8]
    var spell:bool=(result&0x7F)==0x14
    var weapon_stance:=stance(weapon)
    if _living(attacker,entities) and not (attacker=="player:local" and local_dead) and not spell and not bow and not ranged:
        var row:Dictionary=entities[attacker];var model:=int(row.get("model_id",-1))
        var hand:String={0x3E81:"left",0x3E82:"dual"}.get(style,"")
        var styled:bool=hand.is_empty() and style>0 and result==11
        var clip:=""
        if styled:clip=String(style_clips.get(str(int(style_anims.get(str(style),0))),""))
        var actor_stance:=local_stance if attacker=="player:local" else weapon_stance
        if not available(model,clip):clip=attack_clip(model,actor_stance,hand)
        _emit(attacker,row,clip,"style" if styled else "attack",weapon,style,now,false,data)
        fighting[attacker]={"until_ms":now+6000,"weapon_model":weapon,"stance":weapon_stance}
    elif bow or ranged:suppressed_ranged+=1 # No false sword swing; bow actions are a later block.
    if style==0x3E80:return # A drawn bow cannot flinch or damage a defender.
    if _living(defender,entities) and not (defender=="player:local" and local_dead):
        var row:Dictionary=entities[defender];var model:=int(row.get("model_id",-1))
        var defender_stance:=local_stance if defender=="player:local" else String(fighting.get(defender,{}).get("stance",""))
        var kind:String={1:"parry",2:"block",3:"evade"}.get(result,"")
        if not kind.is_empty():_emit(defender,row,defend_clip(model,defender_stance,kind),kind,weapon,style,now,true,data)
        elif result>=10:_emit(defender,row,"flinch","flinch",weapon,style,now,true,data)
func snapshot(id:String,now:int)->Dictionary:
    if not events.has(id):return {}
    var queue:Array=[]
    for value in events[id]:
        var event:Dictionary=value.duplicate(true);event["age_ms"]=maxi(0,now-int(event.at_ms));event.erase("at_ms")
        if int(event.age_ms)<=5000:queue.append(event)
    return {"seq":int(queue.back().seq),"events":queue} if not queue.is_empty() else {}
