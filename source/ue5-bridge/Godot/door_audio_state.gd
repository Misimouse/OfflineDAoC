extends RefCounted
## Original sounds from acknowledged loaded-door transitions, never predicted clicks.
var positions:Dictionary={}
var sets:Dictionary={}
var states:Dictionary={}
var requests:Dictionary={}

func configure(loaded:Dictionary,sound_sets:Dictionary)->void:
    positions=loaded;sets=sound_sets;reset()
func reset()->void:
    states.clear();requests.clear()
func request(id:int,open:bool,now:int)->void:
    if positions.has(id):requests[id]={"open":open,"at":now}
func consume(kind:String,data:Dictionary,audio,now:int)->void:
    if kind in ["you","region_changed","quit"]:reset();return
    if kind!="door_state" or not data.get("open") is bool:return
    var id:=int(data.get("door_id",-1))
    if not positions.has(id):return
    var point=positions[id]
    if not point is Array or point.size()!=3:return
    for value in point:
        if not (value is int or value is float) or not is_finite(float(value)):return
    var open:bool=data.open
    var known:=states.has(id)
    var previous:bool=bool(states.get(id,false))
    var pending:Dictionary=requests.get(id,{})
    var confirmed:bool=not pending.is_empty() and pending.open==open and now-int(pending.at)>=0 and now-int(pending.at)<=5000
    requests.erase(id);states[id]=open
    # A first unsolicited state is hydration, including joining beside an open
    # door. An explicit local request still needs the actual server response.
    if (known and previous==open) or (not known and not confirmed):return
    var flag:=int(data.get("flag",0))
    var event:="open" if open else "close"
    if flag<=0 or String(sets.get(str(flag),{}).get(event,"")).is_empty():return
    var owner:="door:"+str(id)
    audio.emit(owner,{owner:{"position_m":point}},"doors",flag,event,now)
