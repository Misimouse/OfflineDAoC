from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
from pathlib import Path
R=Path(str(ROOT))
s='''extends SceneTree
class FakeServer extends Node:
    var skills:Array=[{"page":0,"name":"Blades","level":2,"bonus":1},{"page":1,"name":"Sprint","icon":409,"level":1},{"page":2,"name":"Style","icon":1,"level":2},{"page":3,"name":"Hybrid spell","icon":2,"level":1,"special":0}]
    var spell_lines:Array=[{"name":"Magic line","spells":[{"name":"Heal","level":1,"icon":3}]}]
    var info:Dictionary={"level":5,"class_name":"Test class","race_name":"Celt","base_class":"Guardian","profession":"Hero","title":"","realm_spec_points":2}
    var points:Dictionary={"spec_points":3,"realm_points":10,"xp":1200}
    var stats:Array=[60,61,62,63,64,65,66,67]
    var stat_buffs:Array=[0,-1,2,0,0,0,0,0]
    var resists:Array=[1,2,3,4,5,6,7,8,9]
    var con_lost:=1
    var weapon_stats:Dictionary={"weapon_skill":12,"weapon_damage":2.3,"armor_factor":10}
    var group_members:Array=[]
    var calls:Array=[]
    var cooldown:=0.0
    func skill_icon(kind:String,icon:int)->Array:return [409,-1]
    func reuse_left(id:String)->float:return cooldown
    func use_entry(id:String,player:Node3D,zone:int,visible:bool)->bool:calls.append(id);return true
var checks:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func _initialize()->void:
    var model=load("res://classic_ui_state.gd").new();var server:=FakeServer.new();var player:=Node3D.new();model.open_character("Bridge UI Test",get_script().resource_path.get_base_dir().path_join("../Reports/ui_integration/test_save"));model.capture_lists(server)
    var inv:={"ready":true,"revision":1,"state_revision":1,"items":[{"slot":10,"name":"Training sword","icon":1,"count":1,"token":"test-item","item_type":10}],"money":{"copper":3},"weight_now":2,"weight_max":70,"pending":false}
    model.sync(server,inv,100)
    check(model.bars.size()==3 and model.bars[2].size()==10 and model.bars[2][9].size()==10,"three bars, ten pages, ten slots")
    check(model.specs.size()==1 and model.entries.size()==5,"original server skill offsets and spell lines assembled")
    check(model.entries["srv:skill:0"].name=="Sprint" and model.entries["srv:skill:1"].kind=="style","specs do not offset use-skill index")
    check(model.entries["srv:spell:0:1"].name=="Heal","spell identifiers preserve line and level")
    check(model.entries["srv:skill:2"].line=="Blades","hybrid spell grouped by actual specialization")
    var e:Dictionary=model.entries["srv:skill:0"];var v:={"action":"ui_assign","bar":0,"bank":0,"slot":0,"entry_id":e.id,"entry_token":e.token}
    check(model.request(v,server,player,207,true,true),"assign known server entry")
    check(server.calls.is_empty(),"assignment cannot execute an ability")
    var bad:Dictionary=v.duplicate();bad.entry_token="stale";check(not model.request(bad,server,player,207,true,true),"stale catalog cannot replace shortcut")
    var use:={"action":"ui_use_slot","bar":0,"slot":0};check(model.request(use,server,player,207,true,true) and server.calls==["srv:skill:0"],"quickbar executes original server identifier")
    var count:int=server.calls.size();check(not model.request(use,server,player,207,true,false) and server.calls.size()==count,"dead cannot execute bar")
    check(not model.request(use,server,player,202,true,true),"outside-region action blocked")
    server.cooldown=2;check(not model.request(use,server,player,207,true,true),"server cooldown blocks repeat")
    server.cooldown=0;model.catalog_loading=true;check(not model.request(use,server,player,207,true,true),"partial server lists cannot execute stale index");model.catalog_loading=false
    var move:Dictionary=v.duplicate();move.bar=2;move.bank=9;move.slot=9;move.from_bar=0;move.from_bank=0;move.from_slot=0
    check(model.request(move,server,player,207,true,true) and model.bars[0][0][0].is_empty() and model.bars[2][9][9].id==e.id,"drag moves shortcut atomically between bars/pages")
    check(model.request({"action":"ui_bank","bar":2,"bank":9},server,player,207,true,true),"page change accepted")
    var restored=load("res://classic_ui_state.gd").new();restored.open_character("Bridge UI Test",model.save_folder);check(restored.banks[2]==9 and restored.bars[2][9][9].id==e.id,"shortcuts and pages persist per character")
    var original:Dictionary=server.info.duplicate(true);server.skills[1].name="Different skill";model.capture_lists(server);model.sync(server,inv,200)
    check(not model.request({"action":"ui_use_slot","bar":2,"slot":9},server,player,207,true,true),"reordered or renamed server entry cannot activate wrong ability")
    check(server.info==original and inv.items.size()==1,"UI does not change character points or inventory")
    var snapshot:Dictionary=model.snapshot();snapshot.character="Bridge UI Test";var f:=FileAccess.open(get_script().resource_path.get_base_dir().path_join("../Reports/ui_integration/fixture.json"),FileAccess.WRITE);f.store_string(JSON.stringify({"classic_ui":snapshot,"inventory":inv,"player_status":{"ready":true,"revision":1,"generation":1,"vitals":{"health_pct":100,"max_health":58,"mana_pct":0,"endurance_pct":100},"gm_mode":{"ready":true,"combat_test":false}}}));f.close()
    var report:={"passed":failures.is_empty(),"checks":checks,"failures":failures,"real_server":false};var out:=FileAccess.open(get_script().resource_path.get_base_dir().path_join("../Reports/ui_integration/godot_tests.json"),FileAccess.WRITE);out.store_string(JSON.stringify(report));out.close();print(JSON.stringify(report));server.free();player.free();quit(0 if failures.is_empty() else 1)
'''
(R/'Godot/test_classic_ui.gd').write_text(s,encoding='utf-8')
s=(R/'verify_chat_death_godot.py').read_text(encoding='utf-8-sig').replace("D=R/'Reports/chat_death_fix'","D=R/'Reports/ui_integration'").replace('test_chat_death_fix.gd','test_classic_ui.gd');(R/'verify_classic_ui_godot.py').write_text(s,encoding='utf-8')
for base in ['UnrealPlugin/DAoCVisualBridge','GMCombatTest/NativeHost/Plugins/DAoCVisualBridge']:
 p=R/base/'Source/DAoCVisualBridge/Private/DAoCBridgeClassicUI.cpp';s=p.read_text(encoding='utf-8').replace('FString Id,Token;int32 Bar=','void SetLabel(const FText& Text){DefaultHoverText=Text;}\n    FString Id,Token;int32 Bar=').replace('D->DefaultHoverText=FText::FromString(CS(Entry,TEXT("name")))','D->SetLabel(FText::FromString(CS(Entry,TEXT("name"))))').replace('return B.Get();','return &B.Get();').replace('B->ImageSize={108,156}','B->ImageSize=FVector2D(108,156)').replace('ClassicDollBrush=B.Get()','ClassicDollBrush=&B.Get()');p.write_text(s,encoding='utf-8')
