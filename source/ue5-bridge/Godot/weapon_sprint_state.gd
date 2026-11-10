extends RefCounted
## Original server requests only. Equipment/speed/endurance remain authoritative.
const ACTIONS := ["weapon_select","player_sprint"]
const SLOTS := {"standard":10,"twohand":12,"ranged":13}
var last_request:=-10000
var last_request_key:=""
func reset()->void:
    last_request=-10000;last_request_key=""
func request(value:Dictionary,server:Node,inventory:RefCounted,state:RefCounted,pose:Node3D,zone:int,now:int)->bool:
    var action:Variant=value.get("action")
    if not action is String or action not in ACTIONS:return false
    if server==null or not server.playing or pose==null or not state.ready or not state.alive():return false
    var generation:Variant=value.get("player_generation")
    if typeof(generation) not in [TYPE_INT,TYPE_FLOAT] or not is_finite(float(generation)) or float(generation)!=float(state.generation):return false
    var mode_key:Variant=value.get("mode","")
    var request_key:String=action+(":"+mode_key if mode_key is String else "")
    if zone!=207 or (request_key==last_request_key and now-last_request<200):return false
    if action=="player_sprint":
        server.command("/sprint")
    else:
        var mode:Variant=value.get("mode")
        if not mode is String or not SLOTS.has(mode):return false
        if inventory.inventory_events<=0 or inventory.fingerprint.is_empty() or not inventory.pending.is_empty():return false
        var revision:Variant=value.get("inventory_revision")
        if typeof(revision) not in [TYPE_INT,TYPE_FLOAT] or not is_finite(float(revision)) or float(revision)!=float(inventory.state_revision):return false
        var slot:int=SLOTS[mode]
        var item:Dictionary=inventory.items.get(slot,{})
        if item.is_empty() or not value.get("item_token") is String or value.item_token!=String(item.get("token","")) or value.item_token.is_empty():return false
        server.switch_weapon(mode,pose,zone)
    last_request=now;last_request_key=request_key
    return true
