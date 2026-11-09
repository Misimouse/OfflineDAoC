extends Node
## Decoded living state only. Networking remains in the original client.
signal missing_entity(oid: int)
signal missing_player(session: int)
var requested_players:Dictionary={}
var requested:Dictionary={}
var non_living:Dictionary={}
var bridge: Node
var entities: Dictionary = {}
var zone_info: Dictionary = {}
var client: Node
var source_label := "live-decoded-world"
var events := 0
var last_publish := 0
var equipment_packets:Dictionary={}
var equipment_revision:=0
var local_oid := -1
var player_level:=1
var player_realm:=3
var con_table:Array=[]
const CON_PALETTE={-3:[130,129,128],-2:[135,225,113],-1:[85,93,214],0:[197,193,0],1:[254,131,49],2:[245,0,0],3:[199,89,255]}
var oid_to_id: Dictionary = {}
var motion_sequence:=0
var motion_intervals:Array=[]
var motion_event_count:=0
var motion_trace:Array=[]
var record_motion:=false
var corpses:Dictionary={}
var corpse_serial:=0
const CORPSE_MS:=12000
const SINK_MS:=4000
const NPCVisualFlags=preload("npc_visual_flags.gd")


func clear_world() -> void:
    corpses.clear()
    equipment_packets.clear()
    entities.clear()
    oid_to_id.clear()
    requested.clear()
    requested_players.clear()
    non_living.clear()
    local_oid=-1

func bind_client(value: Node, transport: Node, info: Dictionary) -> void:
    client = value; bridge = transport; zone_info = info.duplicate()
    client.connect("World", consume_world)
    client.connect("Disconnected", func(_why):
        clear_world(); bridge.publish([],207,source_label))

func _position(data: Dictionary, offsets: bool = false) -> Vector3:
    return Vector3((float(data.x)-(0.0 if offsets else float(zone_info.x)*8192.0))*.025,
        float(data.z)*.025,(float(data.y)-(0.0 if offsets else float(zone_info.y)*8192.0))*.025)

func _inside(p: Vector3) -> bool:
    return p.is_finite() and p.x >= 0 and p.z >= 0 and p.x <= 1638.4 and p.z <= 1638.4

func _erase(oid: int) -> void:
    if oid_to_id.has(oid):entities.erase(oid_to_id[oid])
    oid_to_id.erase(oid)

func _update(row: Dictionary, data: Dictionary) -> void:
    if data.has("heading"):
        var angle := -float(data.heading)*TAU/4096.0
        row.forward_xz = [sin(angle),cos(angle)]
        row.heading_4096=int(data.heading)&4095
    if data.has("speed"):
        row.speed_mps = float(data.speed)*.025
        row.state = "run" if absf(row.speed_mps)>3.75 else ("walk" if absf(row.speed_mps)>0 else "idle")
    if data.has("health") and _health_percent(data.health)>=0:row.health=float(data.health)/100.0;row.health_known=true
    if float(row.health)<=0:row.state="dead"
    for key in ["name","size","level","guild"]:
        if data.has(key):row[key]=data[key]
    if data.has("model"):row.model_id=int(data.model)
    if data.has("flags2"):
        row.targetable=(int(data.flags2)&1)==0
        row.show_name=(int(data.flags2)&2)==0
    if data.has("level"):row.level=int(data.level)&127

