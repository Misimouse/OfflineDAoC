extends RefCounted
## Decoded Riding 0xC8 only: this module never creates mounts or consumes tickets.
const MAX_RIDERS:=128
var revision:=0
var local_oid:=0
var local_steed:=0
var local_slot:=0
var riders:Dictionary={}
var waiting_since:=0
var pending_dismount:=false
var last_request_at:=-2000
var request_count:=0
var feedback:=""
func _uint(value:Variant,maximum:int)->bool:
    return (value is int or value is float) and is_finite(float(value)) and float(value)==floor(float(value)) and float(value)>=0 and float(value)<=maximum
func reset(oid:int=0)->void:
    revision+=1;local_oid=oid;local_steed=0;local_slot=0;riders.clear();waiting_since=0;pending_dismount=false;last_request_at=-2000;feedback=""
func consume(kind:String,data:Dictionary,now:int)->bool:
    if kind in ["you","region_changed","quit"]:
        var oid:Variant=data.get("oid",0) if kind=="you" else 0
        reset(int(oid) if _uint(oid,65535) else 0);return true
    if kind=="death" and data.get("oid",0)==local_oid:
        local_steed=0;local_slot=0;pending_dismount=false;revision+=1;return true
    if kind=="remove":
        var removed:Variant=data.get("oid",0)
        if not _uint(removed,65535):return false
        var changed:=false
        for rider in riders.keys():
            if rider==int(removed) or riders[rider].steed==int(removed):riders.erase(rider);changed=true
        if changed:revision+=1
        if local_steed==int(removed):
            # Lost steed requests real dismount; do not invent a server acknowledgement.
            waiting_since=mini(waiting_since,now-5001);revision+=1
        return true
    if kind!="riding":return false
    for key in ["rider","steed","mount","slot"]:
        if not _uint(data.get(key,null),1 if key=="mount" else 255 if key=="slot" else 65535):return false
    var rider:=int(data.rider);var steed:=int(data.steed)
    if rider==0 or (int(data.mount)==1 and (steed==0 or rider==steed)):return false
    if rider==local_oid and local_oid>0:
        if int(data.mount)==0:
            # An old dismount for a different steed cannot detach the current mount.
            if local_steed!=0 and steed!=local_steed:return false
            if local_steed==0:return true
            local_steed=0;local_slot=0;pending_dismount=false;feedback="";revision+=1;return true
        if local_steed==steed and local_slot==int(data.slot):return true
        local_steed=steed;local_slot=int(data.slot);waiting_since=now;pending_dismount=false;last_request_at=-2000;revision+=1;return true
    if int(data.mount)==0:
        if riders.has(rider) and riders[rider].steed==steed:riders.erase(rider);revision+=1
        return true
    if not riders.has(rider) and riders.size()>=MAX_RIDERS:return false
    var row:={"steed":steed,"slot":int(data.slot)}
    if riders.get(rider,{})!=row:riders[rider]=row;revision+=1
    return true
func request_dismount(client:Node,now:int)->bool:
    if local_steed==0 or client==null or now-last_request_at<1500:return false
    client.call("Dismount");pending_dismount=true;last_request_at=now;request_count+=1;revision+=1;return true
func _ready_steed(id:String,entities:Dictionary)->bool:
    var row:Dictionary=entities.get(id,{})
    var hp:Variant=row.get("health",1.0)
    return not id.is_empty() and row.get("kind","")=="npc" and (hp is int or hp is float) and is_finite(float(hp)) and float(hp)>0 and row.get("state","")!="dead"
func unavailable(entities:Dictionary,ids:Dictionary,now:int)->bool:
    if local_steed==0:return false
    var id:=String(ids.get(local_steed,""))
    if _ready_steed(id,entities):return false
    return now-waiting_since>5000
func snapshot(ids:Dictionary,entities:Dictionary)->Dictionary:
    var id:=String(ids.get(local_steed,""));var ready:=local_steed>0 and _ready_steed(id,entities)
    var remote:Array=[]
    for rider in riders:
        var rid:=String(ids.get(rider,""));var sid:=String(ids.get(riders[rider].steed,""))
        if not rid.is_empty() and not sid.is_empty() and entities.has(rid) and _ready_steed(sid,entities):remote.append({"rider_entity_id":rid,"steed_entity_id":sid,"slot":riders[rider].slot})
    return {"revision":revision,"mounted":local_steed>0,"steed_oid":local_steed,"steed_entity_id":id if ready else "","steed_ready":ready,"slot":local_slot,"state_flags":0x18 if local_steed>0 else 0,"dismount_pending":pending_dismount,"remote":remote}

func speed_limit(entities:Dictionary,ids:Dictionary)->float:
    var row:Dictionary=entities.get(String(ids.get(local_steed,"")),{})
    var speed:Variant=row.get("speed_mps",0.0)
    if not (speed is int or speed is float) or not is_finite(float(speed)):return 0.0
    return clampf(absf(float(speed)),0,37.5)
func position_allowed(point:Vector3,entities:Dictionary,ids:Dictionary,now:int)->bool:
    var id:=String(ids.get(local_steed,""))
    if not point.is_finite() or not _ready_steed(id,entities):return false
    var row:Dictionary=entities[id];var p:Variant=row.get("position_m",[])
    if not p is Array or p.size()!=3:return false
    for value in p:
        if not (value is int or value is float) or not is_finite(float(value)):return false
    var anchor:=Vector3(p[0],p[1],p[2]);var motion:Dictionary=row.get("motion",{})
    var age:=clampf(float(now-int(motion.get("at_ms",now)))/1000.0,0,10)
    var speed:=speed_limit(entities,ids);var forward:Variant=row.get("forward_xz",[0,0])
    if not forward is Array or forward.size()!=2:return false
    for value in forward:
        if not (value is int or value is float) or not is_finite(float(value)):return false
    var direction:=Vector3(forward[0],0,forward[1]).normalized();var length:=speed*minf(age,1.0)
    var destination:Variant=motion.get("destination_m",[])
    if destination is Array and destination.size()==3:
        for value in destination:
            if not (value is int or value is float) or not is_finite(float(value)):return false
        var delta:=Vector3(destination[0],anchor.y,destination[2])-anchor
        direction=delta.normalized();length=minf(delta.length(),speed*age)
    var predicted:=anchor+direction*length
    var interval:=clampf(float(motion.get("interval_ms",500))/1000.0,0,.8)
    var tolerance:=maxf(4.0,speed*interval+2.0)
    return Vector2(point.x-predicted.x,point.z-predicted.z).length()<=tolerance and absf(point.y-anchor.y)<=8.0
