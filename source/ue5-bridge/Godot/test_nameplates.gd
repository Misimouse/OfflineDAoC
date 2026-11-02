extends SceneTree
var failures:Array=[]
var checks:=0
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func _initialize()->void:
    var a=load("res://decoded_world_adapter.gd").new();a.zone_info={"x":35,"y":51};a.player_level=50;a.player_realm=3
    var data=JSON.parse_string(FileAccess.get_file_as_string("C:/Gogot/Download-OfflineDAoC-v0.37c/playable-v0.37c-classic/new-client/godot/content/zones/zone207/npcs.json"));a.con_table=data.con
    var headings:Array=[0,1024,2048,3072]
    var directions:Array=[[0.0,1.0],[-1.0,0.0],[0.0,-1.0],[1.0,0.0]]
    for i in range(4):
        a.consume_world("npc",{"oid":40+i,"x":35*8192+56000+i*40,"y":51*8192+50000,"z":5200,"heading":headings[i],"model":999980,"flags":192,"flags2":0,"level":35,"name":"Cardinal","guild":"Merchant","size":50,"speed":0})
        var row:Dictionary=a.entities["npc:"+str(40+i)];var f:Array=row.forward_xz
        check(Vector2(f[0],f[1]).distance_to(Vector2(directions[i][0],directions[i][1]))<.00001,"packet cardinal "+str(headings[i]))
        var returned:=int(round(atan2(-float(f[0]),float(f[1]))*4096.0/TAU))&4095
        check(returned==headings[i],"movement heading roundtrip "+str(headings[i]))
        var plate:Dictionary=a.nameplate(row)
        check(plate.color_rgb==[175,223,208] and plate.friendly,"friendly name palette")
        check(plate.range_m==40.0 and plate.show,"same name range")
    a.consume_world("move",{"oid":40,"zone":207,"x":56000,"y":50000,"z":5200,"heading":0,"speed":100,"flags":0})
    check(a.nameplate(a.entities["npc:40"]).friendly,"movement flags must not change NPC realm")
    var enemy:Dictionary=a.entities["npc:40"].duplicate(true);enemy.realm=0
    for level in [1,35,45,50,55,60,90]:
        enemy.level=level
        var p:Dictionary=a.nameplate(enemy)
        var con:int=int(a.con_table[50][level]) if level<61 else 3
        check(p.color_rgb==a.CON_PALETTE[con],"con table palette level "+str(level))
    a.consume_world("npc",{"oid":99,"x":35*8192+56000,"y":51*8192+50000,"z":5200,"heading":0,"model":999980,"flags":192,"flags2":2,"level":35})
    check(not a.nameplate(a.entities["npc:99"]).show,"do-not-show-name flag")
    var f:=FileAccess.open("res://../Reports/nameplates/godot_tests.json",FileAccess.WRITE);f.store_string(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures},"  "));f.close()
    print("NAMEPLATE_CHECKS ",checks," failures=",failures);a.free();quit(0 if failures.is_empty() else 1)
