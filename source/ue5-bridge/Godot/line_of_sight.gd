extends RefCounted
## Every server LOS question uses native geometry, including close targets; self-only requests are also correlated.
var pending:Dictionary={}
var serial:=0
var requests:=0
var near_replies:=0
var native_replies:=0
var rejected:=0
var timeouts:=0
func reset()->void:pending.clear()
func request(d:Dictionary,client:Node,positions:Dictionary,now:int)->void:
    requests+=1;var source:=int(d.get("source",0));var target:=int(d.get("target",0))
    if not positions.has(source) or not positions.has(target):client.call("LosReply",source,target,false);return
    var a:Dictionary=positions[source];var b:Dictionary=positions[target]
    if pending.size()>=32:client.call("LosReply",source,target,false);return
    serial+=1;var token:=Crypto.new().generate_random_bytes(12).hex_encode()
    pending[str(serial)]={"id":str(serial),"token":token,"source":source,"target":target,"source_id":a.id,"target_id":b.id,"at_ms":now}
func reply(v:Dictionary,client:Node,now:int)->bool:
    var id:=String(v.get("query_id",""));var q:Dictionary=pending.get(id,{})
    if q.is_empty() or String(v.get("query_token",""))!=String(q.token) or not v.get("visible") is bool:rejected+=1;return false
    pending.erase(id)
    if now-int(q.at_ms)>1500:client.call("LosReply",q.source,q.target,false);timeouts+=1;return false
    client.call("LosReply",q.source,q.target,bool(v.visible));native_replies+=1;return true
func maintain(client:Node,now:int)->void:
    for id in pending.keys():
        var q:Dictionary=pending[id]
        if now-int(q.at_ms)>1500:client.call("LosReply",q.source,q.target,false);pending.erase(id);timeouts+=1
func snapshot()->Array:
    var out:Array=[]
    for value in pending.values():
        var q:Dictionary=value.duplicate();q.erase("source");q.erase("target");q.erase("at_ms");out.append(q)
    return out
