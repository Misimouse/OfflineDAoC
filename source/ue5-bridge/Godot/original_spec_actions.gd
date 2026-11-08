extends RefCounted
## Specializations with an original DOL action handler. No inferred or locally granted skills.
func use(entry:Dictionary,server:Node,position:Vector3,heading:int,speed_mps:float,zone:int,visible:bool)->bool:
    if server==null or not bool(server.get("playing")) or zone!=207:return false
    if not position.is_finite() or not is_finite(speed_mps) or speed_mps<0 or speed_mps>100 or heading<0 or heading>4095:return false
    var parts:=String(entry.get("id","")).split(":")
    if parts.size()!=3 or parts[0]!="srv" or parts[1]!="spec" or not String(parts[2]).is_valid_int():return false
    var index:=int(parts[2]);var skills:Variant=server.get("skills")
    if not skills is Array or index<0 or index>=skills.size() or not skills[index] is Dictionary:return false
    var skill:Dictionary=skills[index]
    if int(skill.get("page",-1))!=0 or String(skill.get("name",""))!="Stealth" or int(skill.get("level",0))<=0:return false
    if String(entry.get("name",""))!="Stealth" or int(entry.get("level",-1))!=int(skill.level):return false
    var client:Variant=server.get("client")
    if not client is Node or not client.has_method("UseSkill") or not server.has_method("to_region"):return false
    var region:Vector3=server.call("to_region",zone,position)
    if not region.is_finite():return false
    client.call("UseSkill",region.x,region.y,region.z,speed_mps/.025,heading,visible,index,0)
    return true
