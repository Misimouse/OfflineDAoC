extends SceneTree
class Client extends Node:
    var calls:Array=[]
    func Target(oid:int,flags:int)->void:calls.append([oid,flags])
class Server extends Node:
    var me_oid:=1
    var group_members:Array=[{"oid":1,"name":"Group Test","class_name":"Druid","level":5},{"oid":2,"name":"Companion","class_name":"Hero","level":7},{"oid":3,"name":"Distant Companion","class_name":"Bard","level":4}]
    var commands:Array=[]
    func skill_icon(kind:String,icon:int)->Array:return [icon,-1]
    func command(text:String)->void:commands.append(text)
var count:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:count+=1;if not ok:failures.append(label)
func _initialize()->void:
    var model=load("res://party_state.gd").new();var interaction=load("res://interaction_state.gd").new();var server:=Server.new();var client:=Client.new();var entities:={"npc:2":{"id":"npc:2","kind":"npc","name":"Companion","health":1.0,"position_m":[1,0,0]},"npc:9":{"id":"npc:9","kind":"npc","name":"Training companion","health":1.0,"position_m":[2,0,0]}};var ids:={2:"npc:2"};var vitals:={"health_pct":75,"mana_pct":42,"endurance_pct":80}
    model.sync(server,ids,vitals,[],100);check(model.members.size()==3 and model.members[0].me and model.members[0].hp==75,"own group vitals use actual status")
    check(model.members[1].hp==-1 and model.members[1].power==-1,"unknown group values are not invented")
    model.observe("group_update",{"list":[{"index":1,"hp":37,"power":21,"end":80},{"index":1,"icons":[409]}]},server);model.sync(server,ids,vitals,[],200);check(model.members[1].hp==37 and model.members[1].power==21 and model.members[1].effects[0].icon==409,"group updates preserve real percentages and original effect icons")
    var token:String=model.roster_token;model.sync(server,ids,vitals,[],250);check(model.roster_token==token,"vital updates do not invalidate roster identity")
    for m in model.members:interaction.group_targets[int(m.oid)]=m
    var member:Dictionary=model.members[1];var pick:={"action":"group_target","member_oid":2,"member_token":member.token}
    check(model.request(pick,server,client,interaction,entities,300) and client.calls.back()==[2,0x6000] and interaction.selected_group_oid==2,"group row targets original server object")
    interaction.maintain(client,entities,Vector3.ZERO);check(interaction.snapshot(entities,Vector3.ZERO).target.health==.37,"target card uses actual group health")
    model.observe("group_update",{"list":[{"index":1,"hp":0,"power":0,"end":0}]},server);model.sync(server,ids,vitals,[],400)
    for m in model.members:interaction.group_targets[int(m.oid)]=m
    entities["npc:2"].health=0;interaction.maintain(client,entities,Vector3.ZERO);check(interaction.selected_id=="npc:2" and interaction.snapshot(entities,Vector3.ZERO).target.health==0,"dead group member stays targetable for resurrection")
    var distant:Dictionary=model.members[2];check(model.request({"action":"group_target","member_oid":3,"member_token":distant.token},server,client,interaction,entities,500),"logical group target can exist before its view is loaded")
    interaction.maintain(client,entities,Vector3.ZERO);check(interaction.snapshot(entities,Vector3.ZERO).target.distance_m==-1,"missing geometry never displays a fabricated distance")
    interaction.local_target={"name":"Group Test","health":.75,"level":5,"kind":"player"};check(interaction.select_self(client,1) and client.calls.back()==[1,0x6000],"self selection targets own real object rather than zero")
    interaction.maintain(client,entities,Vector3.ZERO);check(interaction.snapshot(entities,Vector3.ZERO).target.name=="Group Test" and interaction.selected_id=="player:local","self target persists with actual name and health")
    check(not interaction.select_self(client,0),"uninitialized player cannot target object zero")
    interaction.execute({"action":"target","entity_id":"npc:9"},client,entities,Vector3.ZERO)
    var before:Array=server.group_members.duplicate(true);check(model.request({"action":"group_invite","entity_id":"npc:9"},server,client,interaction,entities,600) and server.commands.back()=="/invite","invite uses original selected-target command")
    check(server.group_members==before and model.members.size()==3,"invite cannot create an optimistic group")
    check(not model.request({"action":"group_leave","group_token":token},server,client,interaction,entities,650),"pending request prevents duplicate group commands")
    model.sync(server,ids,vitals,[],4700);check(model.pending.is_empty() and model.members.size()==3,"unconfirmed invite preserves authoritative roster")
    check(not model.request({"action":"group_remove","group_token":"stale","member_oid":2,"member_token":member.token},server,client,interaction,entities,4800),"stale roster cannot remove member")
    check(model.request({"action":"group_remove","group_token":model.roster_token,"member_oid":2,"member_token":member.token},server,client,interaction,entities,4900) and server.commands.back()=="/disband Companion","remove names the chosen companion and never becomes leave-group")
    check(server.group_members==before,"removal waits for actual group packet")
    server.group_members.remove_at(1);model.sync(server,ids,vitals,[],5000);check(model.members.size()==2 and model.pending.is_empty() and model.roster_token!=token,"server group packet confirms changed roster")
    check(not model.request({"action":"group_target","member_oid":2,"member_token":member.token},server,client,interaction,entities,5100),"removed row cannot target stale member")
    var me:Dictionary=model.members[0];check(not model.request({"action":"group_remove","group_token":model.roster_token,"member_oid":1,"member_token":me.token},server,client,interaction,entities,5200),"own removal must use explicit leave action")
    check(model.request({"action":"group_leave","group_token":model.roster_token},server,client,interaction,entities,5300) and server.commands.back()=="/disband","leave is an explicit original server command")
    check(model.members.size()==2,"leave cannot clear the local group before confirmation")
    server.group_members=[];model.sync(server,ids,vitals,[],5400);check(model.members.is_empty() and model.pending.is_empty(),"only server empty roster closes group")
    for bad in [true,"1",1.5,NAN,INF,-1,0,65536]:check(not model.request({"action":"group_target","member_oid":bad,"member_token":me.token},server,client,interaction,entities,5500),"malformed member identity rejected")
    server.group_members=[{"oid":1,"name":"Group Test","class_name":"Druid","level":5},{"oid":2,"name":"Companion","class_name":"Hero","level":7},{"oid":3,"name":"Distant Companion","class_name":"Bard","level":4}];model.sync(server,ids,vitals,[],6000);model.observe("group_update",{"list":[{"index":1,"hp":37,"power":21,"end":80},{"index":1,"icons":[409]}]},server);model.sync(server,ids,vitals,[],6100)
    server.group_members[1].name="Replacement";model.sync(server,ids,vitals,[],6200);check(model.members[1].hp==-1 and model.members[1].effects.is_empty(),"reused object identity cannot inherit previous member health or buffs")
    model.observe("group_update",{"list":[{"index":1,"hp":66,"power":40,"end":70}]},server);model.sync(server,ids,vitals,[],6300);check(model.members[1].hp==66,"new identity receives only its own server updates")
    server.group_members[1].name="Companion";model.observe("group_update",{"list":[{"index":1,"hp":37,"power":21,"end":80},{"index":1,"icons":[409]}]},server);model.sync(server,ids,vitals,[],6400)
    model.feedback=""
    check_join_packet_order()
    var fixture=JSON.parse_string(FileAccess.get_file_as_string(get_script().resource_path.get_base_dir().path_join("../Reports/ui_integration/fixture.json")));fixture.party_fixture=true;fixture.classic_ui.character="Bridge Group Fixture";fixture.classic_ui.group=model.members;fixture.classic_ui.party=model.snapshot();fixture.classic_ui.group_selected_oid=2
    var f:=FileAccess.open(get_script().resource_path.get_base_dir().path_join("../Reports/group/fixture.json"),FileAccess.WRITE);f.store_string(JSON.stringify(fixture));f.close()
    var report:={"passed":failures.is_empty(),"checks":count,"failures":failures,"real_server":false,"human_invites_sent":0};var out:=FileAccess.open(get_script().resource_path.get_base_dir().path_join("../Reports/group/godot_tests.json"),FileAccess.WRITE);out.store_string(JSON.stringify(report));out.close();print(JSON.stringify(report));server.free();client.free();quit(0 if failures.is_empty() else 1)

