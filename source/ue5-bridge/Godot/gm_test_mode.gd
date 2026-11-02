extends RefCounted
const PREFIX:="[DAOC_BRIDGE_GM] "
var ready:=false
var combat_test:=false
var pending:=""
var until_ms:=0
var uncertain:=false
var revision:=0
var feedback:=""
func reset()->void:
    ready=false;combat_test=false;pending="";uncertain=false;until_ms=0;feedback="";revision+=1
func request(mode:String,client:Node,now:int)->bool:
    if mode not in ["protected","combat"]:return false
    if not pending.is_empty() and not (mode=="protected" and pending=="combat"):return false
    if mode=="combat" and (not ready or uncertain):return false
    client.call("Command","&bridgegm "+mode)
    pending=mode;until_ms=now+5000;feedback="Waiting for server confirmation...";revision+=1;return true
func consume(kind:String,data:Dictionary)->void:
    if kind in ["you","region_changed","quit"]:reset();return
    if kind!="message":return
    var text:=String(data.get("text","")).strip_edges()
    if not text.begins_with(PREFIX):return
    var mode:=text.substr(PREFIX.length())
    if mode not in ["protected","combat"]:return
    if pending=="protected" and mode=="combat":
        ready=true;combat_test=true;uncertain=false;revision+=1
        return
    var refused:bool=pending=="combat" and mode=="protected"
    ready=true;combat_test=mode=="combat";pending="";uncertain=false;until_ms=0
    feedback="The server keeps protection enabled: wait until alive, without flight or temporary immunity." if refused else ""
    revision+=1
func advance(now:int)->void:
    if not pending.is_empty() and now>=until_ms:
        pending="";uncertain=true;feedback="GM mode unconfirmed. F1 requests protection from the server.";revision+=1
func snapshot()->Dictionary:
    return {"ready":ready,"combat_test":combat_test,"pending":not pending.is_empty(),"requested_mode":pending,"uncertain":uncertain,"feedback":feedback,"revision":revision}
