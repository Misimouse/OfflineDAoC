extends RefCounted
## Candidate only. NPC-create bit meanings are independent of movement/player action flags.
static func decode(data:Dictionary)->Dictionary:
    var flags:Variant=data.get("flags");var flags2:Variant=data.get("flags2")
    if typeof(flags)!=TYPE_INT or typeof(flags2)!=TYPE_INT or flags<0 or flags>255 or flags2<0 or flags2>255:return {}
    return {"known":true,"ghost":(flags&1)!=0,"torch_flag":(flags&4)!=0,"peace":(flags&16)!=0,"flying":(flags&32)!=0,"realm":flags>>6,"show_name":(flags2&2)==0,"targetable":(flags2&1)==0,"server_stealth_flag":(flags2&4)!=0,"source_packet":"npc_create"}
static func consume(kind:String,data:Dictionary,previous:Dictionary)->Dictionary:
    # Move flags also encode zone bits. They must never change a spawn's visual identity.
    if kind!="npc":return previous.duplicate(true)
    return decode(data)