func check_join_packet_order()->void:
    var server:=Server.new();server.group_members=[]
    var model=load(get_script().resource_path.get_base_dir().path_join("party_state.gd")).new()
    var a:={"oid":1,"name":"A","class_name":"Druid","level":50}
    var b:={"oid":2,"name":"B","class_name":"Naturalist","level":1}
    model.observe("group_update",{"list":[{"index":1,"hp":37,"power":42,"end":83},{"index":1,"icons":[409]}]},server,100)
    check(model.metrics.is_empty(),"pre-roster values never invent group membership")
    server.group_members=[a,b];model.observe("group",{},server,101);model.sync(server,{}, {},[],102)
    check(model.members[1].hp==37 and model.members[1].power==42 and model.members[1].end==83,"initial status before roster retains authoritative vitals")
    check(model.members[1].effects.size()==1 and model.members[1].effects[0].icon==409,"initial icon packet before roster survives alongside vitals")
    model.reset();server.group_members=[a];model.observe("group",{},server,200)
    model.observe("group_update",{"list":[{"index":1,"hp":61}]},server,201)
    server.group_members=[a,b];model.observe("group",{},server,202);model.sync(server,{}, {},[],203)
    check(model.members[1].hp==61,"leader receives appended companion status before expanded roster")
    model.reset();server.group_members=[];model.observe("group_update",{"list":[{"index":1,"hp":61}]},server,300)
    server.group_members=[a,b];model.observe("group",{},server,1401);model.sync(server,{}, {},[],1402)
    check(model.members[1].hp==-1,"expired pre-roster status cannot attach to later member")
    model.reset();server.group_members=[a];model.observe("group",{},server,1500)
    model.observe("group_update",{"list":[{"index":1,"hp":61}]},server,1501)
    server.group_members=[b,a];model.observe("group",{},server,1502);model.sync(server,{}, {},[],1503)
    check(model.members[1].hp==-1 and model.deferred_updates.is_empty(),"changed roster prefix rejects ambiguous pending indices")
    model.observe("group_update",{"list":[{"index":2,"hp":61},{"index":-1,"hp":77},{"index":8,"hp":88}]},server,1600)
    check(model.deferred_updates.size()==1,"only eight original group positions may be staged")
    model.reset();check(model.deferred_updates.is_empty() and model.observed_roster.is_empty(),"zone or session reset clears unbound group packets")
    server.free()
