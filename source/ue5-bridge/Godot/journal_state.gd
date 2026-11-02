extends RefCounted
## Original server journal. Indices are one-based in QuestEntry and zero-based in RemoveQuest.
var entries:Array=[]
var generation:=0
var signature:=""
var feedback:=""
var guide:Dictionary={}
var pending:Dictionary={}
var suppress_guide:=false
var requests:=0
var rejected:=0
func reset()->void:
    generation+=1;entries.clear();signature="";feedback="";guide.clear();pending.clear();suppress_guide=false
func observe(kind:String,d:Dictionary)->bool:
    if kind in ["you","region_changed","quit"]:reset()
    if kind!="detail" or not String(d.get("caption","")).to_upper().begins_with("QUEST GUIDE"):return false
    if suppress_guide:suppress_guide=false;pending.clear();feedback="";return true
    var lines:Array=[]
    for line in d.get("lines",[]):lines.append(String(line))
    guide={"caption":String(d.get("caption","Quest Guide")),"lines":lines,"status":"ready"}
    if pending.get("action","")=="journal_guide":pending.clear();feedback=""
    return true
func sync(server:Node,now:int)->void:
    var next:Array=[];var keys:Array=server.quests.keys();keys.sort()
    for key in keys:
        var index:=int(key)
        if index<1 or index>255:continue
        var q:Dictionary=server.quests[key];var name:=String(q.get("name",""))
        if name.is_empty():continue
        var goals:Array=[]
        for g in q.get("goals",[]):goals.append({"text":String(g.get("text","")),"done":bool(g.get("done",false))})
        next.append({"index":index,"name":name,"text":String(q.get("text","")),"goals":goals})
    var stamp:=JSON.stringify(next)
    if stamp!=signature:
        signature=stamp;generation+=1
        if pending.get("action","")=="journal_remove":feedback="Journal updated by the server.";pending.clear()
    entries=next
    for row in entries:row["token"]=JSON.stringify([generation,row]).sha256_text()
    if not pending.is_empty() and now-int(pending.at)>=5000:
        if pending.action=="journal_guide" and not suppress_guide:guide={"status":"unavailable","caption":"Quest Guide","lines":[]}
        feedback="The server has not confirmed the request. Check chat.";pending.clear();suppress_guide=false
func fail(text:String)->bool:rejected+=1;feedback=text;return false
func request(value:Dictionary,server:Node,client:Node,now:int)->bool:
    var action:=String(value.get("action",""))
    if action=="journal_guide_close":
        guide.clear();suppress_guide=pending.get("action","")=="journal_guide";return true
    if not pending.is_empty():return fail("Wait for the server response.")
    if action=="journal_guide":
        # Same ShowNext as /task, without granting a task to a targeted NPC.
        suppress_guide=false;server.command("/questguide");guide={"caption":"Quest Guide","status":"pending","lines":[]}
    elif action=="journal_remove":
        var index=value.get("quest_index",-1)
        if not (index is int or index is float) or not is_finite(float(index)) or float(index)!=floor(float(index)) or index<1 or index>255:return fail("Invalid quest.")
        var found:Dictionary={}
        for row in entries:
            if row.index==int(index) and row.token==String(value.get("quest_token","")):found=row;break
        if found.is_empty():return fail("The journal has changed. Select the quest again.")
        client.call("RemoveQuest",int(index)-1)
    else:return fail("Unknown journal action.")
    requests+=1;pending={"action":action,"at":now};feedback="Request sent to server.";return true
func snapshot()->Dictionary:return {"entries":entries.duplicate(true),"feedback":feedback,"pending":not pending.is_empty(),"guide":guide.duplicate(true)}
