extends RefCounted
## Local draw/sheathe audio follows original AttackMode ACKs, never input requests.
var armed:=false
var drawn_model:=0

func reset()->void:
    armed=false;drawn_model=0

func consume(kind:String,data:Dictionary,me:int,audio:RefCounted,entities:Dictionary,inventory,now:int)->void:
    if kind in ["you","region_changed","quit"]:reset();return
    if (kind=="death" and int(data.get("oid",0))==me) or (kind=="status" and int(data.get("health_pct",-1))==0):
        # Death removes weapon mode; a corpse is not audibly sheathing an item.
        reset();return
    if kind!="attack_mode":return
    var on:=bool(data.get("on",false))
    if on==armed:return
    var row:Dictionary=entities.get("player:local",{})
    if row.is_empty() or (on and (String(row.get("state",""))=="dead" or float(row.get("health",1))<=0)):
        reset();return
    var model:=drawn_model
    if on:
        var slot:int={"standard":10,"twohand":12,"ranged":13}.get(String(inventory.weapon_set),10)
        model=int(inventory.items.get(slot,{}).get("model",0))
    armed=on;drawn_model=model if on else 0
    var set_id:int=audio.weapon_set(model)
    if set_id>0:audio.emit("player:local",entities,"weapons",set_id,"activate" if on else "deactivate",now)
