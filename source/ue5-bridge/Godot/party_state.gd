extends RefCounted
## Authoritative roster and original group commands. Never creates or empties a group optimistically.
var members:Array=[]
var metrics:Dictionary={}
var deferred_updates:Dictionary={}
var observed_roster:Array=[]
var generation:=0
var roster_token:=""
var roster_signature:=""
var pending:Dictionary={}
var feedback:=""
var requests:=0
var rejected:=0
func reset()->void:generation+=1;members.clear();metrics.clear();deferred_updates.clear();observed_roster.clear();roster_signature="";roster_token="";pending.clear();feedback=""
func identity(m:Dictionary)->String:return JSON.stringify([int(m.get("oid",0)),String(m.get("name","")),String(m.get("class_name","")),int(m.get("level",0))]).sha256_text()
func store_update(u:Dictionary,server:Node)->void:
    var i:=int(u.get("index",-1))
    if i<0 or i>=server.group_members.size():return
    var oid:=int(server.group_members[i].get("oid",0))
    if not metrics.has(oid) or metrics[oid].get("_identity","")!=identity(server.group_members[i]):metrics[oid]={"_identity":identity(server.group_members[i])}
    if u.has("icons"):
        var icons:Array=[]
        for icon in u.icons:
            var ic:Array=server.skill_icon("spell",int(icon));icons.append({"icon":int(ic[0]),"border":int(ic[1])})
        metrics[oid]["effects"]=icons
    else:
        for key in ["hp","power","end"]:
            if u.has(key) and int(u[key])>=0 and int(u[key])<=100:metrics[oid][key]=int(u[key])
func observe(kind:String,d:Dictionary,server:Node,now:int=-1)->void:
    if kind in ["you","region_changed","quit"]:reset();return
    if now<0:now=Time.get_ticks_msec()
    if kind=="group":
        # The original core sends a joining member's status BEFORE the expanded roster.
        # Adopt only newly appended places, within one second and with an unchanged prefix.
        var next:Array=server.group_members.slice(0,8)
        var extends_roster:bool=next.size()>observed_roster.size()
        for i in observed_roster.size():
            if i>=next.size() or identity(next[i])!=identity(observed_roster[i]):extends_roster=false;break
        if extends_roster:
            for i in deferred_updates:
                var staged:Dictionary=deferred_updates[i]
                if int(i)<observed_roster.size() or int(i)>=next.size() or now-int(staged.at)>1000:continue
                if staged.has("vitals"):store_update(staged.vitals,server)
                if staged.has("effects"):store_update(staged.effects,server)
        deferred_updates.clear();observed_roster=next.duplicate(true);return
    if kind!="group_update":return
    for u in d.get("list",[]):
        var i:=int(u.get("index",-1))
        if i<0 or i>=8:continue
        if i>=server.group_members.size():
            var staged:Dictionary=deferred_updates.get(i,{})
            if now-int(staged.get("at",now))>1000:staged={}
            staged["at"]=now;staged["effects" if u.has("icons") else "vitals"]=u.duplicate(true);deferred_updates[i]=staged
        else:store_update(u,server)
func sync(server:Node,ids:Dictionary,local_vitals:Dictionary,local_effects:Array,now:int)->void:
    var roster:Array=[]
    for m in server.group_members.slice(0,8):roster.append({"oid":int(m.get("oid",0)),"name":String(m.get("name","")),"class_name":String(m.get("class_name","")),"level":int(m.get("level",0))})
    observed_roster=roster.duplicate(true)
    var signature:=JSON.stringify(roster)
    if signature!=roster_signature:
        roster_signature=signature;generation+=1;roster_token=(signature+str(generation)).sha256_text()
        var valid:Array=roster.map(func(m):return m.oid)
        for oid in metrics.keys():
            if not valid.has(oid):metrics.erase(oid)
        if not pending.is_empty():pending.clear();feedback="Group updated by the server."
    members=[]
    for m in roster:
        var row:Dictionary=m.duplicate();var oid:=int(row.oid);row["me"]=oid==int(server.me_oid);row["entity_id"]="player:local" if row.me else String(ids.get(oid,"group:%d" % oid));row["hp"]=-1;row["power"]=-1;row["end"]=-1;row["effects"]=[]
        var current:Dictionary=metrics.get(oid,{})
        if current.get("_identity","")==identity(m):row.merge(current,true)
        row.erase("_identity")
        if row.me:
            for pair in [["hp","health_pct"],["power","mana_pct"],["end","endurance_pct"]]:
                if local_vitals.has(pair[1]):row[pair[0]]=int(local_vitals[pair[1]])
            row.effects=local_effects.duplicate(true)
        row["token"]=identity(m);members.append(row)
    if not pending.is_empty() and now-int(pending.at_ms)>4000:pending.clear();feedback="The server has not updated the group. Check chat."
func oid_value(v:Variant)->int:
    if not (v is int or v is float) or not is_finite(float(v)) or float(v)!=floor(float(v)) or v<=0 or v>65535:return -1
    return int(v)
func member(oid:int,token:String)->Dictionary:
    for m in members:
        if int(m.oid)==oid and String(m.token)==token:return m
    return {}
func fail(text:String)->bool:feedback=text;rejected+=1;return false
func request(v:Dictionary,server:Node,client:Node,interaction:RefCounted,entities:Dictionary,now:int)->bool:
    var action:=String(v.get("action",""))
    if action=="group_target":
        var m:=member(oid_value(v.get("member_oid",0)),String(v.get("member_token","")))
        if m.is_empty() or int(m.oid)<=0:return fail("That member is no longer available.")
        interaction.select_group_member(m,client,int(server.me_oid));feedback="";return true
    if not pending.is_empty():return fail("Wait for the server response.")
    if action=="group_invite":
        var id:=String(v.get("entity_id",""));var row:Dictionary=entities.get(id,{})
        if id!=interaction.selected_id or row.is_empty() or id=="player:local" or not bool(row.get("targetable",true)) or float(row.get("health",1))<=0:return fail("Select someone to invite.")
        var oid:=int(id.get_slice(":",1))
        if oid<=0:return fail("That target is not available.")
        client.call("Target",oid,0x6000);server.command("/invite")
    elif action in ["group_remove","group_leave"]:
        if members.is_empty() or String(v.get("group_token",""))!=roster_token:return fail("Group membership has changed.")
        if action=="group_remove":
            var m:=member(oid_value(v.get("member_oid",0)),String(v.get("member_token","")))
            if m.is_empty() or bool(m.me):return fail("Select the group member to remove.")
            var name:=String(m.name).strip_edges()
            if name.is_empty() or name.contains("\n") or name.contains("\r"):return fail("Invalid group member name.")
            server.command("/disband "+name)
        else:server.command("/disband")
    else:return false
    requests+=1;pending={"action":action,"at_ms":now};feedback="Request sent to server.";return true
func snapshot()->Dictionary:return {"members":members.duplicate(true),"token":roster_token,"pending":not pending.is_empty(),"feedback":feedback}
