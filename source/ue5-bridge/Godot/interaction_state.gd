extends RefCounted
## Server-derived interaction state; injectable client keeps protocol tests offline.
var selected_id:=""
var selected_group_oid:=0
var group_targets:Dictionary={}
var local_target:Dictionary={}
var conversation_id:=""
var talk:Dictionary={}
var merchant:Dictionary={}
var dialogs:Array=[]
var messages:Array=[]
var revision:=0
var serial:=0
var feedback:=""
var requests:=0
var responses:=0
var rejected:=0

func reset()->void:
    selected_id="";selected_group_oid=0;group_targets.clear();local_target.clear();conversation_id="";talk.clear();merchant.clear();dialogs.clear();messages.clear();feedback="";revision+=1

func _row(entities:Dictionary,id:String)->Dictionary:
    return entities.get(id,{})

func _distance(row:Dictionary,pos:Vector3)->float:
    var p:Array=row.get("position_m",[])
    if p.size()!=3:return INF
    var at:=Vector3(float(p[0]),float(p[1]),float(p[2]))
    var motion:Dictionary=row.get("motion",{})
    var speed:=maxf(0.0,float(motion.get("speed_mps",0.0)))
    if speed>0 and float(row.get("health",1))>0:
        var goal:Array=motion.get("destination_m",[])
        var interval:=float(motion.get("interval_ms",500))*.001
        var horizon:=clampf(interval*2+1,6,10) if goal.size()==3 else clampf(interval*1.5+.1,.25,1)
        var elapsed:=clampf(float(Time.get_ticks_msec()-int(motion.get("at_ms",Time.get_ticks_msec())))*.001,0,horizon)
        var forward:Array=row.get("forward_xz",[0,1])
        var delta:=Vector3(float(goal[0])-at.x,0,float(goal[2])-at.z) if goal.size()==3 else Vector3(float(forward[0]),0,float(forward[1]))
        var length:=delta.length()
        if length>.00001:at+=delta/length*(minf(length,speed*elapsed) if goal.size()==3 else speed*elapsed)
    return pos.distance_to(at)

func _valid(row:Dictionary)->bool:
    return not row.is_empty() and row.get("id","")!="player:local" and bool(row.get("targetable",true)) and float(row.get("health",1))>0

func _fail(text:String)->bool:
    feedback=text;rejected+=1;revision+=1;return false

func _close_conversation()->void:
    talk={};merchant={};conversation_id=""

func maintain(client:Node,entities:Dictionary,pos:Vector3)->void:
    if selected_group_oid>0 and group_targets.has(selected_group_oid):selected_id=String(group_targets[selected_group_oid].entity_id)
    elif selected_group_oid>0:selected_group_oid=0
    if selected_id!="player:local" and selected_group_oid==0 and not selected_id.is_empty() and not _valid(_row(entities,selected_id)):
        selected_id="";_close_conversation();client.call("Target",0,0);revision+=1
    if not conversation_id.is_empty() and _distance(_row(entities,conversation_id),pos)>12:
        _close_conversation();revision+=1

func execute(value:Dictionary,client:Node,entities:Dictionary,pos:Vector3)->bool:
    var action:=String(value.get("action",""))
    if action=="target" or action=="interact":
        selected_group_oid=0
        var id:=String(value.get("entity_id",""))
        if id.is_empty() and action=="target":
            selected_id="";_close_conversation();client.call("Target",0,0);revision+=1;return true
        var row:=_row(entities,id)
        if not _valid(row):return _fail("That target is no longer available.")
        if action=="interact" and (row.get("kind","")!="npc" or _distance(row,pos)>6):return _fail("Move closer to interact.")
        if selected_id!=id:_close_conversation()
        selected_id=id;feedback="";revision+=1
        client.call("Target",int(id.get_slice(":",1)),0xE000)
        if action=="interact":
            _close_conversation();conversation_id=id;requests+=1
            client.call("Interact",int(id.get_slice(":",1)),int(pos.x*40+35*8192),int(pos.z*40+51*8192))
        return true
    if action=="keyword":
        var row:=_row(entities,conversation_id)
        var word:=String(value.get("word",""))
        if talk.is_empty() or int(value.get("reply_id",-1))!=int(talk.get("id",-2)) or selected_id!=conversation_id or not _valid(row) or _distance(row,pos)>6 or not word in talk.get("keywords",[]):return _fail("That response is no longer available.")
        client.call("Target",int(selected_id.get_slice(":",1)),0xE000)
        client.call("Command","&whisper "+word);requests+=1;return true
    if action=="dialog_response":
        var id:=int(value.get("dialog_id",-1));var answer=value.get("answer")
        if not (answer is int or answer is float) or (answer!=0 and answer!=1):return _fail("Invalid response.")
        for i in range(dialogs.size()):
            if int(dialogs[i].id)==id:
                var d:Dictionary=dialogs.pop_at(i)
                client.call("DialogResponse",int(d.data1),int(d.data2),int(d.data3),int(d.code),int(answer))
                revision+=1;requests+=1;return true
        return _fail("That confirmation is no longer available.")
    if action=="dismiss_interaction":
        _close_conversation();revision+=1;return true
    return false

