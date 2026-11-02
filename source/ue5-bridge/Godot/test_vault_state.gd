extends SceneTree
class Client extends Node:
    var calls:Array=[]
    func MoveItem(a:int,b:int,count:int)->void:calls.append([a,b,count])
var failures:Array=[]
var checks:=0
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func _initialize()->void:run.call_deferred()
func run()->void:
    var folder:String=get_script().resource_path.get_base_dir()
    var vault=load(folder.path_join("vault_state.gd")).new()
    var interaction=load(folder.path_join("interaction_state.gd")).new()
    var client:=Client.new()
    var entities:={"npc:9":{"id":"npc:9","name":"QA Keeper","health":1,"position_m":[0,0,0]}}
    var rows:Array=[{"slot":40,"name":"Club","count":1,"item_type":10,"object_type":1,"model":1,"icon":0},{"slot":110,"name":"Stored","count":2,"item_type":10,"object_type":1,"model":1,"icon":0},{"slot":150,"name":"Account","count":1,"item_type":10,"object_type":1,"model":1,"icon":0}]
    var inv=load(folder.path_join("inventory_state.gd")).new()
    inv.observe("inventory");inv.sync(rows,{}, {},"standard",1,20,100,vault.snapshot())
    check(inv.items.size()==1 and not vault.valid,"cached vault slots stay hidden before a genuine open")
    vault.observe("inventory",{"window":3},interaction,entities,Vector3.ZERO)
    check(not vault.valid,"unsolicited container packet without a keeper cannot open")
    interaction.selected_id="npc:9";interaction.conversation_id="npc:9"
    vault.observe("inventory",{"window":3},interaction,entities,Vector3.ZERO)
    check(vault.valid and vault.first==110 and vault.count==40,"personal vault opens exact original forty slots")
    var token:String=vault.token
    inv.sync(rows,{}, {},"standard",1,20,110,vault.snapshot())
    check(inv.items.has(110) and not inv.items.has(150),"personal vault excludes account and consignment slots")
    var command:={"action":"inventory_move","slot":110,"to_slot":41,"item_token":inv.items[110].token,"inventory_revision":inv.state_revision,"vault_token":token}
    var before:Dictionary=inv.items.duplicate(true)
    check(inv.execute(command,client,interaction,entities,Vector3.ZERO,120) and client.calls.back()==[110,41,2],"withdrawal sends whole original stack through MoveItem")
    check(inv.items==before and not inv.pending.is_empty(),"withdrawal waits for authoritative inventory update")
    check(not inv.execute(command,client,interaction,entities,Vector3.ZERO,121),"one inventory lock prevents duplicate withdrawal")
    inv.reset();inv.observe("inventory");inv.sync(rows,{}, {},"standard",1,20,130,vault.snapshot())
    command.inventory_revision=inv.state_revision;command.item_token=inv.items[110].token;command.vault_token="old"
    check(not inv.execute(command,client,interaction,entities,Vector3.ZERO,140),"stale container token cannot move stored items")
    command.vault_token=token;command.to_slot=10
    check(not inv.execute(command,client,interaction,entities,Vector3.ZERO,150),"vault equipment shortcut must go through backpack")
    command.to_slot=150
    check(not inv.execute(command,client,interaction,entities,Vector3.ZERO,160),"personal and account vault ranges cannot cross")
    command.to_slot=120
    check(inv.execute(command,client,interaction,entities,Vector3.ZERO,170) and client.calls.back()==[110,120,2],"reordering within current vault uses actual slot numbers")
    check(not vault.close({"vault_token":"old"}) and vault.valid,"stale close cannot affect another opened vault")
    check(vault.close({"vault_token":token}) and not vault.valid,"explicit close invalidates the container")
    inv.sync(rows,{}, {},"standard",1,20,180,vault.snapshot())
    check(not inv.items.has(110),"closing hides stale bank inventory while original cache remains")
    vault.observe("inventory",{"window":4},interaction,entities,Vector3.ZERO)
    check(vault.valid and vault.first==150 and vault.count==100 and vault.token!=token,"account vault opens one hundred original client slots with new identity")
    token=vault.token;inv.reset();inv.observe("inventory");inv.sync(rows,{}, {},"standard",1,20,190,vault.snapshot())
    command={"action":"inventory_move","slot":40,"to_slot":249,"item_token":inv.items[40].token,"inventory_revision":inv.state_revision,"vault_token":token}
    check(inv.execute(command,client,interaction,entities,Vector3.ZERO,200) and client.calls.back()==[40,249,1],"deposit supports the final account slot")
    vault.observe("inventory",{"window":4},interaction,entities,Vector3.ZERO)
    check(vault.token!=token,"switching account server pages invalidates previous operations")
    vault.observe("inventory",{"window":5},interaction,entities,Vector3.ZERO)
    check(not vault.valid,"consignment chest packet never inherits account-vault permissions")
    vault.observe("inventory",{"window":3},interaction,entities,Vector3.ZERO);vault.maintain(interaction,entities,Vector3(7,0,0),true)
    check(not vault.valid,"leaving keeper range closes storage")
    vault.observe("inventory",{"window":3},interaction,entities,Vector3.ZERO);interaction.conversation_id="npc:10";vault.maintain(interaction,entities,Vector3.ZERO,true)
    check(not vault.valid,"switching service closes the old container")
    interaction.conversation_id="npc:9";vault.observe("inventory",{"window":3},interaction,entities,Vector3.ZERO);vault.maintain(interaction,entities,Vector3.ZERO,false)
    check(not vault.valid,"death invalidates storage access")
    vault.observe("inventory",{"window":3},interaction,entities,Vector3.ZERO);vault.observe("region_changed",{},interaction,entities,Vector3.ZERO)
    check(not vault.valid and vault.token=="","region change removes container identity")
    vault.observe("inventory",{"window":3},interaction,entities,Vector3.ZERO);vault.observe("remove",{"oid":9,"type":1},interaction,entities,Vector3.ZERO)
    check(not vault.valid,"keeper removal invalidates storage before an object id can be reused")
    var ui=load(folder.path_join("classic_ui_state.gd")).new();var stored:Dictionary=ui.entry("srv:110","Stored","item",0,-1,0,"","stored-token");stored.stored=true;ui.entries[stored.id]=stored
    var server:=Node.new();var player:=Node3D.new()
    check(not ui.request({"action":"ui_assign","bar":0,"bank":0,"slot":0,"entry_id":stored.id,"entry_token":stored.token},server,player,207,true,true),"stored items cannot be assigned to usable quickbars")
    ui.bars[0][0][0]=stored
    check(not ui.request({"action":"ui_use_slot","bar":0,"slot":0},server,player,207,true,true),"old quickbar access cannot use an item inside storage")
    var report:={"passed":failures.is_empty(),"checks":checks,"failures":failures,"real_server":false}
    var out:=FileAccess.open(folder.path_join("../Reports/vault/godot_tests.json"),FileAccess.WRITE);out.store_string(JSON.stringify(report));out.close();print(JSON.stringify(report));client.free();server.free();player.free();quit(0 if failures.is_empty() else 1)
