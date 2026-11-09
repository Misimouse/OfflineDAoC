extends RefCounted
## Control is granted only by the original server interface packet.
var current:Dictionary={}
var revision:=0
var visible:=false
var last_command:=-1000
var received_at:=0
var feedback:=""

func integer(value:Variant,minimum:int,maximum:int)->int:
    if not (value is int or value is float) or not is_finite(float(value)) or float(value)!=floor(float(value)) or float(value)<minimum or float(value)>maximum:return -1
    return int(value)

func reset()->void:
    current.clear();visible=false;last_command=-1000;received_at=0;feedback="";revision+=1

func consume(kind:String,data:Dictionary,now:int)->bool:
    if kind in ["you","quit","region_changed","siege_close"]:reset();return true
    if kind!="siege_window":return false
    var next:Dictionary={}
    for spec in [["oid",1,65535],["ammo_type",0,255],["time",0,255],["action",0,4],["ammo_slot",0,255],["effect",0,65535]]:
        var value:=integer(data.get(spec[0]),spec[1],spec[2])
        if value<0:return false
        next[spec[0]]=value
    if not data.get("can_move") is bool or not data.get("name") is String or String(data.name).is_empty() or String(data.name).length()>255:return false
    next.can_move=data.can_move;next.name=data.name
    var incoming:Variant=data.get("ammo")
    if not incoming is Array or incoming.size()>255:return false
    var ammo:Array=[];var indices:Dictionary={}
    for raw in incoming:
        if not raw is Dictionary:return false
        var entry:Dictionary={}
        for spec in [["index",0,255],["level",0,255],["object_type",0,255],["count",0,255],["model",0,65535]]:
            var value:=integer(raw.get(spec[0]),spec[1],spec[2])
            if value<0:return false
            entry[spec[0]]=value
        if indices.has(entry.index) or not raw.get("name") is String or String(raw.name).length()>255:return false
        entry.name=raw.name;indices[entry.index]=true;ammo.append(entry)
    next.ammo=ammo;current=next;visible=true;received_at=now;feedback="";revision+=1;return true

func request(value:Dictionary,client:Node,playing:bool,now:int)->bool:
    var action:=String(value.get("action",""))
    if not playing or current.is_empty() or client==null or not client.has_method("SiegeCommand"):return false
    if integer(value.get("oid"),1,65535)!=int(current.oid) or integer(value.get("revision"),0,2147483647)!=revision:return false
    if action=="siege_hide":visible=false;revision+=1;return true
    if action!="siege_command":return false
    var command:=integer(value.get("command"),1,10);var ammo:=integer(value.get("ammo",0),0,255)
    if command<0 or ammo<0 or now-last_command<180:return false
    if command==5 and not current.can_move:return false
    if command==1:
        var found:=false
        for entry in current.ammo:
            if int(entry.index)==ammo and int(entry.count)>0:found=true;break
        if not found:return false
    elif ammo!=0:return false
    # The server retains range, posture, ownership, target, ammunition and
    # action-timer validation. Do not infer local readiness or release control.
    client.call("SiegeCommand",command,ammo);last_command=now;return true

func snapshot(now:int)->Dictionary:
    return {"revision":revision,"visible":visible,"controlled":not current.is_empty(),"weapon":current.duplicate(true),"time_left":maxf(0.0,float(current.get("time",0))/10.0-float(maxi(0,now-received_at))/1000.0),"feedback":feedback}
