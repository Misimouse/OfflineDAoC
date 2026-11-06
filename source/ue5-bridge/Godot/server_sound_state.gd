extends RefCounted
## Server SoundEffect packets, separate from predicted spells and ambient audio.
var sounds:Dictionary={}
var events:Array=[]
var sequence:=0

func configure(rows:Dictionary)->void:
    sounds=rows;reset()
func reset()->void:
    events.clear()
func consume(kind:String,data:Dictionary,zone:int,local:Vector3,now:int)->void:
    if kind in ["you","region_changed","quit"]:reset();return
    if kind!="sound_effect" or zone!=207 or not local.is_finite():return
    for key in ["id","zone","x","y","z","radius"]:
        var value=data.get(key)
        if not (value is int or value is float) or not is_finite(float(value)) or float(value)!=floor(float(value)) or value<0 or value>65535:return
    var id:=int(data.id)
    if not sounds.has(str(id)):return
    var placed:bool=int(data.zone)>0 and int(data.radius)>0
    var point:=Vector3(float(data.x)*.025,float(data.z)*.025,float(data.y)*.025)
    var radius:=float(data.radius)*.025
    # The current bridge renders Connacht only; do not invent another zone's origin.
    if placed and (int(data.zone)!=zone or local.distance_to(point)>radius):return
    sequence+=1
    events.append({"seq":sequence,"at_ms":now,"sound_id":id,"placed":placed,
        "position_m":[point.x,point.y,point.z],"radius_m":radius})
    if events.size()>128:events.pop_front()
func snapshot(now:int)->Array:
    var out:Array=[]
    for row in events:
        var age:=now-int(row.at_ms)
        if age<0 or age>1000:continue
        var event:Dictionary=row.duplicate(true);event.erase("at_ms");event["age_ms"]=age;out.append(event)
    return out