func _player_position(data:Dictionary)->void:
    for key in ["oid","session"]:
        var v:Variant=data.get(key)
        if typeof(v) not in [TYPE_INT,TYPE_FLOAT] or not is_finite(float(v)) or float(v)!=floor(float(v)) or float(v)<1 or float(v)>65535:return
    var oid:=int(data.get("oid",0))
    if oid<=0 or oid>65535 or oid==local_oid:return
    if not oid_to_id.has(oid):
        var session:=int(data.session)
        var now:=Time.get_ticks_msec()
        if now-int(requested_players.get(session,-100000))>=3000:
            if requested_players.size()>=2048:requested_players.clear()
            requested_players[session]=now;missing_player.emit(session)
        return
    var id:String=String(oid_to_id[oid]);var row:Dictionary=entities.get(id,{})
    if row.get("kind","")!="player" or int(row.get("session_id",0))<=0 or int(data.get("session",0))!=int(row.session_id):return
    for key in ["x","y","z","speed","speed_z","heading","state_flags","action_flags","health"]:
        var v:Variant=data.get(key)
        if typeof(v) not in [TYPE_INT,TYPE_FLOAT] or not is_finite(float(v)):return
    for key in ["session","oid","zone","heading","state_flags","action_flags","health"]:
        var v:Variant=data.get(key)
        if typeof(v) not in [TYPE_INT,TYPE_FLOAT] or not is_finite(float(v)) or float(v)!=floor(float(v)) or float(v)<0 or float(v)>65535:return
    if int(data.health)>100 or int(data.state_flags)>255 or int(data.action_flags)>255 or not data.get("combat_active") is bool:return
    if int(data.zone)!=207:_erase(oid);return
    var p:=_position(data)
    if not _inside(p):_erase(oid);return
    var mode:=int(data.state_flags)&0x1c
    var values:Dictionary=data.duplicate()
    if mode==0x18:values.erase("heading") # while riding, heading contains a steed OID
    row.position_m=[p.x,p.y,p.z];_update(row,values)
    row.remote_sitting=mode==0x10;row.remote_swimming=mode==4;row.remote_climbing=mode==0x1c;row.remote_riding=mode==0x18
    row.torch_on=(int(data.action_flags)&0x80)!=0;row.diving=(int(data.action_flags)&4)!=0;row.stealthed=(int(data.action_flags)&2)!=0
    row.combat_active=data.combat_active;row.remote_combat_active=data.combat_active;row.remote_ladder_rate=clampf(float(data.speed_z)/85.0,-2.0,2.0)
    if float(row.health)>0:
        if row.remote_sitting:row.state="sit_idle"
        elif row.remote_swimming:row.state="swim"
        elif row.remote_climbing:row.state="ladder"
        elif row.remote_riding:row.state="ride_horse"
        elif float(data.speed)<0:row.state="walk_back"
    _motion_sample(row,data,"move")
    var direction:Array=row.forward_xz.duplicate();var strafe:=int(data.state_flags)&0xc0
    if strafe==0x40:direction=[-float(direction[1]),float(direction[0])]
    elif strafe==0x80:direction=[float(direction[1]),-float(direction[0])]
    if float(data.speed)<0:direction=[-float(direction[0]),-float(direction[1])]
    row.motion.direction_xz=direction;row.motion.speed_mps=absf(float(data.speed)*.025)
    row.motion.source_packet="player_position1127"

