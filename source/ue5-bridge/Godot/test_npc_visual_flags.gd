extends SceneTree
var checks:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func _initialize()->void:
    var folder:String=get_script().resource_path.get_base_dir();var state=load(folder.path_join("npc_visual_flags.gd"));var original=load(folder.path_join("original_npc_flags.gd")).new()
    for flags in range(256):
        for flags2 in [0,1,2,4,7,128,255]:
            var d:={"flags":flags,"flags2":flags2};var row:Dictionary=state.decode(d);var reference:int=original.normalize(d)
            check(row.ghost==bool(reference&1) and row.torch_flag==bool(reference&64) and row.peace==bool(reference&16) and row.flying==bool(reference&32) and row.server_stealth_flag==bool(reference&2) and row.show_name==not bool(reference&4) and row.targetable==not bool(reference&8),"original NPC-create normalization %d/%d"%[flags,flags2])
    for bad in [true,false,-1,256,1.5,"1",null]:
        check(state.decode({"flags":bad,"flags2":0}).is_empty(),"invalid first byte rejected")
        check(state.decode({"flags":0,"flags2":bad}).is_empty(),"invalid second byte rejected")
    var ghost:Dictionary=state.decode({"flags":1,"flags2":0})
    for kind in ["move","player","player_move","model_change","equipment"]:
        var preserved:Dictionary=state.consume(kind,{"flags":0,"flags2":255},ghost)
        check(preserved==ghost and preserved.ghost and preserved.show_name,"unrelated packet cannot erase spawn visual flags: "+kind)
    var ordinary:Dictionary=state.consume("npc",{"flags":0,"flags2":0},ghost)
    check(not ordinary.ghost and ordinary.targetable,"new create on reused OID can restore ordinary appearance")
    check(not state.decode({"flags":4,"flags2":0}).ghost and state.decode({"flags":1,"flags2":0}).ghost,"torch cannot manufacture ghost")
    check(state.consume("npc",{},ghost).is_empty(),"missing create data cannot borrow previous identity")
    var copied:Dictionary=state.consume("move",{},ghost);copied.ghost=false;check(ghost.ghost,"snapshot copy cannot mutate original identity")
    var result:={"passed":failures.is_empty(),"checks":checks,"failures":failures,"candidate_only":true,"installed":false};FileAccess.open("res://npc_flags_tests.json",FileAccess.WRITE).store_string(JSON.stringify(result));print(JSON.stringify(result));quit(0 if failures.is_empty() else 1)
