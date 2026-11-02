extends SceneTree
const Base=preload("res://test_classic_ui.gd")
class Client extends Node:
    var calls:Array=[]
    func Target(oid:int,flags:int)->void:calls.append(["target",oid,flags])
    func PetCommand(aggro:int,walk:int,order:int)->void:calls.append(["pet",aggro,walk,order])
var checks:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:checks+=1;if not ok:failures.append(label)
func _initialize()->void:
    var pet=load("res://pet_state.gd").new();var server=Base.FakeServer.new();var client:=Client.new();var interaction=load("res://interaction_state.gd").new();var entities:Dictionary={};var ids:Dictionary={}
    pet.sync(server,entities,ids);check(not pet.valid and pet.entries.is_empty(),"no pet window or commands without server ownership")
    check(not pet.request({"command":"follow","pet_token":"none"},client,interaction,entities,0,true),"a world NPC cannot be commanded without owned PetWindow")
    pet.observe("pet_window",{"action":1,"oid":0});check(not pet.valid,"invalid server pet identity cannot create ownership")
    pet.observe("pet_window",{"action":2,"oid":90,"aggro":2,"walk":1,"icons":[409]});pet.sync(server,entities,ids);var token:String=pet.token
    check(pet.valid and pet.health==-1 and pet.name.is_empty(),"unloaded pet keeps health and name unknown")
    check(pet.entries.size()==7 and pet.effects.size()==1 and pet.effects[0].icon==409,"original seven commands and real effect icons are exposed")
    check(not pet.request({"command":"stay","pet_token":"old"},client,interaction,entities,100,true),"stale owned-pet identity rejected")
    check(not pet.request({"command":"stay","pet_token":token},client,interaction,entities,200,false),"dead owner cannot give orders")
    check(not pet.request({"command":"/anything","pet_token":token},client,interaction,entities,250,true),"arbitrary commands cannot enter pet protocol")
    check(pet.request({"command":"stay","pet_token":token},client,interaction,entities,300,true) and client.calls.back()==["pet",0,2,0] and pet.walk==1,"stay uses original packet without changing confirmed follow state")
    check(not pet.request({"command":"stay","pet_token":token},client,interaction,entities,350,true),"duplicate clicks are debounced")
    pet.observe("pet_window",{"action":1,"oid":90,"aggro":3,"walk":2,"icons":[409,410]});pet.sync(server,entities,ids);check(pet.token==token and pet.aggro==3 and pet.walk==2,"only server updates confirmed aggression and movement")
    check(not pet.request({"command":"attack","pet_token":token},client,interaction,entities,500,true),"attack requires a current target")
    entities={"player:local":{"health":1},"npc:90":{"name":"Spirit guardian","health":.63},"npc:2":{"id":"npc:2","health":1,"targetable":true},"npc:3":{"health":0},"npc:4":{"health":1,"targetable":false}};ids={90:"npc:90"}
    for id in ["player:local","npc:90","npc:3","npc:4"]:
        interaction.selected_id=id;check(not pet.request({"command":"attack","pet_token":token},client,interaction,entities,600,true),"pet attack rejects self own pet dead and unavailable targets")
    interaction.selected_id="npc:2";check(pet.request({"command":"attack","pet_token":token},client,interaction,entities,700,true) and client.calls[-2]==["target",2,0x6000] and client.calls[-1]==["pet",0,0,1],"attack refreshes actual selected object then sends original pet order")
    pet.sync(server,entities,ids);check(pet.name=="Spirit guardian" and pet.health==.63,"pet name and health use the actual world entity")
    check(pet.request({"command":"release","pet_token":token},client,interaction,entities,900,true) and pet.valid,"release cannot remove ownership before server closes its window")
    pet.observe("pet_window",{"action":2,"oid":91,"aggro":2,"walk":1,"icons":[]});pet.sync(server,entities,ids);check(pet.token!=token and pet.health==-1 and pet.name.is_empty() and not pet.request({"command":"follow","pet_token":token},client,interaction,entities,1100,true),"new pet cannot inherit previous identity name health or controls")
    var ui=load("res://classic_ui_state.gd").new();ui.capture_lists(server);ui.pet=pet.snapshot();ui.pet_request=func(v:Dictionary)->bool:return pet.request(v,client,interaction,entities,5000,true)
    ui.sync(server,{"items":[]},1200);var command:Dictionary=ui.entries["petcmd:stay"]
    check(ui.request({"action":"ui_assign","bar":0,"bank":0,"slot":5,"entry_id":command.id,"entry_token":command.token},server,null,207,true,true),"owned pet command can bind to a standard quickbar slot")
    check(ui.request({"action":"ui_use_slot","bar":0,"slot":5},server,null,207,true,true) and client.calls.back()==["pet",0,2,0] and server.calls.is_empty(),"quickbar dispatch reaches pet protocol rather than casting an invented skill")
    pet.observe("pet_window",{"action":0,"oid":91});pet.sync(server,entities,ids);ui.pet=pet.snapshot();ui.sync(server,{"items":[]},1300);var count:int=client.calls.size();check(not ui.request({"action":"ui_use_slot","bar":0,"slot":5},server,null,207,true,true) and client.calls.size()==count,"stored shortcut cannot command absent pet")
    pet.observe("pet_window",{"action":2,"oid":92,"aggro":2,"walk":1,"icons":[409,410]});entities["npc:92"]={"name":"Spirit guardian","health":.63};ids[92]="npc:92";pet.sync(server,entities,ids);ui.pet=pet.snapshot();ui.sync(server,{"items":[]},1400)
    check(ui.bars[0][0][5].token==ui.entries["petcmd:stay"].token and ui.bars[0][0][5].token!=command.token,"generic saved shortcut safely refreshes to newly owned pet identity")
    check(ui.request({"action":"ui_use_slot","bar":0,"slot":5},server,null,207,true,true) and client.calls.back()==["pet",0,2,0],"rebound pet shortcut works after resummoning")
    entities.erase("npc:92");pet.sync(server,entities,ids);check(pet.valid and pet.health==-1,"unloaded geometry does not fabricate pet death or full health")
    pet.observe("pet_window",{"action":2,"oid":92,"aggro":2,"walk":1,"icons":[]});pet.sync(server,entities,ids);ui.pet=pet.snapshot();ui.sync(server,{"items":[]},1450);ui.catalog_loading=true;check(ui.request({"action":"ui_use_slot","bar":0,"slot":5},server,null,207,true,true) and client.calls.back()==["pet",0,2,0],"pet control stays available while unrelated spell catalog refreshes");ui.catalog_loading=false
    pet.observe("region_changed",{});check(not pet.valid and pet.entries.is_empty() and pet.effects.is_empty(),"region lifecycle clears ownership and command catalog")
    pet.observe("pet_window",{"action":2,"oid":93,"aggro":2,"walk":1,"icons":[409,410]});entities["npc:93"]={"name":"Spirit guardian","health":.63};ids[93]="npc:93";pet.sync(server,entities,ids);pet.feedback="";server.effects={2:{"icon":11,"name":"Timed buff","negative":0,"until":10000},7:{"icon":12,"name":"Permanent debuff","negative":1,"until":0}}
    var fixture=JSON.parse_string(FileAccess.get_file_as_string(get_script().resource_path.get_base_dir().path_join("../Reports/ui_integration/fixture.json")));ui.pet=pet.snapshot();ui.character="Bridge Pet Fixture";ui.feedback="";ui.sync(server,fixture.inventory,1500);ui.bars[0][0][0]=ui.entries["srv:skill:0"].duplicate(true);fixture.pet_fixture=true;fixture.classic_ui=ui.snapshot()
    var f:=FileAccess.open(get_script().resource_path.get_base_dir().path_join("../Reports/pet/fixture.json"),FileAccess.WRITE);f.store_string(JSON.stringify(fixture));f.close()
    var report:={"passed":failures.is_empty(),"checks":checks,"failures":failures,"real_server":false,"real_pets_created":0};var out:=FileAccess.open(get_script().resource_path.get_base_dir().path_join("../Reports/pet/godot_tests.json"),FileAccess.WRITE);out.store_string(JSON.stringify(report));out.close();print(JSON.stringify(report));server.free();client.free();quit(0 if failures.is_empty() else 1)
