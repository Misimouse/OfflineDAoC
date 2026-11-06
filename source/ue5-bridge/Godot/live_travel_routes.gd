extends RefCounted
## Public original stable/item definitions, never substitute world paths or prices.
var routes:Array=[]
var ready:=false
const UNAVAILABLE:="This destination is not available in the loaded world yet."
func configure(value:Variant)->bool:
    ready=false;routes.clear()
    if not value is Dictionary or value.get("version",0)!=1 or value.get("zone",0)!=207 or value.get("region",0)!=200:return false
    var rows:Variant=value.get("routes",null)
    if not rows is Array or rows.is_empty() or rows.size()>128:return false
    for row in rows:
        if not row is Dictionary or not row.get("available",null) is bool:return false
        var p:Variant=row.get("stable_position_m",null)
        if not p is Array or p.size()!=3:return false
        for n in p:
            if not (n is float or n is int) or not is_finite(float(n)):return false
        for key in ["stable","name","ticket"]:
            if not row.get(key,null) is String or String(row[key]).is_empty():return false
        for key in ["page","index","model","price","object_type","stable_model"]:
            var n:Variant=row.get(key,null)
            if not (n is float or n is int) or not is_finite(float(n)) or float(n)!=floor(float(n)) or float(n)<0:return false
        if row.page>9 or row.index>29 or (row.available and not row.get("fully_inside_zone207",false)):return false
    routes=rows.duplicate(true);ready=true;return true
func decision(stable:Dictionary,page:int,item:Dictionary)->Dictionary:
    var name:=String(stable.get("name",""))
    var candidates:Array=[]
    for row in routes:
        if row.stable==name:candidates.append(row)
    var ticket:=int(item.get("model",0))==499 and int(item.get("object_type",-1))==0
    if candidates.is_empty():return {"managed":ticket,"available":not ticket,"reason":UNAVAILABLE if ticket else ""}
    if not ready:return {"managed":true,"available":false,"reason":UNAVAILABLE}
    var p:Variant=stable.get("position_m",[])
    if not p is Array or p.size()!=3:return {"managed":true,"available":false,"reason":UNAVAILABLE}
    for n in p:
        if not (n is int or n is float) or not is_finite(float(n)):return {"managed":true,"available":false,"reason":UNAVAILABLE}
    for row in candidates:
        var q:Array=row.stable_position_m
        if Vector3(p[0],p[1],p[2]).distance_to(Vector3(q[0],q[1],q[2]))>2 or int(stable.get("model_id",0))!=row.stable_model:continue
        if page!=row.page or int(item.get("index",-1))!=row.index:continue
        for key in ["name","model","price","object_type"]:
            if item.get(key,null)!=row[key]:return {"managed":true,"available":false,"reason":"The route catalogue has changed. Reopen the stable window."}
        return {"managed":true,"available":row.available,"reason":"" if row.available else UNAVAILABLE}
    return {"managed":true,"available":false,"reason":UNAVAILABLE}
func annotate(interaction:Dictionary,entities:Dictionary)->Dictionary:
    var out:=interaction.duplicate(true);var shop:Dictionary=out.get("merchant",{})
    var stable:Dictionary=entities.get(shop.get("entity_id",""),{})
    for page in shop.get("pages",{}):
        for item in shop.pages[page]:
            var result:=decision(stable,int(page),item)
            if result.managed:item["travel_available"]=result.available;item["travel_reason"]=result.reason
    return out
