extends RefCounted
## Message kinds and default colors follow the original ServerWorld/ChatWindow.
const KINDS={0:"system",1:"say",2:"send",3:"group",4:"guild",5:"broadcast",6:"emote",7:"help",8:"chatgroup",9:"advice",10:"officer",11:"alliance",12:"group",13:"group",15:"broadcast",16:"spells",17:"combat",18:"damage_taken",19:"combat",20:"merchant",21:"system",22:"combat_others",23:"combat_others",24:"combat",25:"spells",26:"loot",27:"resists",28:"system",29:"damage_taken",30:"combat",31:"spells",32:"combat_others",33:"combat_others",34:"combat_others",35:"system",36:"merchant"}
const LIMIT:=200
const TEXT_LIMIT:=4096
var entries:Array=[]
var serial:=0
var revision:=0
var skipped_social:=0
var last_private_sender:=""
var cached:Dictionary={"revision":0,"entries":[]}
var bubbles:Array=[]
var notices:Array=[]
func screen_message(text:String,now:int,small:bool=false,duration:int=5000)->void:
    if not notices.is_empty() and notices.back().text==text and now-int(notices.back().at_ms)<1000:return
    serial+=1;notices.append({"id":serial,"text":text.left(1000),"at_ms":now,"duration_ms":duration,"small":small})
    if notices.size()>3:notices.pop_front()
func world_message(data:Dictionary,entities:Dictionary,selected:String,pos:Vector3,now:int)->bool:
    var text:=String(data.get("text",""));var raw:=int(data.get("type",0))
    if raw in [200,201,202,203]:screen_message(text,now,raw in [201,203]);return true
    if raw in [0,21,28,35] and (text.begins_with("(Region) You have entered ") or text.begins_with("(Region) You have left ") or text.begins_with("You have entered ")):
        screen_message(text.trim_prefix("(Region) "),now,false,6500);return true
    var id:="";var body:=text;var name:="";var popup:=bool(data.get("popup",false))
    if popup and entities.has(selected) and String(entities[selected].get("kind",""))=="npc":
        id=selected;name=String(entities[id].get("name",""))
    elif popup:screen_message(body,now,true);return true
    elif raw==1:
        var split:=text.find(' says, "')
        if split<1:return false
        name=text.left(split);var matches:Array=[]
        for row in entities.values():
            if row.get("kind","")!="npc" or String(row.get("name",""))!=name:continue
            var p:Array=row.get("position_m",[])
            if p.size()==3 and pos.distance_to(Vector3(p[0],p[1],p[2]))<=60:matches.append(row)
        # The original Message packet has no speaker OID. Do not guess between duplicate names.
        if matches.is_empty():return false
        body=text.substr(split+8).trim_suffix('"')
        if matches.size()>1:screen_message(name+": "+body,now,true);return true
        id=String(matches[0].id)
    if id.is_empty():
        if popup:screen_message(body,now,true);return true
        return false
    serial+=1;bubbles=bubbles.filter(func(b):return b.entity_id!=id)
    bubbles.append({"id":serial,"entity_id":id,"name":name,"text":body.left(1600),"at_ms":now,"duration_ms":clampi(4500+body.length()*25,6500,14000)})
    if bubbles.size()>8:bubbles.pop_front()
    return true
func reset()->void:
    entries.clear();bubbles.clear();notices.clear();serial=0;revision+=1;skipped_social=0;last_private_sender="";cached={"revision":revision,"entries":[]}
func append(text:String,kind:String,raw_type:int=-1,source:String="client")->void:
    if text.is_empty():return
    serial+=1;revision+=1;entries.append({"id":serial,"text":text.left(TEXT_LIMIT),"kind":kind,"type":raw_type,"source":source})
    if entries.size()>LIMIT:entries.pop_front()
    # Build a new immutable view on a message, rather than cloning history on every world frame.
    cached={"revision":revision,"entries":entries.duplicate(true)}
func observe(kind:String,data:Dictionary,entities:Dictionary={},selected:String="",pos:Vector3=Vector3.ZERO,now:int=-1)->bool:
    if kind=="quit":reset();return true
    if kind in ["you","region_changed"]:bubbles.clear();notices.clear();return false
    if kind!="message":return false
    # DOL's CT_Send incoming English template is distinct from outgoing echoes.
    # Never infer a reply recipient from player speech or client-local feedback.
    if data.get("type")==2 and not bool(data.get("popup",false)) and data.get("text") is String:
        var sender:=RegEx.create_from_string("^([A-Za-z][A-Za-z'-]{1,47})(?: \\[AFK\\])? sends, \"").search(String(data.text))
        if sender!=null:last_private_sender=sender.get_string(1)
    if now<0:now=Time.get_ticks_msec()
    if world_message(data,entities,selected,pos,now):return true
    var raw:=int(data.get("type",0))
    if raw==0x64:skipped_social+=1;return true
    var channel:="npc" if bool(data.get("popup",false)) else "system" if raw in [0xCA,0xCB] else String(KINDS.get(raw,"system"))
    append(String(data.get("text","")),channel,raw,"server")
    return false
func snapshot(now:int=-1)->Dictionary:
    if now<0:now=Time.get_ticks_msec()
    bubbles=bubbles.filter(func(b):return now-int(b.at_ms)<int(b.duration_ms))
    notices=notices.filter(func(n):return now-int(n.at_ms)<int(n.duration_ms))
    var view:Dictionary=cached.duplicate();view["bubbles"]=[];view["notices"]=[];view["reply_to"]=last_private_sender
    for key in ["bubbles","notices"]:
        for row in bubbles if key=="bubbles" else notices:
            var value:Dictionary=row.duplicate();value["age_ms"]=maxi(0,now-int(row.at_ms));view[key].append(value)
    return view