func consume(kind:String,data:Dictionary,entities:Dictionary,now:int)->void:
    if kind in ["region_changed","quit"]:reset();return
    var row:=_row(entities,conversation_id)
    if kind=="message":
        var text:=String(data.get("text","")).left(12000)
        messages.append(text.left(1000));if messages.size()>8:messages.pop_front()
        if bool(data.get("popup",false)) and not row.is_empty() and selected_id==conversation_id:
            var stack:bool=not talk.is_empty() and int(talk.get("at",-1000))==now
            var body:String=(String(talk.get("text",""))+"\n\n"+text) if stack else text
            serial+=1
            var words:Array=[]
            var regex:=RegEx.create_from_string("\\[([^\\]\\r\\n]{1,100})\\]")
            for match in regex.search_all(body):
                var word:=match.get_string(1)
                if not words.has(word):words.append(word)
                if words.size()>=30:break
            talk={"id":serial,"entity_id":conversation_id,"name":row.get("name",""),"text":body.left(24000),"keywords":words,"at":now}
            responses+=1
        revision+=1
    elif kind=="merchant" and not row.is_empty() and selected_id==conversation_id:
        if merchant.is_empty():merchant={"entity_id":conversation_id,"name":row.get("name",""),"pages":{},"window":int(data.get("window",0))}
        var page:=int(data.get("page",0))
        if page<0 or page>9:return
        var items:Array=[]
        for item in data.get("items",[]):
            items.append({"index":int(item.get("index",0)),"name":String(item.get("name","")).left(160),"price":int(item.get("price",0)),"level":int(item.get("level",0)),"model":int(item.get("model",0)),"object_type":int(item.get("object_type",0)),"hand":int(item.get("hand",0)),"can_use":bool(item.get("can_use",false))})
            if items.size()>=30:break
        serial+=1;merchant["catalog_revision"]=serial
        merchant.pages[str(page)]=items;responses+=1;revision+=1
    elif kind=="dialog":
        if int(data.get("type",0))==0 and int(data.get("code",0))==0 and String(data.get("text","")).to_lower().contains("free level"):
            messages.append(String(data.get("text","")).left(1000));if messages.size()>8:messages.pop_front()
            revision+=1;return
        if dialogs.size()>=8:return
        for old in dialogs:
            if old.get("text","")==data.get("text","") and int(old.code)==int(data.get("code",0)):return
        serial+=1
        var d:Dictionary=data.duplicate(true);d.id=serial;d.text=String(data.get("text","")).left(24000);d.title=String(data.get("title","")).left(160)
        dialogs.append(d);responses+=1;revision+=1

func select_self(client:Node,me:int)->bool:
    if me<=0:return _fail("The character is not available yet.")
    selected_group_oid=0;selected_id="player:local";_close_conversation();client.call("Target",me,0x6000);revision+=1;return true
func select_group_member(m:Dictionary,client:Node,me:int)->void:
    if bool(m.get("me",false)):select_self(client,me);return
    selected_group_oid=int(m.oid);selected_id=String(m.entity_id);_close_conversation();client.call("Target",selected_group_oid,0x6000);revision+=1
func snapshot(entities:Dictionary,pos:Vector3)->Dictionary:
    var target:Dictionary={}
    if entities.has(selected_id):
        var row:Dictionary=entities[selected_id]
        target={"id":selected_id,"name":row.get("name",""),"health":row.get("health",1),"level":row.get("level",0),"guild":row.get("guild",""),"kind":row.get("kind","npc"),"distance_m":_distance(row,pos)}
    var confirmations:Array=[]
    for d in dialogs:confirmations.append({"id":d.id,"text":d.text,"title":d.title,"type":int(d.get("type",0))})
    if selected_id=="player:local" and not local_target.is_empty():target=local_target.duplicate(true);target["id"]="player:local";target["distance_m"]=0
    elif selected_group_oid>0 and group_targets.has(selected_group_oid):
        var member:Dictionary=group_targets[selected_group_oid];target={"id":selected_id,"name":member.name,"level":member.level,"kind":"player","health":float(member.hp)/100.0 if int(member.hp)>=0 else -1.0,"guild":"","distance_m":_distance(_row(entities,selected_id),pos) if entities.has(selected_id) else -1.0}
    return {"revision":revision,"target":target,"talk":talk,"merchant":merchant,"dialogs":confirmations,"messages":messages,"feedback":feedback}
