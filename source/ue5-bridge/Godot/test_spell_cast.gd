extends SceneTree
var n:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:n+=1;if not ok:failures.append(label)
func _initialize()->void:
    var model=load("res://spell_cast_state.gd").new();model.configure({"effects":{"12":{"name":"Spell test","anims":["cast_crossed_start","cast_crossed_mid","cast_crossed_end"]}}});var ids:={7:"npc:7"}
    check(model.snapshot("player:local",0).is_empty(),"requests do not create an optimistic cast")
    model.consume("cast",{"caster":1,"spell":12,"time":30},1,ids,1000);var c:Dictionary=model.snapshot("player:local",1500)
    check(c.phase=="casting" and c.duration_ms==3000 and c.age_ms==500,"server tenths become actual casting duration")
    check(c.name=="Spell test" and c.anims[1]=="cast_crossed_mid","original effect definition chooses casting style")
    check(model.snapshot("player:local",6000).phase=="unconfirmed","elapsed cast never invents successful completion")
    check(model.snapshot("player:local",9000).is_empty(),"silent cast cannot leave UI stuck")
    model.consume("spell_effect",{"caster":1,"spell":13,"success":1},1,ids,1800);check(model.snapshot("player:local",1900).phase=="casting","unrelated effect cannot finish a cast")
    model.consume("interrupt",{"caster":7},1,ids,1900);check(model.snapshot("player:local",2000).phase=="casting","remote interruption cannot interrupt local player")
    model.consume("interrupt",{"caster":1},1,ids,2100);check(model.snapshot("player:local",2100).phase=="interrupted","original interrupt terminates local pose and progress")
    model.consume("spell_effect",{"caster":1,"spell":12,"success":1},1,ids,2200);check(model.snapshot("player:local",2200).phase=="interrupted","late effect cannot undo interruption")
    model.consume("cast",{"caster":1,"spell":12,"time":20},1,ids,3000);model.consume("spell_effect",{"caster":1,"spell":12,"success":0},1,ids,5000);c=model.snapshot("player:local",5100)
    check(c.phase=="released" and c.resisted and c.age_ms==100,"release and resisted result remain server derived")
    model.consume("cast",{"caster":1,"spell":12,"time":0},1,ids,6000);c=model.snapshot("player:local",6000);check(c.instant and c.phase=="instant","instant has no fabricated casting progress")
    model.consume("spell_effect",{"caster":1,"spell":12,"success":1},1,ids,6001);check(model.snapshot("player:local",6001).instant,"instant release cannot gain a windup pose")
    model.consume("cast",{"caster":7,"spell":12,"time":10},1,ids,6100);check(not model.snapshot("npc:7",6150).is_empty(),"remote NPC can display original cast")
    model.consume("remove",{"oid":7},1,ids,6200);check(model.snapshot("npc:7",6200).is_empty(),"removal clears remote casting")
    model.consume("death",{"oid":1},1,ids,6300);model.consume("cast",{"caster":1,"spell":12,"time":30},1,ids,6400);check(model.snapshot("player:local",6400).is_empty(),"death prevents stale cast pose on corpse")
    model.consume("revive",{"oid":1},1,ids,6500);model.consume("cast",{"caster":1,"spell":12,"time":30},1,ids,6600);check(model.snapshot("player:local",6600).phase=="casting","revive permits a new server confirmed cast")
    model.consume("region_changed",{},1,ids,6700);check(model.casts.is_empty(),"region lifecycle clears casting state")
    model.consume("cast",{"caster":99,"spell":12,"time":30},1,ids,6800);check(model.casts.is_empty(),"unknown caster cannot create a fake entity")
    model.consume("cast",{"caster":1,"spell":99999,"time":10},1,ids,7000);check(model.snapshot("player:local",7000).name=="Spell","missing effect definition uses English fallback")
    var report:={"passed":failures.is_empty(),"checks":n,"failures":failures,"real_server":false};var f:=FileAccess.open(get_script().resource_path.get_base_dir().path_join("../Reports/spell_casting/godot_tests.json"),FileAccess.WRITE);f.store_string(JSON.stringify(report));f.close();print(JSON.stringify(report));quit(0 if failures.is_empty() else 1)