func consume_world(kind: String, data: Dictionary) -> void:
    events += 1
    if kind=="player_move":_player_position(data);return
    if kind in ["region_changed","quit"]:
        clear_world();return
    if kind == "you":
        clear_world();local_oid=int(data.oid)
        if int(data.get("region",200))!=200:return
        var p:=_position(data)
        if not _inside(p):return
        var row:Dictionary={"id":"player:local","kind":"player","name":"Player","model_id":0,
            "position_m":[p.x,p.y,p.z],"forward_xz":[0,1],"size":50,"health":1.0,"state":"idle","speed_mps":0.0}
        _update(row,data);entities[row.id]=row;oid_to_id[local_oid]=row.id
        return
    if kind=="combat":
        for key in ["attacker","defender"]:_request_missing(int(data.get(key,0)))
        # Drawing a bow announces an animation, not a hit.
        if int(data.get("style",0))==0x3E80:return
        var defender:=int(data.get("defender",0))
        var health:=_health_percent(data.get("health",-1))
        if defender!=local_oid and oid_to_id.has(defender) and health>=0:
            var row:Dictionary=entities[oid_to_id[defender]]
            row.health=float(health)/100.0;row.health_known=true
            if health==0 and String(row.state)!="dead":
                row.state="dead";row.speed_mps=0.0;_motion_sample(row,{},"death")
        return
    if not data.has("oid"):return
    var oid:=int(data.oid)
    if kind=="equipment":
        if oid<=0 or oid>65535:return
        equipment_revision+=1
        var gear:={"items":data.get("items",[]).duplicate(true),"weapon_slots":int(data.get("weapon_slots",255)),"revision":equipment_revision,
            "hood":(int(data.get("hood",0))&1)!=0,"cloak_hidden":(int(data.get("hidden",0))&1)!=0,"helm_hidden":(int(data.get("hidden",0))&2)!=0}
        if equipment_packets.size()<2048 or equipment_packets.has(oid):equipment_packets[oid]=gear
        if oid_to_id.has(oid) and entities.has(oid_to_id[oid]):entities[oid_to_id[oid]]["equipment"]=gear
        return
    if kind == "object":
        non_living[oid]=true;return
    if kind == "move" and not oid_to_id.has(oid) and not non_living.has(oid) and oid!=local_oid and oid>0 and oid<=65535 and int(data.get("zone",-1))==207:
        _request_missing(oid)
    if kind == "remove":
        requested.erase(oid)
        equipment_packets.erase(oid)
        if int(data.get("type",1))==9:non_living.erase(oid)
        # Original ObjectDelete is generic: DOL also uses it to hide a stealthed player.
        # OIDs share one current world identity. Retained NPC corpses have already detached it.
        if int(data.get("type",1))==0:_keep_corpse(oid,Time.get_ticks_msec())
        else:_erase(oid)
        return
    if oid==local_oid:return
    if kind in ["npc","player"]:
        var p:=_position(data)
        requested.erase(oid);non_living.erase(oid)
        var id:=kind+":"+str(oid)
        # A reused server OID is a new living, never a resurrection of a corpse.
        if corpses.has(id):
            corpse_serial+=1
            var corpse_id:="corpse:"+str(oid)+":"+str(corpse_serial)
            var body:Dictionary=entities[id];body.id=corpse_id
            entities[corpse_id]=body;corpses[corpse_id]=corpses[id]
            entities.erase(id);corpses.erase(id)
        var previous:Dictionary=entities.get(id,{})
        _erase(oid)
        if not _inside(p):return
        var row:Dictionary=previous if not previous.is_empty() else {"id":id,"kind":kind,"name":"","model_id":0,"size":50,
            "forward_xz":[0,1],"health":1.0,"state":"idle","speed_mps":0.0}
        row.position_m=[p.x,p.y,p.z]
        if equipment_packets.has(oid):row["equipment"]=equipment_packets[oid].duplicate(true)
        _update(row,data)
        if kind=="player":
            row.session_id=int(data.get("session",0));row.realm=(int(data.get("flags",0))>>2)&3
        if kind=="npc" and data.has("flags"):
            row.realm=int(data.flags)>>6;row.flying=(int(data.flags)&32)!=0
        if kind=="npc":
            # Only the create packet owns these bits. Movement flags encode zones.
            # Replace, never merge: a reused OID must not inherit a prior ghost.
            row.npc_visual=NPCVisualFlags.decode(data)
        _motion_sample(row,data,kind)
        entities[id]=row;oid_to_id[oid]=id
    elif oid_to_id.has(oid):
        var row:Dictionary=entities[oid_to_id[oid]]
        if kind == "move":
            if int(data.get("zone",-1))!=207:_erase(oid);return
            var p:=_position(data,true)
            if not _inside(p):_erase(oid);return
            row.position_m=[p.x,p.y,p.z]
            _update(row,data)
            _motion_sample(row,data,kind)
        elif kind == "model_change":_update(row,data)
        elif kind == "death":
            row.health=0.0;row.state="dead";row.speed_mps=0.0
            _motion_sample(row,{},kind)
        elif kind == "revive":
            row.health=1.0;row.state="idle";row.speed_mps=0.0
            _motion_sample(row,{},kind)

func _keep_corpse(oid:int,now:int)->void:
    var id:String=String(oid_to_id.get(oid,""))
    if id.is_empty() or not entities.has(id):return
    var row:Dictionary=entities[id]
    if row.get("kind","")!="npc":_erase(oid);return
    if String(row.get("state",""))!="dead":_motion_sample(row,{},"death")
    row.health=0.0;row.health_known=true;row.state="dead";row.speed_mps=0.0
    row.targetable=false;row.show_name=false;row.combat_active=false
    # Detach the server identity, retaining the same UE actor for death playback.
    oid_to_id.erase(oid)
    if row.has("motion"):
        row.motion.event="death";row.motion.position_valid=false;row.motion.speed_mps=0.0;row.motion.erase("destination_m")
    corpses[id]={"at_ms":now,"death_at_ms":int(row.get("motion",{}).get("at_ms",now)),"position":row.position_m.duplicate()}
    if corpses.size()>128:
        var oldest:String=String(corpses.keys()[0]);entities.erase(oldest);corpses.erase(oldest)

