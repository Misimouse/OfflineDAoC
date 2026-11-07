extends RefCounted
## Opens only for the original server packet; the server owns permissions and payment.
const ACTIONS=["emblem_select","emblem_submit","emblem_close"]
var character:=""
var guild:=""
var visible:=false
var revision:=0
var generation:=0
var token:=""
var draft:Dictionary={"primary":0,"secondary":0,"pattern":0,"logo":1}
var feedback:=""
var submitted:=0
var rejected:=0

func reset()->void:
    visible=false;generation+=1;revision+=1;token="";feedback=""
    draft={"primary":0,"secondary":0,"pattern":0,"logo":1}

func sync(server:Node,name:String)->void:
    var next_guild:=String(server.info.get("guild","")).strip_edges()
    if next_guild.to_lower()=="none" or not server.playing:next_guild=""
    if name!=character or next_guild!=guild or not server.playing:
        reset();character=name;guild=next_guild

static func integer(value:Variant,minimum:int,maximum:int)->int:
    if typeof(value) not in [TYPE_INT,TYPE_FLOAT]:return -1
    var n:=float(value)
    if not is_finite(n) or n!=floorf(n) or n<minimum or n>maximum:return -1
    return int(n)

static func encode(value:Dictionary)->int:
    return (int(value.logo)<<9)|(int(value.pattern)<<7)|(int(value.primary)<<3)|int(value.secondary)

func consume(kind:String,_data:Dictionary,server:Node,items:Array)->bool:
    if kind in ["you","quit"]:reset();return false
    if kind!="emblem_dialog":return false
    if not server.playing or guild.is_empty() or character.is_empty():return true
    reset();visible=true;token=JSON.stringify([generation,character,guild]).sha256_text()
    var worn:=0
    for slot in [26,11]:
        for item in items:
            if int(item.get("slot",-1))==slot and integer(item.get("emblem",0),1,131071)>0:
                worn=int(item.emblem);break
        if worn>0:break
    if worn>0:
        draft={"logo":maxi(1,worn>>9),"pattern":(worn>>7)&3,"primary":(worn>>3)&15,"secondary":worn&7}
    revision+=1;return true

func fail(text:String)->bool:
    feedback=text;rejected+=1;revision+=1;return false

func request(value:Dictionary,server:Node)->bool:
    var action:=String(value.get("action",""))
    if action not in ACTIONS:return false
    if not server.playing or not visible or guild.is_empty() or String(value.get("token",""))!=token:
        return fail("This emblem window is no longer available.")
    if action=="emblem_close":visible=false;revision+=1;return true
    if action=="emblem_select":
        var next:Dictionary={}
        for key in ["primary","secondary","pattern","logo"]:
            var n:=integer(value.get(key,draft[key]),1 if key=="logo" else 0,255 if key=="logo" else 15 if key=="primary" else 7 if key=="secondary" else 3)
            if n<0:return fail("Invalid emblem choice.")
            next[key]=n
        draft=next;feedback="";revision+=1;return true
    if server.client==null:return fail("The server connection is unavailable.")
    server.client.call("EmblemChoice",int(draft.primary),int(draft.secondary),int(draft.pattern),int(draft.logo))
    submitted+=1;visible=false;revision+=1;feedback="Request sent to server."
    return true

func snapshot()->Dictionary:
    return {"visible":visible,"revision":revision,"token":token,"guild":guild,"draft":draft.duplicate(true),"emblem":encode(draft),"feedback":feedback}
