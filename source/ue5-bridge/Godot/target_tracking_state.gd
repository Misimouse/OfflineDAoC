extends RefCounted
## Client-only target tracking. This never asks the server to move bots or teleport.
const MODES:=["face","follow","stick"]
const START_RANGE:=25.0
var serial:=0
var mode:=""
var entity_id:=""
var target_name:=""
var requested_at:=0
var pending:=false
var active:=false
var feedback:=""
func reset()->void:
    serial+=1;mode="";entity_id="";target_name="";pending=false;active=false;feedback=""
func stop()->void:
    var message:="You are no longer %s %s." % [{"follow":"following","stick":"sticking to","face":"facing"}.get(mode,"tracking"),target_name] if active else ""
    reset();feedback=message
func request(wanted:String,selected:String,entities:Dictionary,position:Vector3,ready:bool,now:int)->bool:
    feedback=""
    if wanted not in MODES:return false
    if not ready:feedback="You cannot %s right now." % wanted;return false
    if selected.is_empty() or not entities.has(selected):feedback="You must select a target to %s!" % wanted;return false
    if selected=="player:local":feedback="You can't %s yourself!" % wanted;return false
    var row:Dictionary=entities[selected]
    if row.get("kind","") not in ["npc","player"] or float(row.get("health",1))<=0 or not bool(row.get("targetable",true)):
        feedback="You must select a living target to %s!" % wanted;return false
    var p=row.get("position_m",[])
    if not p is Array or p.size()!=3:return false
    for value in p:
        if not (value is int or value is float) or not is_finite(float(value)):return false
    var name:=String(row.get("name",selected)).left(128)
    if wanted!="face" and position.distance_to(Vector3(p[0],p[1],p[2]))>START_RANGE:
        feedback="%s is too far away to %s." % [name,wanted];return false
    reset();mode=wanted;entity_id=selected;target_name=name;requested_at=now;pending=true;return true
func consume(value:Dictionary)->bool:
    var seq=value.get("request_seq",null)
    if not (seq is float or seq is int) or not is_finite(float(seq)) or float(seq)!=float(serial) or mode.is_empty():return false
    if String(value.get("target_entity_id",""))!=entity_id:return false
    var result:=String(value.get("result",""))
    if result=="started" and pending:
        pending=false;active=true;feedback="You are now %s %s." % [{"follow":"following","stick":"sticking to","face":"facing"}[mode],target_name];return true
    if result=="stopped" and (pending or active):stop();return true
    if result=="rejected" and pending:
        var text:="Unable to %s %s." % [mode,target_name];reset();feedback=text;return true
    return false
func maintain(entities:Dictionary,ready:bool,now:int)->void:
    if mode.is_empty():return
    if not ready or not entities.has(entity_id) or float(entities.get(entity_id,{}).get("health",1))<=0:stop();return
    if pending and now-requested_at>5000:
        var text:="Unable to %s %s." % [mode,target_name];reset();feedback=text
func take_feedback()->String:
    var text:=feedback;feedback="";return text
func snapshot(now:int)->Dictionary:
    return {"request_seq":serial,"mode":mode,"target_entity_id":entity_id,"target_name":target_name,"age_ms":maxi(0,now-requested_at),"pending":pending,"active":active}
