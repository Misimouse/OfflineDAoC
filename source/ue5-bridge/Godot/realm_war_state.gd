extends RefCounted
## Original decoded realm-war information only. Never authorizes teleportation.
const PAGES:=[1,2,3]
var pages:Dictionary={}
var fights:Array=[]
var fights_ready:=false
var selected_page:=3
var pending_page:=-1
var pending_until:=0
var last_request:=-1000
var visible:=false
var revision:=0
var feedback:=""

func reset()->void:
    pages.clear();fights.clear();fights_ready=false;pending_page=-1;pending_until=0;last_request=-1000;visible=false;selected_page=3;feedback="";revision+=1

func integer(value:Variant,minimum:int,maximum:int)->int:
    if not (value is int or value is float) or not is_finite(float(value)) or float(value)!=floor(float(value)) or float(value)<minimum or float(value)>maximum:return -1
    return int(value)

func request(value:Dictionary,client:Node,playing:bool,now:int)->bool:
    if String(value.get("action",""))=="warmap_close":
        visible=false;revision+=1;return true
    if String(value.get("action",""))!="warmap_request":return false
    var page:=integer(value.get("page"),1,3)
    if not playing or page not in PAGES or client==null or not client.has_method("ShowWarmap"):return false
    maintain(now)
    if pending_page!=-1 or now-last_request<1000:return false
    selected_page=page;visible=true;pending_page=page;pending_until=now+10000;last_request=now;feedback="Waiting for the server map update.";revision+=1
    # Actual original window/KeepManager pages are 1..3, despite an old 0..2
    # comment above ShowWarmap. Code 2 (teleport) is intentionally unreachable.
    client.call("ShowWarmap",0,page,0);client.call("ShowWarmap",1,page,0);return true

func maintain(now:int)->void:
    if pending_page!=-1 and now>=pending_until:
        pending_page=-1;pending_until=0;feedback="No map update received. Use Update to try again.";revision+=1

func consume(kind:String,data:Dictionary)->bool:
    if kind in ["you","quit","region_changed"]:
        reset();return true
    if kind=="warmap_keeps":
        if pending_page not in PAGES:return false
        var incoming:Variant=data.get("keeps");var relics:Variant=data.get("relics")
        if not incoming is Array or incoming.size()>510 or not relics is Array or relics.size()!=6:return false
        var holders:Array=[]
        for holder in relics:
            var realm:=integer(holder,0,3)
            if realm<0:return false
            holders.append(realm)
        var next:Dictionary={}
        for raw in incoming:
            if not raw is Dictionary:return false
            var page:=integer(raw.get("map"),1,3);var index:=integer(raw.get("index"),0,7);var tower:=integer(raw.get("tower"),0,7);var realm:=integer(raw.get("realm"),0,3)
            if page!=pending_page or index<0 or tower<0 or realm<0:return false
            for flag in ["claimed","siege","teleport"]:
                if not raw.get(flag) is bool:return false
            if not raw.get("guild") is String or String(raw.guild).length()>255:return false
            var id:=(page+1)*25+index+tower*256
            if next.has(str(id)):return false
            next[str(id)]={"id":id,"map":page,"index":index,"tower":tower,"realm":realm,"claimed":raw.claimed,"siege":raw.siege,"teleport":raw.teleport,"guild":raw.guild}
        pages[str(pending_page)]={"ready":true,"keeps":next,"relics":holders}
        pending_page=-1;pending_until=0;feedback="";revision+=1;return true
    if kind=="warmap_fights":
        if pages.is_empty():return false
        var incoming:Variant=data.get("fights")
        if not incoming is Array or incoming.size()>510:return false
        var next:Array=[]
        for raw in incoming:
            if not raw is Dictionary or not raw.get("group") is bool:return false
            var zone:=integer(raw.get("zone"),0,255);var x:=integer(raw.get("x"),0,3);var y:=integer(raw.get("y"),0,3);var color:=integer(raw.get("color"),0,7);var size:=integer(raw.get("size"),0,63)
            if zone<0 or x<0 or y<0 or color<0 or size<0:return false
            if (raw.group and color not in [1,2,4]) or (not raw.group and (color>3 or size>3)):return false
            next.append({"zone":zone,"x":x,"y":y,"color":color,"size":size,"group":raw.group})
        fights=next;fights_ready=true;revision+=1;return true
    return false

func snapshot()->Dictionary:
    return {"revision":revision,"visible":visible,"page":selected_page,"pending":pending_page!=-1,"pages":pages.duplicate(true),"fights":fights.duplicate(true),"fights_ready":fights_ready,"feedback":feedback}
