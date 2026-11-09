extends RefCounted
## A client-requested point, not a server acknowledgement of navigation validity.
var point:Variant=null
var revision:=0
var sight_at:=-10000
var sight:=false
var last_request:=-1000
var feedback:=""

func integer(value:Variant,minimum:int,maximum:int)->int:
    if not (value is int or value is float) or not is_finite(float(value)) or float(value)!=floor(float(value)) or float(value)<minimum or float(value)>maximum:return -1
    return int(value)

func reset()->void:
    point=null;revision+=1;sight=false;sight_at=-10000;last_request=-1000;feedback=""

func consume(kind:String)->void:
    if kind in ["you","quit","region_changed"]:reset()

func visible(now:int)->bool:
    return point is Vector3 and sight and now>=sight_at and now-sight_at<=1500

func request(value:Dictionary,server:Node,position:Vector3,now:int)->bool:
    if String(value.get("action",""))!="ground_target":return false
    if server==null or not bool(server.get("playing")) or not position.is_finite() or now-last_request<180:return false
    var client:Variant=server.get("client")
    if not client is Node or not client.has_method("GroundTarget") or not server.has_method("to_region"):return false
    var raw:Variant=value.get("position_m");var in_view:Variant=value.get("visible")
    if not raw is Array or raw.size()!=3 or not in_view is bool:return false
    for n in raw:
        if not (n is int or n is float) or not is_finite(float(n)):return false
    var next:=Vector3(float(raw[0]),float(raw[1]),float(raw[2]))
    if next.distance_to(position)>250.0:return false
    var entry:Variant=server.get("entry")
    if not entry is Dictionary:return false
    var zone:=integer(entry.get("zone"),0,65535)
    if zone<0:return false
    var region:Variant=server.call("to_region",zone,next)
    if not region is Vector3 or not region.is_finite() or region.x<0 or region.y<0 or region.x>2147483000 or region.y>2147483000 or absf(region.z)>2147483000:return false
    client.call("GroundTarget",roundi(region.x),roundi(region.y),roundi(region.z),0x100 if in_view else 0)
    point=next;revision+=1;sight=in_view;sight_at=now;last_request=now;feedback="";return true

func update_visibility(value:Dictionary,now:int)->bool:
    if not point is Vector3 or integer(value.get("ground_target_revision"),0,2147483647)!=revision:return false
    var in_view:Variant=value.get("ground_target_in_view")
    if not in_view is bool:return false
    sight=in_view;sight_at=now;return true

func flags(now:int)->int:return 0x08 if visible(now) else 0

func snapshot(now:int)->Dictionary:
    return {"revision":revision,"has_point":point is Vector3,"position_m":[point.x,point.y,point.z] if point is Vector3 else [],"visible":visible(now),"server_acknowledged":false,"feedback":feedback}
