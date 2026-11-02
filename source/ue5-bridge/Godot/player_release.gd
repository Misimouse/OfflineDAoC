extends RefCounted
## Request the original server release; never heal, relocate or simulate revival.
var pending:=false
var until_ms:=0
var revision:=0
var feedback:=""
var requests:=0
var rejected:=0
func reset()->void:
    pending=false;until_ms=0;feedback="";revision+=1
func request(value:Dictionary,state:RefCounted,client:Node,now:int)->bool:
    var epoch=value.get("player_generation",-1)
    if not (epoch is int or epoch is float) or not is_finite(float(epoch)) or float(epoch)!=float(state.generation):return fail("Character state has changed.")
    if not state.ready or int(state.vitals.get("health_pct",100))!=0:return fail("You can only release after dying.")
    if pending:return false
    client.call("Command","&release")
    pending=true;until_ms=now+8000;requests+=1;feedback="Release requested. Waiting for server...";revision+=1;return true
func fail(text:String)->bool:
    feedback=text;rejected+=1;revision+=1;return false
func consume(kind:String,data:Dictionary,me:int)->void:
    if kind in ["you","region_changed","quit"]:reset();return
    if pending and kind=="status":
        var hp=data.get("health_pct",-1)
        if (hp is int or hp is float) and is_finite(float(hp)) and float(hp)>0 and float(hp)<=100 and float(hp)==floor(float(hp)):reset()
func advance(now:int)->void:
    if pending and now>=until_ms:
        pending=false;until_ms=0;feedback="The server has not confirmed release yet. You may request it again.";revision+=1
func snapshot()->Dictionary:return {"pending":pending,"feedback":feedback,"requests":requests}
