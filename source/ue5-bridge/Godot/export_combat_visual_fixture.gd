extends SceneTree
func _initialize()->void:
    var base:String=get_script().resource_path.get_base_dir().path_join("..")
    var source:="C:/Gogot/Download-OfflineDAoC-v0.37c/playable-v0.37c-classic/new-client/godot/content"
    var m=load("res://combat_visual_state.gd").new()
    m.configure(JSON.parse_string(FileAccess.get_file_as_string(base.path_join("models.json"))),JSON.parse_string(FileAccess.get_file_as_string(source+"/weapons/weapons.json")).models,JSON.parse_string(FileAccess.get_file_as_string(source+"/rules/style_anims.json")),JSON.parse_string(FileAccess.get_file_as_string(source+"/characters/style_clips.json")))
    var entities:Dictionary={"player:local":{"model_id":0,"health":1.0,"state":"idle"},"npc:2":{"model_id":123,"health":1.0,"state":"idle"}}
    var ids:Dictionary={2:"npc:2"};var p:Dictionary={"attacker":1,"defender":2,"weapon":445,"style":0,"result":10,"health":50};var result:Dictionary={}
    seed(7);m.consume(p,1,ids,entities,1000);result.local_attack=m.snapshot("player:local",1100)
    m.reset();seed(7);m.consume(p,1,ids,entities,2000);result.second_attack=m.snapshot("player:local",2100)
    m.reset();p.defender=1;seed(7);m.consume(p,1,ids,entities,3000);result.attack_then_flinch=m.snapshot("player:local",3100)
    m.reset();p.defender=2;seed(7);m.consume(p,1,ids,entities,4000);result.death_attack=m.snapshot("player:local",4000)
    m.reset();seed(7);m.consume(p,1,ids,entities,5000);result.stale_attack=m.snapshot("player:local",9000)
    m.reset();p.attacker=2;p.defender=1;seed(7);m.consume(p,1,ids,entities,10000);result.npc_attack=m.snapshot("npc:2",10100);result.local_flinch=m.snapshot("player:local",10100)
    var file:=FileAccess.open(base.path_join("Reports/combat_visual/fixture.json"),FileAccess.WRITE);file.store_string(JSON.stringify(result,"  "));file.close();print("COMBAT_VISUAL_FIXTURE_PASS");quit()