func advance_corpses(now:int)->void:
    for id in corpses.keys():
        if not entities.has(id):corpses.erase(id);continue
        var body:Dictionary=corpses[id];var age:int=maxi(0,now-int(body.at_ms))
        if age>=CORPSE_MS+SINK_MS:entities.erase(id);corpses.erase(id);continue
        if age>CORPSE_MS:
            var row:Dictionary=entities[id];var p:Array=body.position
            var depth:float=lerpf(0.0,2.0*maxf(.1,float(row.get("size",50))/50.0),float(age-CORPSE_MS)/SINK_MS)
            row.position_m=[p[0],float(p[1])-depth,p[2]]
            # Position-valid update lets the native corpse follow the sinking body.
            if not row.has("motion"):row.motion={}
            motion_sequence+=1
            row.motion={"seq":motion_sequence,"at_ms":int(body.death_at_ms),"age_ms":now-int(body.death_at_ms),"interval_ms":50,"event":"death","position_valid":true,"speed_mps":0.0}

func _health_percent(value)->int:
    if not (value is int or value is float) or not is_finite(float(value)) or float(value)!=floor(float(value)):return -1
    return int(value) if value>=0 and value<=100 else -1

func _request_missing(oid:int)->void:
    if oid<=0 or oid>65535 or oid==local_oid or oid_to_id.has(oid) or non_living.has(oid):return
    var now:=Time.get_ticks_msec()
    if now-int(requested.get(oid,-100000))<3000:return
    if requested.size()>=2048:requested.clear()
    requested[oid]=now;missing_entity.emit(oid)

func _process(_delta: float) -> void:
    if bridge != null and Time.get_ticks_msec()-last_publish>=50:
        last_publish=Time.get_ticks_msec();bridge.publish(entities.values(),207,source_label)

func nameplate(row:Dictionary)->Dictionary:
    var friendly:bool=int(row.get("realm",0))==player_realm
    var con:=0
    if player_level>=0 and player_level<con_table.size():
        var levels:Array=con_table[player_level]
        var level:int=int(row.get("level",0))
        con=int(levels[level]) if level>=0 and level<levels.size() else 3
    return {"color_rgb":[175,223,208] if friendly else CON_PALETTE.get(con,[255,255,255]),
        "show":bool(row.get("show_name",true)) and bool(row.get("targetable",true)),"range_m":40.0,"friendly":friendly,"con":con}

func _motion_sample(row:Dictionary,data:Dictionary,kind:String)->void:
    var now:=Time.get_ticks_msec()
    var previous:Dictionary=row.get("motion",{})
    var interval:=float(previous.get("interval_ms",500.0))
    if kind=="move" and previous.has("at_ms"):
        var delta:int=now-int(previous.at_ms)
        if delta>=50 and delta<=5000:
            motion_intervals.append(delta)
            if motion_intervals.size()>2048:motion_intervals.pop_front()
            interval=lerpf(interval,float(delta),.25)
    motion_sequence+=1;motion_event_count+=1
    var motion:Dictionary={"seq":motion_sequence,"at_ms":now,"age_ms":0,"interval_ms":interval,"event":kind,"position_valid":kind in ["npc","player","move"],"speed_mps":row.get("speed_mps",0.0)}
    if kind=="move" and int(data.get("tzone",-1))==207 and (int(data.get("tx",0))!=0 or int(data.get("ty",0))!=0):
        motion.destination_m=[float(data.tx)*.025,float(data.get("tz",0))*.025,float(data.ty)*.025]
    elif kind in ["npc","player"] and previous.has("destination_m") and float(motion.speed_mps)>0:
        motion.destination_m=previous.destination_m
    row.motion=motion
    if record_motion and motion_trace.size()<20000:
        motion_trace.append({"id":row.id,"at_ms":now,"position_m":row.position_m.duplicate(),"forward_xz":row.forward_xz.duplicate(),"state":row.state,"motion":motion.duplicate(true)})

func motion_report()->Dictionary:
    var intervals:Array=motion_intervals.duplicate();intervals.sort()
    return {"events":motion_event_count,"interval_count":intervals.size(),
        "interval_p50_ms":intervals[int(intervals.size()*.5)] if not intervals.is_empty() else 0,
        "interval_p95_ms":intervals[mini(int(intervals.size()*.95),intervals.size()-1)] if not intervals.is_empty() else 0}
