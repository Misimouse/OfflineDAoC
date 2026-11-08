extends SceneTree
var adapter:Node
var cases:Array=[]
var checks:=0
var failures:Array=[]
var requests:Array=[]

func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)

func capture(label:String)->void:
    var rows:Array=adapter.entities.values().duplicate(true)
    cases.append({"label":label,"snapshot":{"type":"snapshot","protocol":"daoc-visual-bridge","version":1,
        "session":"entity-acceptance","seq":cases.size()+1,"zone_id":207,"origin_m":[1364,130,1263],"entities":rows}})

func spawn(oid:int,model:int=999980)->Dictionary:
    return {"oid":oid,"x":35*8192+56000,"y":51*8192+50000,"z":5200,"heading":0,
        "model":model,"name":"Probe","size":50,"speed":0}

func _initialize()->void:
    adapter=load("res://decoded_world_adapter.gd").new()
    adapter.zone_info={"x":35,"y":51}
    adapter.missing_entity.connect(func(oid):requests.append(oid))
    var you:=spawn(1);you.region=200
    adapter.consume_world("you",you)
    adapter.entities["player:local"].position_revision=1
    capture("local entry")
    adapter.consume_world("npc",spawn(2))
    adapter.consume_world("player",spawn(3))
    check(adapter.entities.has("npc:2") and adapter.entities.has("player:3"),"separate player and NPC identities")
    capture("NPC and remote player")
    adapter.consume_world("move",{"oid":3,"zone":207,"x":57000,"y":51000,"z":5200,"heading":1024,"speed":191,"health":42})
    var row:Dictionary=adapter.entities["player:3"]
    check(row.name=="Probe" and row.model_id==999980 and row.kind=="player","movement preserves appearance and remote kind")
    check(row.position_m==[1425.0,130.0,1275.0] and is_equal_approx(row.health,.42),"zone offset and health conversion")
    check(row.state=="run" and is_equal_approx(row.speed_mps,4.775),"running speed")
    check(is_equal_approx(row.forward_xz[0],-1.0) and absf(row.forward_xz[1])<.0001,"heading conversion")
    capture("remote movement")
    adapter.consume_world("move",{"oid":3,"zone":207,"x":57000,"y":51000,"z":5200,"speed":0})
    check(is_equal_approx(row.health,.42) and row.forward_xz[0]<-.99,"partial movement retains health and heading")
    adapter.consume_world("player",spawn(3))
    check(is_equal_approx(adapter.entities["player:3"].health,.42),"target-triggered create retains health")
    row=adapter.entities["player:3"]
    capture("partial update")
    adapter.consume_world("model_change",{"oid":3,"model":999981,"size":75})
    check(row.model_id==999981 and row.size==75 and row.name=="Probe","model change retains identity")
    capture("model changed")
    adapter.consume_world("death",{"oid":3})
    check(row.health==0.0 and row.state=="dead","death state")
    capture("death")
    adapter.consume_world("revive",{"oid":3})
    check(row.state=="idle" and row.health==1.0,"revive state")
    adapter.consume_world("object",{"oid":99})
    adapter.consume_world("remove",{"oid":99,"type":9})
    check(adapter.entities.has("player:3") and not adapter.non_living.has(99),"deleting a different ground OID leaves living intact")
    adapter.consume_world("remove",{"oid":3,"type":9})
    check(not adapter.entities.has("player:3") and not adapter.oid_to_id.has(3),"original ObjectDelete removes a hidden player without a corpse")
    adapter.consume_world("player",spawn(3))
    check(adapter.entities.has("player:3"),"original PlayerCreate restores a revealed player")
    capture("revive and object remove")
    adapter.consume_world("remove",{"oid":3,"type":2})
    check(not adapter.entities.has("player:3"),"remote player removal")
    capture("remote removed")
    adapter.consume_world("npc",spawn(3))
    check(adapter.entities.has("npc:3") and not adapter.entities.has("player:3"),"reused ID changes kind")
    capture("ID reused by NPC")
    adapter.consume_world("move",{"oid":3,"zone":208,"x":0,"y":0,"z":0})
    check(not adapter.entities.has("npc:3"),"out of supported zone removed")
    adapter.consume_world("move",{"oid":88,"zone":207,"x":0,"y":0,"z":0})
    check(not adapter.oid_to_id.has(88),"unknown movement does not invent a living")
    adapter.consume_world("move",{"oid":88,"zone":207,"x":0,"y":0,"z":0})
    check(requests==[88],"unknown creation request is throttled")
    adapter.consume_world("object",{"oid":89,"door":207033701})
    adapter.consume_world("move",{"oid":89,"zone":207,"x":0,"y":0,"z":0})
    check(requests==[88],"known world objects never requested as livings")
    var local:Dictionary=adapter.entities["player:local"]
    local.position_m=[1402.0,130.0,1250.0];local.position_revision=2
    capture("authoritative short local teleport")
    adapter.consume_world("region_changed",{})
    check(adapter.entities.is_empty() and adapter.oid_to_id.is_empty(),"region clears stale entities")
    capture("region changed")
    adapter.consume_world("you",you)
    check(adapter.entities.size()==1 and adapter.entities.has("player:local"),"new entry starts fresh")
    capture("re-entry")
    adapter.consume_world("quit",{})
    check(adapter.entities.is_empty(),"quit clears entities")
    capture("quit")
    var output:String=get_script().resource_path.get_base_dir().path_join("../Reports/entities/godot_lifecycle.json")
    var file:=FileAccess.open(output,FileAccess.WRITE)
    file.store_string(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures,"cases":cases},"  "));file.close()
    print("ENTITY_LIFECYCLE ",checks," checks; failures=",failures)
    adapter.free()
    quit(0 if failures.is_empty() else 1)
