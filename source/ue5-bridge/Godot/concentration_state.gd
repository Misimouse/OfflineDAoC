extends RefCounted
## Original ConcentrationList and status pool; cancellation refers to the current server list position.
var entries:Array=[]
var pool_known:=false
var maximum:=0
var remaining:=0
var visible:=false
var generation:=0
var signature:=""
var pending:Dictionary={}
var stale:=false
var feedback:=""
var requests:=0
var rejected:=0
func reset()->void:
    generation+=1;signature="";entries.clear();pending.clear();pool_known=false;maximum=0;remaining=0;visible=false;stale=false;feedback=""
func observe(kind:String)->void:
    if kind in ["you","region_changed","quit"]:reset()
func sync(server:Node,vitals:Dictionary,ready:bool,now:int)->void:
    var rows:Array=[]
    for item in server.conc_list:
        var index:=int(item.get("index",-1))
        if index<0 or index>255:continue
        rows.append({"index":index,"name":String(item.get("name","")),"owner":String(item.get("owner","")),"conc":int(item.get("conc",0)),"icon":int(item.get("icon",-1)),"border":int(item.get("border",-1))})
    # A repeated packet may represent another cast reusing the same list slot and truncated names.
    var stamp:=JSON.stringify([int(server.raw_seen.get(0x75,0)),rows])
    if stamp!=signature:
        signature=stamp;generation+=1;stale=false
        if not pending.is_empty():pending.clear();feedback="Concentration updated by the server."
    entries=rows
    for row in entries:row["token"]=JSON.stringify([generation,row]).sha256_text()
    pool_known=ready and vitals.has("max_conc") and vitals.has("conc")
    maximum=maxi(0,int(vitals.get("max_conc",0))) if pool_known else 0
    remaining=maxi(0,int(vitals.get("conc",0))) if pool_known else 0
    visible=(ready and int(vitals.get("max_mana",0))>0 and maximum>0) or not entries.is_empty()
    if not pending.is_empty() and now-int(pending.at)>=4000:
        pending.clear();stale=true;feedback="The list is out of date. Wait before cancelling."
func fail(text:String)->bool:rejected+=1;feedback=text;return false
func request(value:Dictionary,client:Node,now:int)->bool:
    if stale or not pending.is_empty():return fail("Wait for the concentration list to update.")
    if not client.has_method("RemoveConcentration"):return fail("Cancellation is not available.")
    var index=value.get("concentration_index",-1)
    if not (index is int or index is float) or not is_finite(float(index)) or float(index)!=floor(float(index)) or index<0 or index>255:return fail("Invalid concentration effect.")
    var found:Dictionary={}
    for row in entries:
        if row.index==int(index) and row.token==String(value.get("concentration_token","")):found=row;break
    if found.is_empty():return fail("The effect has changed. Select it again.")
    client.call("RemoveConcentration",int(index));pending={"index":int(index),"token":found.token,"at":now};requests+=1;feedback="Cancellation requested.";return true
func snapshot()->Dictionary:return {"visible":visible,"pool_known":pool_known,"maximum":maximum,"remaining":remaining,"entries":entries.duplicate(true),"pending":not pending.is_empty(),"stale":stale,"feedback":feedback}
