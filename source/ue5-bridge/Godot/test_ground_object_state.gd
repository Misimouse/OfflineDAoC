extends SceneTree
class Client extends Node:
    var calls:Array=[]
    func Target(oid:int,flags:int)->void:calls.append(["Target",oid,flags])
    func PickUp(x:int,y:int,oid:int)->void:calls.append(["PickUp",x,y,oid])
    func Interact(oid:int,x:int,y:int)->void:calls.append(["Interact",oid,x,y])
var count:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:count+=1;if not ok:failures.append(label)
func packet(oid:int,model:int,p:Vector3,name:String="Dropped item")->Dictionary:return {"oid":oid,"model":model,"x":35*8192+p.x*40,"y":51*8192+p.z*40,"z":p.y*40,"heading":0,"flags":0,"emblem":0,"door":-1,"name":name}
func enter(state:RefCounted,pos:Vector3)->void:
    var me:=packet(1,0,pos);me.region=200;state.observe("you",me)
func command(state:RefCounted,id:String,action:String)->Dictionary:return {"action":action,"entity_id":id,"object_token":state.objects.get(id,{}).get("object_token",""),"world_generation":state.generation}
func _initialize()->void:run.call_deferred()
func run()->void:
    var state=load("res://ground_object_state.gd").new();var interaction=load("res://interaction_state.gd").new();var client:=Client.new();var pos:=Vector3(100,130,100);var living:={}
    state.observe("object",packet(2,488,pos));check(state.objects.is_empty(),"object before an active player context is ignored")
    state.configure({"x":35,"y":51,"fixtures":[{"source":"world_object","pos":[110,130,100]}]});enter(state,pos)
    state.observe("object",packet(2,488,Vector3(105,130,100)));state.observe("object",packet(3,637,Vector3(101,130,100),"Test's Grave"))
    check(state.objects.size()==2 and state.nearest_loot(pos)=="object:2","nearest loot skips closer gravestone")
    var row:Dictionary=state.objects["object:2"];var token:String=row.object_token;state.observe("object",packet(2,488,Vector3(105,130,100)));check(state.objects["object:2"].object_token==token,"duplicate original create preserves current object identity")
    check(row.kind=="object" and row.realm==-1 and row.non_living and not row.nameplate.show,"objects remain non-living and outside enemy/nameplate classification")
    var select:Dictionary=command(state,"object:2","target_object");check(state.request(select,client,interaction,living,pos,true,207) and interaction.selected_id=="object:2","click selection reuses existing interaction state")
    check(client.calls==[["Target",2,0xE000]],"selection only targets and never picks up")
    client.calls.clear();var get:Dictionary=command(state,"object:2","get_object");check(state.request(get,client,interaction,living,pos,true,207),"selected current item can request pickup")
    check(client.calls==[["Target",2,0xE000],["PickUp",290720,421792,2]],"pickup pins current server target before original coordinates and object request")
    check(state.objects.has("object:2"),"pickup never removes object optimistically")
    state.observe("inventory",{});check(state.objects.has("object:2"),"inventory announcement alone cannot erase world object")
    # Execute the actual extracted original get_object/to_region functions as an independent protocol reference.
    var reference=load("res://original_ground_reference.gd").new();var player:=Node3D.new();root.add_child(player);player.position=pos
    client.calls.clear();reference.setup(client,player,2,488);reference.get_object();check(client.calls==[["PickUp",290720,421792,2]],"actual original Get Item function confirms pickup field order and coordinate conversion")
    for model in [630,631,632,633,634,635]:
        var id:="object:%d"%model;state.observe("object",packet(model,model,Vector3(110,130,100),"Relic"));check(state.objects.has(id),"relic bypasses baked-prop suppression")
        client.calls.clear();var pick:Dictionary=command(state,id,"target_object");state.request(pick,client,interaction,living,pos,true,207);client.calls.clear();check(state.request(command(state,id,"get_object"),client,interaction,living,pos,true,207) and client.calls==[["Target",model,0xE000],["Interact",model,290720,421792]],"relic uses original Interact instead of PickUp")
        client.calls.clear();reference.setup(client,player,model,model);reference.get_object();check(client.calls==[["Interact",model,290720,421792]],"actual original relic function agrees with interaction field order")
    reference.close();player.free()
    client.calls.clear();interaction.selected_id="object:3";check(state.request(command(state,"object:3","target_object"),client,interaction,living,pos,false,207),"dead player can still select a gravestone for prayer");client.calls.clear()
    check(not state.request(command(state,"object:3","get_object"),client,interaction,living,pos,false,207) and client.calls.is_empty(),"dead player cannot request pickup")
    interaction.selected_id="object:2";check(not state.request(command(state,"object:3","get_object"),client,interaction,living,pos,true,207) and client.calls.is_empty(),"pickup cannot act on a different selected object")
    check(not state.request(get,client,interaction,living,pos,true,206) and client.calls.is_empty(),"unsupported zone cannot reuse an old ground request")
    var stale:Dictionary=command(state,"object:2","get_object");state.observe("object",packet(2,488,Vector3(105,130,100),"Replacement"));check(state.objects["object:2"].object_token!=token,"reused object identity receives a fresh token")
    check(not state.request(stale,client,interaction,living,pos,true,207) and client.calls.is_empty(),"stale object token cannot pick up a replacement")
    for bad in [true,"0",1.5,NAN,INF,-1]:
        var value:Dictionary=command(state,"object:2","get_object");value.world_generation=bad;check(not state.request(value,client,interaction,living,pos,true,207) and client.calls.is_empty(),"malformed generation never issues protocol requests")
    state.observe("remove",{"oid":2,"type":9});check(not state.objects.has("object:2"),"only original deletion removes the picked object")
    state.observe("object",packet(2,488,Vector3(105,130,100)));var recreated:String=state.objects["object:2"].object_token;check(recreated!=token,"removed and recreated OID never revives an old token")
    interaction.selected_id="object:2";client.calls.clear();check(not state.request(command(state,"object:2","get_object"),client,interaction,living,pos,true,207) and client.calls.is_empty(),"fresh render token cannot pick up a reused OID without selecting it again")
    state.observe("npc",{"oid":2});check(not state.objects.has("object:2"),"living replacement clears ground identity")
    var door:=packet(4,488,pos);door.door=207000001;state.observe("object",door);check(not state.objects.has("object:4"),"doors never spawn loot bodies")
    state.observe("object",packet(4,488,Vector3(110,130,100)));check(not state.objects.has("object:4"),"source baked-world duplicate is suppressed")
    state.observe("object",packet(4,488,Vector3(112.01,130,100)));check(state.objects.has("object:4"),"object beyond original two-metre duplicate radius remains")
    for field in ["oid","model","heading","emblem","flags","x","y","z","door","name"]:
        var bad:=packet(9,488,pos);bad[field]=[];state.observe("object",bad);check(not state.objects.has("object:9"),"malformed decoded field cannot create a body")
    var masked:=packet(9,32768+488,pos);masked.heading=8192+1024;state.observe("object",masked);check(state.objects["object:9"].model_id==488 and state.objects["object:9"].heading_4096==1024,"original model flag and heading wrapping preserved")
    var old_generation:int=state.generation;state.observe("region_changed",{});check(not state.active and state.objects.is_empty() and state.generation>old_generation,"region transition clears all world identities")
    enter(state,pos);state.observe("object",packet(10,488,Vector3(137.5,130,100)));check(state.nearest_loot(pos)=="object:10","original37.5-metre loot boundary is included")
    state.observe("object",packet(10,488,Vector3(137.501,130,100)));check(state.nearest_loot(pos).is_empty(),"loot beyond original range is excluded")
    client.calls.clear();check(not state.request({"action":"target_loot","world_generation":state.generation},client,interaction,living,pos,true,207) and client.calls.is_empty(),"no loot in range cannot select a distant object")
    state.observe("object",packet(10,488,Vector3(137,130,100)));check(state.request({"action":"target_loot","world_generation":state.generation},client,interaction,living,pos,true,207) and interaction.selected_id=="object:10","nearest loot selects an actual current object")
    state.configure({"x":35,"y":51});enter(state,pos)
    for index in 150:state.observe("object",packet(index+100,488,pos+Vector3(float(index)*.1,0,0)))
    var view:Array=state.view(pos,500);check(view.size()==128 and view[0].oid==100,"render view is nearest-first and independently capped at128 objects")
    view[0].name="Changed copy";check(state.objects["object:100"].name!="Changed copy" and not view[0].has("signature"),"render snapshot is copied and omits internal identity signature")
    check(state.view(Vector3.INF).is_empty(),"invalid player position cannot publish world bodies")
    state.observe("quit",{});check(state.objects.is_empty() and not state.active,"logout clears object lifecycle")
    var report:={"passed":failures.is_empty(),"checks":count,"failures":failures,"original_get_object_executed":true,"real_server":false,"normal_runtime_modified":false};var file:=FileAccess.open(get_script().resource_path.get_base_dir().path_join("verified.json"),FileAccess.WRITE);file.store_string(JSON.stringify(report));file.close();print(JSON.stringify(report));client.free();quit(0 if failures.is_empty() else 1)
