extends RefCounted
## Original decoded world objects; pickup remains entirely server-authorized.
const RELICS:=[630,631,632,633,634,635]
const LOOT_RANGE_M:=37.5
const MAX_OBJECTS:=2048
var objects:Dictionary={}
var generation:=0
var serial:=0
var active:=false
var zone_info:Dictionary={"x":35,"y":51}
var baked:Array=[]
var feedback:=""
var rejected:=0
var selection_id:=""
var selection_token:=""
func integer(value:Variant,minimum:int,maximum:int)->int:
    if not (value is int or value is float) or not is_finite(float(value)) or float(value)!=floor(float(value)) or value<minimum or value>maximum:return -1
    return int(value)
func reset()->void:generation+=1;objects.clear();active=false;feedback="";selection_id="";selection_token=""
func configure(info:Dictionary)->void:
    baked.clear()
    if info.has("x") and info.has("y"):zone_info={"x":int(info.x),"y":int(info.y)}
    for fixture in info.get("fixtures",[]):
        if not fixture is Dictionary or fixture.get("source","")!="world_object":continue
        var p:Variant=fixture.get("pos")
        if not p is Array or p.size()!=3:continue
        var point:=Vector3(float(p[0]),float(p[1]),float(p[2]))
        if point.is_finite():baked.append(point)
func position(data:Dictionary)->Vector3:
    for k in ["x","y","z"]:
        var v:Variant=data.get(k)
        if not (v is int or v is float) or not is_finite(float(v)):return Vector3.INF
    return Vector3((float(data.x)-float(zone_info.x)*8192.0)*.025,float(data.z)*.025,(float(data.y)-float(zone_info.y)*8192.0)*.025)
func inside(p:Vector3)->bool:return p.is_finite() and p.x>=0 and p.z>=0 and p.x<=1638.4 and p.z<=1638.4
func observe(kind:String,data:Dictionary)->void:
    if kind in ["region_changed","quit","disconnected"]:reset();return
    if kind=="you":
        reset();active=integer(data.get("region"),0,65535)==200 and inside(position(data));return
    var oid:=integer(data.get("oid"),1,65535)
    if oid<1:return
    var id:="object:%d"%oid
    if kind in ["npc","player","remove"]:objects.erase(id);return
    if kind!="object" or not active:return
    var previous:Dictionary=objects.get(id,{})
    objects.erase(id)
    var model:=integer(data.get("model"),0,65535);var heading:=integer(data.get("heading"),0,65535);var flags:=integer(data.get("flags"),0,65535);var emblem:=integer(data.get("emblem"),0,65535)
    var door:Variant=data.get("door");var name:Variant=data.get("name");var p:=position(data)
    if model<0 or heading<0 or flags<0 or emblem<0 or not (door is int or door is float) or not is_finite(float(door)) or float(door)!=floor(float(door)) or door < -1 or door>4294967295 or not name is String or name.length()>255 or not inside(p):return
    if int(door)>=0:return
    model&=32767;heading&=4095
    if model not in RELICS:
        for point in baked:
            if Vector2(point.x-p.x,point.z-p.z).length()<=2.0:return
    if objects.size()>=MAX_OBJECTS:return
    var signature:=JSON.stringify([generation,oid,model,p.x,p.y,p.z,heading,name,flags,emblem])
    var token:=String(previous.get("object_token",""))
    if previous.get("signature","")!=signature:serial+=1;token=(signature+":"+str(serial)).sha256_text()
    var angle:=-float(heading)*TAU/4096.0
    objects[id]={"id":id,"oid":oid,"kind":"object","model_id":model,"name":name,"position_m":[p.x,p.y,p.z],"forward_xz":[sin(angle),cos(angle)],"heading_4096":heading,"size":50,"health":1.0,"state":"idle","targetable":true,"non_living":true,"realm":-1,"nameplate":{"show":false},"emblem":emblem,"original_flags":flags,"object_token":token,"world_generation":generation,"signature":signature}
func entities(living:Dictionary)->Dictionary:
    var combined:=living.duplicate()
    for id in objects:combined[id]=objects[id]
    return combined
func point(row:Dictionary)->Vector3:
    var p:Array=row.position_m;return Vector3(p[0],p[1],p[2])
func view(pos:Vector3,limit:int=128,range_m:float=150.0)->Array:
    if not active or not inside(pos) or limit<1:return []
    var rows:Array=[]
    for row in objects.values():
        if pos.distance_squared_to(point(row))<=range_m*range_m:rows.append(row)
    rows.sort_custom(func(a,b):return pos.distance_squared_to(point(a))<pos.distance_squared_to(point(b)))
    var out:Array=[]
    for row in rows.slice(0,mini(limit,128)):
        var copy:Dictionary=row.duplicate(true);copy.erase("signature");out.append(copy)
    return out
func nearest_loot(pos:Vector3)->String:
    if not active or not inside(pos):return ""
    var best:="";var distance:=LOOT_RANGE_M
    for id in objects:
        var row:Dictionary=objects[id]
        if String(row.name).contains("'s Grave"):continue
        var d:=pos.distance_to(point(row))
        if d<=distance:best=id;distance=d
    return best
func fail(text:String)->bool:feedback=text;rejected+=1;return false
func request(value:Dictionary,client:Node,interaction:RefCounted,living:Dictionary,pos:Vector3,alive:bool,player_zone:int)->bool:
    if not active or player_zone!=207 or not inside(pos) or client==null or integer(value.get("world_generation"),0,2147483647)!=generation:return fail("That world state is no longer available.")
    var action:=String(value.get("action",""));var id:=""
    if action=="target_loot":id=nearest_loot(pos)
    else:
        if not value.get("entity_id") is String:return fail("Select an object on the ground.")
        id=String(value.entity_id)
    var row:Dictionary=objects.get(id,{})
    if row.is_empty():return fail("No lootable object in range." if action=="target_loot" else "That object is no longer available.")
    if action!="target_loot" and (not value.get("object_token") is String or value.object_token!=row.object_token):return fail("That object has changed. Select it again.")
    if action in ["target_object","target_loot"]:
        feedback=""
        var accepted:bool=interaction.execute({"action":"target","entity_id":id},client,entities(living),pos)
        if accepted:selection_id=id;selection_token=String(row.object_token)
        return accepted
    if action!="get_object":return false
    if not alive:return fail("You cannot pick up objects while dead.")
    if interaction.selected_id!=id or selection_id!=id or selection_token!=row.object_token:return fail("Select that object first.")
    # DOL pickup acts on TargetObject, not merely the supplied OID. Pin that
    # target immediately before the original request; await its inventory/delete.
    var rx:=int(pos.x*40.0+float(zone_info.x)*8192.0);var ry:=int(pos.z*40.0+float(zone_info.y)*8192.0)
    client.call("Target",int(row.oid),0xE000)
    if int(row.model_id) in RELICS:client.call("Interact",int(row.oid),rx,ry)
    else:client.call("PickUp",rx,ry,int(row.oid))
    feedback="";return true
