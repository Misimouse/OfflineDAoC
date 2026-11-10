extends SceneTree
## Progression snapshots exercise the real bridge state, not server XP rules.
const Fixture=preload("res://test_classic_ui.gd")
class ProgressionServer extends Fixture.FakeServer:
    func skill_icon(kind:String,icon:int)->Array:return [icon,-1]
var checks:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func _initialize()->void:
    var model=load("res://classic_ui_state.gd").new()
    var server=ProgressionServer.new()
    var player:=Node3D.new()
    model.open_character("Private progression fixture","user://progression")
    var inv:={"ready":true,"revision":1,"items":[],"pending":false}
    server.info={"level":1,"class_name":"Naturalist"}
    server.points={"xp":49,"xp_next":50,"level_permill":980,"spec_points":0,"realm_points":0}
    server.skills=[{"page":0,"name":"Regrowth","level":1,"bonus":0},{"page":1,"name":"Sprint","level":1,"icon":409}]
    server.spell_lines=[{"name":"Regrowth","spells":[{"name":"Minor Revigoration 1","level":1,"icon":3}]}]
    model.capture_lists(server);model.sync(server,inv,100)
    check(model.data.info.level==1 and model.data.points.xp==49,"initial level and exact experience come from server")
    check(model.data.points.level_permill==980 and model.data.points.xp_next==50,"original fractional experience and next threshold preserved")
    var heal:Dictionary=model.entries["srv:spell:0:1"].duplicate(true)
    var sprint:Dictionary=model.entries["srv:skill:0"].duplicate(true)
    check(model.request({"action":"ui_assign","bar":0,"bank":0,"slot":0,"entry_id":heal.id,"entry_token":heal.token},server,player,207,true,true),"assign existing heal before level update")
    check(model.request({"action":"ui_assign","bar":0,"bank":0,"slot":1,"entry_id":sprint.id,"entry_token":sprint.token},server,player,207,true,true),"assign existing ability before level update")
    var previous:int=model.revision
    server.points={"xp":53,"xp_next":250,"level_permill":15,"spec_points":2,"realm_points":0}
    server.info.level=2;model.sync(server,inv,110)
    check(model.data.info.level==2 and model.data.points.xp==53,"level increase appears without reconnect")
    check(model.data.points.level_permill==15 and model.data.points.xp_next==250,"experience fraction resets only to server value")
    check(model.data.points.spec_points==2 and model.revision>previous,"new server training points change UI revision")
    check(model.entries.size()==2,"level packet alone cannot grant a spell")
    model.skills_loading=true;model.catalog_loading=true
    var before:int=server.calls.size()
    check(not model.request({"action":"ui_use_slot","bar":0,"slot":0},server,player,207,true,true) and server.calls.size()==before,"incomplete skill update cannot execute old shortcut")
    server.skills[0].level=2;server.skills[1].icon=411
    model.capture_lists(server);model.sync(server,inv,120)
    check(model.specs[0].level==2,"received specialization rank replaces old rank")
    check(model.bars[0][0][1].token==model.entries[sprint.id].token and model.entries[sprint.id].token!=sprint.token and model.entries[sprint.id].icon==411,"same ability refreshes shortcut identity after icon update")
    model.skills_loading=false;model.spells_loading=true;model.catalog_loading=true
    server.spell_lines[0].spells.append({"name":"New server heal","level":2,"icon":4})
    model.capture_lists(server);model.sync(server,inv,130)
    check(model.entries.has("srv:spell:0:2"),"new spell is exposed only after received list is captured")
    check(not model.request({"action":"ui_use_slot","bar":0,"slot":1},server,player,207,true,true) and server.calls.size()==before,"spell batch still blocks actions after skill batch completes")
    model.spells_loading=false;model.catalog_loading=false
    check(model.request({"action":"ui_use_slot","bar":0,"slot":0},server,player,207,true,true) and server.calls.back()==heal.id,"unchanged lower rank spell remains usable after complete refresh")
    var fresh:Dictionary=model.entries["srv:spell:0:2"].duplicate(true)
    check(model.request({"action":"ui_assign","bar":0,"bank":0,"slot":2,"entry_id":fresh.id,"entry_token":fresh.token},server,player,207,true,true),"received new rank can be assigned with its current identity")
    check(model.request({"action":"ui_use_slot","bar":0,"slot":2},server,player,207,true,true) and server.calls.back()==fresh.id,"new shortcut uses received line and level identifier")
    server.skills[1].name="Different ability";model.capture_lists(server);model.sync(server,inv,140)
    before=server.calls.size()
    check(not model.request({"action":"ui_use_slot","bar":0,"slot":1},server,player,207,true,true) and server.calls.size()==before,"replacement at old ability index cannot trigger different skill")
    check(not model.request({"action":"ui_assign","bar":0,"bank":0,"slot":3,"entry_id":sprint.id,"entry_token":sprint.token},server,player,207,true,true),"old drag token cannot assign replacement ability")
    server.spell_lines[0].spells.remove_at(1);model.capture_lists(server);model.sync(server,inv,150)
    check(not model.entries.has(fresh.id),"removed server spell disappears from catalogue")
    check(not model.request({"action":"ui_use_slot","bar":0,"slot":2},server,player,207,true,true) and server.calls.size()==before,"removed rank cannot execute retained shortcut")
    var restored=load("res://classic_ui_state.gd").new()
    restored.open_character("Private progression fixture",model.save_folder)
    restored.capture_lists(server);restored.sync(server,inv,160)
    check(restored.bars[0][0][0].id==heal.id and restored.data.info.level==2,"reopen restores shortcuts while reading current server level")
    check(restored.request({"action":"ui_use_slot","bar":0,"slot":0},server,player,207,true,true),"valid saved shortcut works with current catalogue")
    check(not restored.request({"action":"ui_use_slot","bar":0,"slot":2},server,player,207,true,true),"reopen does not resurrect removed spell")
    check(server.info.level==2 and server.points.xp==53 and server.points.spec_points==2,"UI never awards experience, level or training points")
    var report:={"passed":failures.is_empty(),"checks":checks,"failures":failures,"real_server":false,"scope":"authoritative UI snapshot and shortcut refresh"}
    print(JSON.stringify(report));server.free();player.free();quit(0 if failures.is_empty() else 1)
