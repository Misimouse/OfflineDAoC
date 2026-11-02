extends SceneTree
var checks:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func _initialize()->void:
    var base:String=get_script().resource_path.get_base_dir().path_join("..")
    var source:="C:/Gogot/Download-OfflineDAoC-v0.37c/playable-v0.37c-classic/new-client/godot/content"
    var catalog:Dictionary=JSON.parse_string(FileAccess.get_file_as_string(base.path_join("models.json")))
    var weapons:Dictionary=JSON.parse_string(FileAccess.get_file_as_string(source+"/weapons/weapons.json")).models
    var styles:Dictionary=JSON.parse_string(FileAccess.get_file_as_string(source+"/rules/style_anims.json"))
    var clips:Dictionary=JSON.parse_string(FileAccess.get_file_as_string(source+"/characters/style_clips.json"))
    var m=load("res://combat_visual_state.gd").new();m.configure(catalog,weapons,styles,clips)
    var entities:Dictionary={"player:local":{"model_id":0,"health":1.0,"state":"idle"},"npc:2":{"model_id":123,"health":1.0,"state":"idle"}}
    var before:Dictionary=entities.duplicate(true);var ids:Dictionary={2:"npc:2"}
    var packet:Dictionary={"attacker":1,"defender":2,"weapon":445,"style":0,"result":10,"health":50}
    m.consume(packet,1,ids,entities,1000)
    var local:Dictionary=m.snapshot("player:local",1100);var mob:Dictionary=m.snapshot("npc:2",1100)
    check(local.events.size()==1 and String(local.events[0].clip) in ["attack_med","attack_high","attack_low"],"actual melee packet selects an available original swing")
    check(not local.events[0].if_idle and local.events[0].age_ms==100,"swing age and interruption rule retained")
    check(mob.events.size()==1 and mob.events[0].clip=="flinch" and mob.events[0].if_idle,"actual hit offers a noninterrupting flinch")
    check(entities==before,"visual events cannot mutate HP, position or authority")
    check(local.seq==m.snapshot("player:local",1200).seq and m.snapshot("player:local",1200).events[0].age_ms==200,"repeated snapshots never create or rejuvenate events")
    m.reset();packet.result=0x14;m.consume(packet,1,ids,entities,2000);check(m.snapshot("player:local",2000).is_empty(),"spell damage cannot swing the caster's weapon");check(m.snapshot("npc:2",2000).events[0].clip=="flinch","spell impact may flinch the actual defender")
    m.reset();packet.result=0x94;m.consume(packet,1,ids,entities,2000);check(m.snapshot("player:local",2000).is_empty(),"masked spell result also suppresses melee")
    m.reset();packet.result=11;packet.style=0x3E80;packet.health=0;m.consume(packet,1,ids,entities,3000);check(m.events.is_empty()and entities==before,"bow prepare cannot swing or flinch or damage anyone")
    m.reset();packet.style=0x3E83;packet.result=10;m.consume(packet,1,ids,entities,3000);check(m.snapshot("player:local",3000).is_empty(),"bow shoot is never a sword swing")
    var bow_id:=0
    for id in weapons:
        if int(weapons[id].get("stance",0))==5:bow_id=int(id);break
    m.reset();packet.weapon=bow_id;packet.style=0;m.consume(packet,1,ids,entities,3000);check(m.snapshot("player:local",3000).is_empty(),"arrow impacts with ordinary style also suppress melee")
    m.reset();packet.weapon=445;packet.style=0x3E81;packet.result=11;m.consume(packet,1,ids,entities,4000);check(String(m.snapshot("player:local",4000).events[0].clip).begins_with("attack_left_"),"actual off-hand code selects left attack")
    m.reset();packet.style=0x3E82;m.consume(packet,1,ids,entities,4000);check(String(m.snapshot("player:local",4000).events[0].clip).begins_with("attack_dual_"),"actual dual-weapon code selects dual attack")
    var chosen_style:=-1;var chosen_clip:=""
    for id in styles:
        var name:=String(clips.get(str(int(styles[id])),""))
        if int(id)>0 and catalog["0"].has(name):chosen_style=int(id);chosen_clip=name;break
    check(chosen_style>0,"real style definition with exported clip available")
    m.reset();packet.style=chosen_style;m.consume(packet,1,ids,entities,4100);check(m.snapshot("player:local",4100).events[0].clip==chosen_clip,"style packet maps through original style and canims tables")
    m.reset();packet.style=65534;m.consume(packet,1,ids,entities,4200);check(String(m.snapshot("player:local",4200).events[0].clip) in ["attack_med","attack_high","attack_low"],"missing style falls back to the original generic family")
    m.reset();packet.attacker=2;packet.defender=1;packet.style=0;packet.result=1;m.consume(packet,1,ids,entities,5000,"2h");check(String(m.snapshot("player:local",5000).events[0].clip).begins_with("parry_2h_"),"local defence respects actual main-weapon stance")
    m.reset();packet.attacker=1;packet.defender=2;packet.result=2;m.consume(packet,1,ids,entities,5000);check(m.snapshot("npc:2",5000).is_empty(),"creature without a block clip gets no invented defence")
    m.reset();packet.attacker=90000;packet.defender=90001;packet.result=10;m.consume(packet,1,ids,entities,5000);check(m.events.is_empty()and entities==before,"unknown combatants do not become invented entities")
    m.reset();packet.attacker=1;packet.defender=2;packet.result=10;entities["player:local"].health=0;entities["player:local"].state="dead";m.consume(packet,1,ids,entities,5000);check(m.snapshot("player:local",5000).is_empty(),"dead attacker cannot receive a living swing")
    entities["player:local"].health=1;entities["player:local"].state="idle";m.reset()
    for i in range(12):m.consume(packet,1,ids,entities,6000+i*10)
    var queue:Dictionary=m.snapshot("player:local",6200);check(queue.events.size()==8,"burst queue is bounded")
    for i in range(1,queue.events.size()):check(int(queue.events[i].seq)>int(queue.events[i-1].seq),"queued events preserve order")
    check(m.snapshot("player:local",12000).is_empty(),"old combat announcements expire")
    m.remove("player:local");check(not m.events.has("player:local")and not m.fighting.has("player:local"),"revive or model reset removes old actions")
    m.prune({});check(m.events.is_empty()and m.fighting.is_empty(),"removed entities leave no visual cache")
    m.reset();packet.attacker=1;packet.defender=2;m.consume(packet,1,ids,entities,13000,"",true);check(m.snapshot("player:local",13000).is_empty(),"real local death/unknown HP overrides stale adapter local row")
    var file:=FileAccess.open(base.path_join("Reports/combat_visual/godot_tests.json"),FileAccess.WRITE);file.store_string(JSON.stringify({"checks":checks,"passed":failures.is_empty(),"failures":failures},"  "));file.close();print("COMBAT_VISUAL_CHECKS ",checks," failures=",failures);quit(0 if failures.is_empty() else 1)
