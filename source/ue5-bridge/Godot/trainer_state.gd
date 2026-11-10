extends RefCounted
## Training uses original packets; previews never enter the usable-skill catalog.
var specs:Array=[]
var realm:Array=[]
var previews:Dictionary={}
var ready:=false
var realm_ready:=false
var preview_ready:=false
var generation:=0
var open_serial:=0
var spec_points:=-1
var realm_points:=-1
var character_level:=0
var feedback:=""
var pending:Dictionary={}
var refresh_at:=0
var requests:=0
var rejected:=0
func reset()->void:
    generation+=1;ready=false;realm_ready=false;preview_ready=false;specs.clear();realm.clear();previews.clear();pending.clear();refresh_at=0;spec_points=-1;realm_points=-1;feedback="";character_level=0
func observe(kind:String,d:Dictionary,server:Node)->void:
    if kind in ["you","region_changed","quit"]:reset();return
    if kind=="trainer":
        generation+=1;open_serial+=1;specs=d.get("specs",[]).duplicate(true);realm.clear();realm_ready=false;previews.clear();preview_ready=false;ready=true;spec_points=int(d.get("points",-1))
        if pending.get("action","")=="trainer_refresh":pending.clear();feedback=""
    elif kind=="trainer_ra":generation+=1;realm=d.get("list",[]).duplicate(true);realm_points=int(d.get("points",-1));realm_ready=true
    elif kind=="trainer_skills":preview_ready=true
func sync(server:Node,client:Node,now:int)->void:
    character_level=int(server.info.get("level",0))
    if ready and server.points.has("spec_points"):spec_points=int(server.points.spec_points)
    if preview_ready:
        previews.clear()
        for index in server.trainer_skills:
            var list:Array=[]
            for skill in server.trainer_skills[index]:
                var page:=int(skill.get("page",0));var kind:="style" if page==2 else "spell" if page in [3,4] else "icon";var icon:Array=server.skill_icon(kind,int(skill.get("icon",-1)))
                list.append({"level":int(skill.get("level",0)),"name":String(skill.get("name","")),"kind":{2:"style",3:"spell",4:"song",5:"ability"}.get(page,"skill"),"icon":int(icon[0]),"border":int(icon[1])})
            previews[str(int(index))]=list
    for row in specs:
        row["kind"]="spec";row["cost"]=int(row.get("next",int(row.level)+1));row["can_train"]=int(row.level)<mini(character_level,50) and int(row.cost)>0 and int(row.cost)<=spec_points;row["token"]=identity(row)
    for row in realm:
        row["kind"]="realm";row["can_train"]=bool(row.get("available",false)) and int(row.get("cost",0))<=realm_points;row["token"]=identity(row)
    if not pending.is_empty():
        if pending.action=="trainer_train":
            var current:Dictionary=find(String(pending.kind),int(pending.index))
            if not current.is_empty() and int(current.level)>=int(pending.level):feedback="Training confirmed by the server.";pending.clear();refresh_at=0
        if not pending.is_empty() and refresh_at>0 and now>=refresh_at:client.call("TrainWindow");refresh_at=0
        if not pending.is_empty() and now-int(pending.at)>=5000:feedback="The server has not confirmed training. Check chat.";pending.clear();refresh_at=0
func identity(row:Dictionary)->String:return JSON.stringify([generation,String(row.kind),int(row.index),String(row.name),int(row.level),int(row.get("cost",0)),bool(row.get("can_train",false)),spec_points,realm_points,character_level]).sha256_text()
func find(kind:String,index:int)->Dictionary:
    for row in specs if kind=="spec" else realm if kind=="realm" else []:
        if int(row.index)==index:return row
    return {}
func fail(text:String)->bool:rejected+=1;feedback=text;return false
func request(value:Dictionary,client:Node,now:int,alive:bool)->bool:
    if not alive:return fail("You cannot train while dead.")
    if not pending.is_empty():return fail("Wait for the server response.")
    var action:=String(value.get("action",""))
    if action=="trainer_refresh":client.call("TrainWindow");pending={"action":action,"at":now};requests+=1;feedback="Requesting trainer information...";return true
    if action!="trainer_train" or not ready:return fail("The server has not opened the trainer yet.")
    var index=value.get("training_index",-1)
    if not (index is int or index is float) or not is_finite(float(index)) or float(index)!=floor(float(index)) or index<0 or index>255:return fail("Invalid training entry.")
    var kind:=String(value.get("training_kind",""));var row:Dictionary=find(kind,int(index))
    if row.is_empty() or row.token!=String(value.get("training_token","")):return fail("The list has changed. Select the entry again.")
    if not bool(row.can_train):return fail("The server's requirements are not met.")
    if kind=="realm" and int(index)>=50:return fail("The entry does not fit the original protocol.")
    var level:=int(row.level)+1
    client.call("TrainSpec" if kind=="spec" else "TrainRealmAbility",int(index),level)
    pending={"action":action,"kind":kind,"index":int(index),"level":level,"at":now};refresh_at=now+600;requests+=1;feedback="Training requested; waiting for server.";return true
func snapshot()->Dictionary:return {"ready":ready,"realm_ready":realm_ready,"preview_ready":preview_ready,"open_serial":open_serial,"specs":specs.duplicate(true),"realm":realm.duplicate(true),"previews":previews.duplicate(true),"spec_points":spec_points,"realm_points":realm_points,"character_level":character_level,"pending":not pending.is_empty(),"feedback":feedback}
