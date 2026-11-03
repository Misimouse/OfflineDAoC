extends Node
## Real headless session using the unchanged Server autoload and its normal login/logout.
var transport:Node
var adapter:Node
var interaction:RefCounted
var inventory:RefCounted
var character_lobby:RefCounted
var local_model_id:=0
var vault:RefCounted
var exchange:RefCounted
var player_state:RefCounted
var combat_visual:RefCounted
var gm_mode:RefCounted
var release_state:RefCounted
var concentration:RefCounted
var pet:RefCounted
var trainer:RefCounted
var journal:RefCounted
var party:RefCounted
var line_of_sight:RefCounted
var spell_visuals:RefCounted
var spell_cast:RefCounted
var classic_ui:RefCounted
var ui_pose:Node3D
var zone_lights:Array=[]
var last_ui_sync:=0
var last_move_speed:=0.0
var target_sight_id:=""
var target_sight:=false
var target_sight_at:=0
var attack_visibility_syncs:=0
var last_attack_visibility:Dictionary={}
var last_inventory_sync:=0
var server:Node
var item_db:Script
var weapon_models:Script
var position:=Vector3.ZERO
var heading:=0
var entered:=false
var ever_played:=false
var leaving:=false
var connected_once:=false
var last_peer:=0
var last_publish:=0
var last_report:=0
var last_position_send:=0
var began:=0
var character_name:=""
var status:="Connecting to server"
var chat_lines:Array=[]
var chat_state:RefCounted
var message_count:=0
var home_jump_requested:=false
var test_return_attempts:=0
var test_return_at:=-10000
var folder:=""
var move_commands:=0
var move_rejected:=0
var initial_spawn:=Vector3(1352,132,1244.2)
var allowed_doors:Dictionary={}
var door_states:Dictionary={}
var door_requests:=0
var door_events:=0
var peak_move_speed:=0.0
var entry_revision:=0

func _ready()->void:
    folder=get_script().resource_path.get_base_dir()
    chat_state=load(folder.path_join("chat_state.gd")).new()
    var zone_info=JSON.parse_string(FileAccess.get_file_as_string("res://content/zones/zone207/zone.json"))
    if zone_info is Dictionary:zone_lights=zone_info.get("lights",[])
    var config=JSON.parse_string(FileAccess.get_file_as_string(folder.path_join("../bridge_config.json")))
    if config is Dictionary:
        var point=config.get("initial_spawn_m",[])
        if point is Array and point.size()==3:initial_spawn=Vector3(float(point[0]),float(point[1]),float(point[2]))
    if "--bridge-door-test" in OS.get_cmdline_user_args():initial_spawn=Vector3(1376,130,1270.9)
    if "--bridge-shack-door-test" in OS.get_cmdline_user_args():initial_spawn=Vector3(1375.4,130,1250.6)
    interaction=load(folder.path_join("interaction_state.gd")).new()
    inventory=load(folder.path_join("inventory_state.gd")).new()
    vault=load(folder.path_join("vault_state.gd")).new()
    exchange=load(folder.path_join("exchange_state.gd")).new()
    player_state=load(folder.path_join("player_combat_state.gd")).new()
    combat_visual=load(folder.path_join("combat_visual_state.gd")).new()
    gm_mode=load(folder.path_join("gm_test_mode.gd")).new()
    release_state=load(folder.path_join("player_release.gd")).new()
    concentration=load(folder.path_join("concentration_state.gd")).new()
    pet=load(folder.path_join("pet_state.gd")).new()
    trainer=load(folder.path_join("trainer_state.gd")).new()
    journal=load(folder.path_join("journal_state.gd")).new()
    party=load(folder.path_join("party_state.gd")).new()
    line_of_sight=load(folder.path_join("line_of_sight.gd")).new()
    spell_visuals=load(folder.path_join("spell_visual_state.gd")).new()
    spell_cast=load(folder.path_join("spell_cast_state.gd")).new()
    spell_cast.configure(JSON.parse_string(FileAccess.get_file_as_string("res://content/spells/spell_fx.json")))
    classic_ui=load(folder.path_join("classic_ui_state.gd")).new()
    classic_ui.macro_request=func(line:String)->bool:return dispatch_chat(line)
    classic_ui.pet_request=func(value:Dictionary)->bool:return pet.request(value,server.client,interaction,adapter.entities,Time.get_ticks_msec(),player_state.ready and int(player_state.vitals.get("health_pct",0))>0)
    ui_pose=load(folder.path_join("ui_player_pose.gd")).new();add_child(ui_pose)
    combat_visual.configure(JSON.parse_string(FileAccess.get_file_as_string(folder.path_join("../models.json"))),JSON.parse_string(FileAccess.get_file_as_string("res://content/weapons/weapons.json")).models,JSON.parse_string(FileAccess.get_file_as_string("res://content/rules/style_anims.json")),JSON.parse_string(FileAccess.get_file_as_string("res://content/characters/style_clips.json")))
    server=get_node("/root/Server");server.no_world=true
    interaction.icon_for_model=Callable(server,"item_icon")
    character_lobby=load(folder.path_join("character_lobby.gd")).new()
    character_lobby.enabled="--bridge-character-menu" in OS.get_cmdline_user_args()
    character_lobby.enter_requested.connect(enter_character)
    server.created.connect(func(ok,why):character_lobby.refresh(server);character_lobby.creation_result(ok,why))
    server.name_checked.connect(func(name,result):character_lobby.name_result(name,result,server,Time.get_ticks_msec()))
    item_db=load("res://game/ui/item_db.gd");assert(item_db!=null)
    exchange.item_lookup=func(id:String)->Dictionary:return item_db.item(id)
    server.exchange_open.connect(func(which):exchange.open(which,server,interaction,adapter.entities,position,player_state.ready and int(player_state.vitals.get("health_pct",0))>0,Time.get_ticks_msec()))
    server.exchange_changed.connect(func():exchange.sync(server,inventory,Time.get_ticks_msec()))
    var collisions=JSON.parse_string(FileAccess.get_file_as_string(folder.path_join("../collision_catalog.json")))
    if collisions is Dictionary:
        for model in collisions.get("models",{}).values():
            for fixture in model.get("door_fixtures",[]):
                for id in fixture.get("groups",{}).values():allowed_doors[int(id)]=fixture.get("position_m",[])
    transport=load(folder.path_join("visual_bridge.gd")).new();add_child(transport)
    transport.gameplay_enabled=true;assert(transport.start()==OK)
    adapter=load(folder.path_join("decoded_world_adapter.gd")).new();add_child(adapter);adapter.set_process(false)
    adapter.missing_entity.connect(func(oid):
        if server.playing and not leaving and server.client.has_method("RequestObject"):server.client.call("RequestObject",oid))
    var plate_data=JSON.parse_string(FileAccess.get_file_as_string("res://content/zones/zone207/npcs.json"))
    if plate_data is Dictionary:adapter.con_table=plate_data.get("con",[])
    adapter.record_motion="--bridge-motion-record" in OS.get_cmdline_user_args()
    adapter.bridge=transport;adapter.zone_info={"x":35,"y":51};adapter.source_label="live-offlinedaoc"
    server.skills_changed.connect(func():classic_ui.capture_lists(server))
    server.characters_ready.connect(characters_ready)
    server.world.connect(world_event)
    server.jumped.connect(func(entry):apply_entry(entry))
    server.login_failed.connect(func(_why):status="Login error. Check the normal launcher";write_report())
    server.disconnected.connect(func(_why):status="Disconnected";write_report();get_tree().quit())
    transport.command_received.connect(command)
    began=Time.get_ticks_msec()
    server.start.call_deferred()

func characters_ready(realm:String)->void:
    if realm!="hib" or entered:return
    character_lobby.refresh(server)
    if character_lobby.enabled:return
    if server.character_list_pending():return
    var list:Array=server.characters_in("hib")
    if list.is_empty():status="No Hibernia characters available";write_report();return
    var chosen:Dictionary=list[0]
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--bridge-character="):
            var desired:=arg.trim_prefix("--bridge-character=")
            for c in list:
                if String(c.name).nocasecmp_to(desired)==0:chosen=c;break
    enter_character(chosen)

func enter_character(chosen:Dictionary)->void:
    if entered or server.playing:return
    var task_file:String=folder.path_join("../SourceModels/tasks.json")
    if FileAccess.file_exists(task_file):
        var tasks=JSON.parse_string(FileAccess.get_file_as_string(task_file))
        if tasks is Array:
            for task in tasks:
                if String(task.get("info",{}).get("race",""))==String(chosen.get("prefix","")):local_model_id=int(task.id);break
    adapter.player_level=int(chosen.get("level",1));adapter.player_realm=3
    entered=true;character_name=chosen.name
    var legacy:String=server.quickbars_path(character_name)
    if not FileAccess.file_exists(legacy) and character_name.is_valid_filename():
        legacy=ProjectSettings.globalize_path("res://../save/Godot/app_userdata/MMOEngine/server_quickbars/"+character_name.to_lower()+".json").simplify_path()
    classic_ui.open_character(character_name,folder.path_join("../Client/Saved/ClassicUI"),legacy)
    status="Entering with "+character_name
    server.enter_world(chosen)

func apply_entry(entry:Dictionary)->void:
    entry_revision+=1
    if int(entry.get("zone",-1))!=207 and adapter!=null:adapter.clear_world()
    if int(entry.get("zone",-1))==207:
        var point=entry.get("pos",Vector3.ZERO)
        position=point if point is Vector3 else Vector3(point[0],point[1],point[2])
        heading=server.heading_of(float(entry.get("face",180)))
        status="Connected to Connacht"

func world_event(kind:String,data:Dictionary)->void:
    exchange.observe(kind,data)
    if kind in ["you","region_changed","quit"]:line_of_sight.reset()
    if kind=="los":
        var positions:Dictionary={};positions[int(server.me_oid)]={"id":"player:local","pos":position}
        if int(server.entry.get("zone",-1))==207:
            for row in adapter.entities.values():
                var p:Array=row.get("position_m",[])
                if p.size()==3 and String(row.id)!="player:local":positions[int(String(row.id).get_slice(":",1))]={"id":row.id,"pos":Vector3(p[0],p[1],p[2])}
        else:positions.clear()
        line_of_sight.request(data,server.client,positions,Time.get_ticks_msec())
    spell_cast.consume(kind,data,int(server.me_oid),adapter.oid_to_id,Time.get_ticks_msec())
    spell_visuals.consume(kind,data,int(server.me_oid),adapter.oid_to_id,Time.get_ticks_msec())
    concentration.observe(kind)
    pet.observe(kind,data)
    trainer.observe(kind,data,server)
    party.observe(kind,data,server)
    if not journal.observe(kind,data):classic_ui.observe(kind,data,server)
    if kind=="skills":classic_ui.skills_loading=bool(data.get("more",false))
    if kind=="spell_line":classic_ui.spells_loading=not bool(data.get("done",false))
    classic_ui.catalog_loading=classic_ui.skills_loading or classic_ui.spells_loading
    var changed_oid:=int(data.get("oid",-1))
    var changed_id:String="player:local" if changed_oid==int(server.me_oid) else String(adapter.oid_to_id.get(changed_oid,""))
    if kind in ["you","region_changed","quit"]:combat_visual.reset()
    elif kind in ["death","revive","model_change"] or (kind=="remove" and int(data.get("type",1))!=9):combat_visual.remove(changed_id)
    var gm_revision:int=gm_mode.revision
    gm_mode.consume(kind,data)
    if kind=="you" or (kind=="revive" and changed_oid==int(server.me_oid)):gm_mode.request("protected",server.client,Time.get_ticks_msec())
    if gm_mode.revision!=gm_revision:player_state.revision+=1
    if kind=="door_state":
        var id:=int(data.get("door_id",-1))
        if allowed_doors.has(id):door_states[id]=bool(data.get("open",false));door_events+=1
    if kind=="you":
        apply_entry(server.entry)
        var door_trial:bool="--bridge-door-test" in OS.get_cmdline_user_args() or "--bridge-shack-door-test" in OS.get_cmdline_user_args()
        if int(server.entry.get("zone",-1))==207 and not home_jump_requested and (door_trial or Vector2(position.x-initial_spawn.x,position.z-initial_spawn.z).length()>20):
            home_jump_requested=true
            # Server-authorized GM teleport; never edits a save or changes a database directly.
            server.command("/jump to %d %d %d 200" % [roundi(initial_spawn.x*40)+35*8192,roundi(initial_spawn.z*40)+51*8192,roundi(initial_spawn.y*40)])
            status="Requesting GM transfer to the Ardee test location"
        else:
            server.command("/gmstealth on")
    if kind=="jump":apply_entry(server.entry)
    var routed:bool=chat_state.observe(kind,data,adapter.entities,interaction.conversation_id,position,Time.get_ticks_msec()) if chat_state!=null else false
    if kind=="message":
        message_count+=1;var text:=String(data.get("text",""))
        if not routed:
            chat_lines.append(text.left(240));if chat_lines.size()>8:chat_lines.pop_front()
    if kind in ["you","region_changed","quit"]:interaction.reset();inventory.reset()
    vault.observe(kind,data,interaction,adapter.entities,position)
    inventory.observe(kind)
    player_state.consume(kind,data,int(server.me_oid),Time.get_ticks_msec())
    var release_revision:int=release_state.revision
    release_state.consume(kind,data,int(server.me_oid))
    if release_state.revision!=release_revision:player_state.revision+=1
    player_state.observe_target_death(kind,data,interaction.selected_id,adapter.oid_to_id,adapter.entities,server.client,Time.get_ticks_msec())
    if kind in ["you","region_changed","quit"]:target_sight_id="";target_sight=false;target_sight_at=0
    interaction.consume(kind,data,adapter.entities,Engine.get_process_frames())
    if kind=="quit":status="Session saved";write_report();return
    if kind in ["you","npc","player","move","remove","region_changed","quit","model_change","death","revive","object","combat","equipment"]:adapter.consume_world(kind,data)
    # Publish the opened container and its inventory revision together. The original
    # Server emits exchange_open before forwarding this inventory world event.
    if kind in ["inventory","market"]:sync_inventory(Time.get_ticks_msec())
    if kind=="combat" and int(server.entry.get("zone",-1))==207:
        var now:=Time.get_ticks_msec();sync_inventory(now)
        combat_visual.consume(data,int(server.me_oid),adapter.oid_to_id,adapter.entities,now,local_weapon_stance(),not player_state.ready or int(player_state.vitals.get("health_pct",0))<=0)

func command(value:Dictionary)->void:
    var action:=String(value.get("action",""))
    if action=="logout":request_logout();return
    if action in ["character_enter","character_create","character_refresh"]:
        character_lobby.execute(value,server,Time.get_ticks_msec());return
    if not server.playing or leaving:return
    if action in exchange.ACTIONS:
        var now:=Time.get_ticks_msec()
        sync_inventory(now);exchange.sync(server,inventory,now)
        exchange.execute(value,server,inventory,interaction,adapter.entities,position,player_state.ready and int(player_state.vitals.get("health_pct",0))>0,now)
        return
    if action=="vault_close":vault.close(value);sync_inventory(Time.get_ticks_msec());return
    if action=="conc_cancel":
        concentration.sync(server,player_state.vitals,player_state.ready,Time.get_ticks_msec());concentration.request(value,server.client,Time.get_ticks_msec());return
    if action in ["trainer_refresh","trainer_train"]:
        trainer.sync(server,server.client,Time.get_ticks_msec());trainer.request(value,server.client,Time.get_ticks_msec(),player_state.ready and int(player_state.vitals.get("health_pct",0))>0);return
    if action in ["journal_remove","journal_guide","journal_guide_close"]:
        journal.sync(server,Time.get_ticks_msec());journal.request(value,server,server.client,Time.get_ticks_msec());return
    if action=="target_self":interaction.select_self(server.client,int(server.me_oid));return
    if action in ["group_target","group_invite","group_remove","group_leave"]:
        sync_party(Time.get_ticks_msec());party.request(value,server,server.client,interaction,adapter.entities,Time.get_ticks_msec());return
    if action=="los_reply":line_of_sight.reply(value,server.client,Time.get_ticks_msec());return
    if action=="move":
        if int(server.entry.get("zone",-1))!=207:return
        var p=value.get("position_m",[]);var f=value.get("forward_xz",[])
        if not p is Array or p.size()!=3 or not f is Array or f.size()!=2:return
        for v in p+f:
            if not (v is float or v is int) or not is_finite(float(v)):return
        var next:=Vector3(float(p[0]),float(p[1]),float(p[2]))
        if next.x<0 or next.z<0 or next.x>1638.4 or next.z>1638.4 or next.y < -100 or next.y>2000:return
        var pct:=int(server.max_speed_pct)
        var limit:float=player_state.run_speed_mps(pct)
        var elapsed:=clampf(float(Time.get_ticks_msec()-last_position_send)/1000.0,0.05,0.5)
        if next.distance_to(position)>maxf(5.0,limit*elapsed+1.0):move_rejected+=1;return
        if limit<=0 and next.distance_to(position)>.1:move_rejected+=1;return
        if player_state.ready and int(player_state.vitals.get("health_pct",0))<=0:return
        position=next
        move_commands+=1
        var yaw:=atan2(-float(f[0]),float(f[1]));heading=int(round(yaw*4096.0/TAU))&4095
        var speed:=clampf(float(value.get("speed_mps",0)),0,limit)
        last_move_speed=speed
        peak_move_speed=maxf(peak_move_speed,speed)
        var seen=value.get("target_in_view",false)
        if seen is bool:
            target_sight_id=String(value.get("target_entity_id",""));target_sight=seen;target_sight_at=Time.get_ticks_msec()
        send_position(speed)
        last_position_send=Time.get_ticks_msec()
    elif action in ["target","interact","keyword","dialog_response","dismiss_interaction"]:
        interaction.execute(value,server.client,adapter.entities,position)
    elif action in ["inventory_move","inventory_equip","inventory_unequip","merchant_buy","merchant_sell"]:
        if exchange.inventory_locked():inventory.fail("Wait for the Realm Exchange transaction to finish.");return
        sync_inventory(Time.get_ticks_msec())
        inventory.execute(value,server.client,interaction,adapter.entities,position,Time.get_ticks_msec())
    elif action in ["ui_bank","ui_assign","ui_clear","ui_use","ui_use_slot","ui_detail","ui_detail_close","ui_server_window_close"]:
        sync_inventory(Time.get_ticks_msec());classic_ui.sync(server,inventory.snapshot(),Time.get_ticks_msec())
        ui_pose.global_position=position;ui_pose.heading=heading;ui_pose.velocity=Vector3(0,0,last_move_speed if Time.get_ticks_msec()-last_position_send<300 else 0)
        classic_ui.request(value,server,ui_pose,int(server.entry.get("zone",-1)),target_visible(Time.get_ticks_msec()),player_state.ready and int(player_state.vitals.get("health_pct",0))>0)
    elif action=="player_release":
        if int(server.entry.get("zone",-1))==207:
            release_state.request(value,player_state,server.client,Time.get_ticks_msec());player_state.revision+=1
    elif action=="gm_test_mode":
        if int(server.entry.get("zone",-1))!=207 or not value.get("on") is bool:return
        if int(value.get("player_generation",-1))!=player_state.generation:return
        var mode:="combat" if bool(value.on) else "protected"
        if mode=="combat" and (not player_state.ready or int(player_state.vitals.get("health_pct",0))<=0):return
        if gm_mode.request(mode,server.client,Time.get_ticks_msec()):player_state.revision+=1
    elif action in ["combat_attack","player_sit"]:
        if int(server.entry.get("zone",-1))==207:player_state.execute(value,server.client,interaction.selected_id,adapter.entities,Time.get_ticks_msec(),sync_attack_visibility)
    elif action=="chat":
        var text:=String(value.get("text",""))
        dispatch_chat(text)
    elif action=="door":
        var id:=int(value.get("door_id",-1))
        if not allowed_doors.has(id) or not value.get("open") is bool:return
        var p:Array=allowed_doors[id]
        if p.size()!=3 or position.distance_to(Vector3(float(p[0]),float(p[1]),float(p[2])))>5:return
        server.client.DoorRequest(id,1 if value.open else 0);door_requests+=1

func local_chat(text:String,channel:String="help")->void:
    if chat_state!=null:chat_state.append(text,channel)
    chat_lines.append(text.left(240));if chat_lines.size()>8:chat_lines.pop_front()
func dispatch_chat(text:String)->bool:
    text=text.strip_edges()
    if text.is_empty() or text.length()>240 or text.find("\n")!=-1 or text.find("\r")!=-1:return false
    if classic_ui.create_macro(text):
        classic_ui.sync(server,inventory.snapshot(),Time.get_ticks_msec());local_chat(classic_ui.feedback);return true
    var parts:=text.split(" ",false);var word:=String(parts[0]).to_lower()
    if word=="/loc":
        var zone_name:=String(server.entry.get("zone_name","Connacht" if int(server.entry.get("zone",0))==207 else str(server.entry.get("zone",0))))
        local_chat("%s: loc=%d,%d,%d dir=%d" % [zone_name,roundi(position.x*40),roundi(position.z*40),roundi(position.y*40),int(heading*360.0/4096.0)%360],"system");return true
    if word in ["/quit","/q","/logout"]:request_logout();return true
    if word=="/qbar":
        if parts.size()<2 or parts.size()>3 or not String(parts[1]).is_valid_int() or (parts.size()==3 and not String(parts[2]).is_valid_int()):local_chat("Usage: /qbar page[1..10] bar[1..3]");return false
        var page:=int(parts[1]);var bar:=int(parts[2]) if parts.size()==3 else 1
        if page<1 or page>10 or bar<1 or bar>3:local_chat("Usage: /qbar page[1..10] bar[1..3]");return false
        return classic_ui.request({"action":"ui_bank","bar":bar-1,"bank":page-1},server,ui_pose,int(server.entry.get("zone",-1)),false,true)
    if word=="/train" and parts.size()==1:
        trainer.sync(server,server.client,Time.get_ticks_msec());return trainer.request({"action":"trainer_refresh"},server.client,Time.get_ticks_msec(),player_state.ready and int(player_state.vitals.get("health_pct",0))>0)
    server.command(text);return true

func request_logout()->void:
    if leaving:return
    if player_state.attack_on or player_state.attack_uncertain or bool(player_state.pending.get("on",false)):server.client.call("Attack",false)
    if gm_mode.combat_test or gm_mode.uncertain or gm_mode.pending=="combat":server.client.Command("&bridgegm protected")
    leaving=true;status="Saving and logging out";write_report()
    server.quit_world(true)

func recover_test_region(now:int)->void:
    if not server.playing or leaving:return
    if int(server.entry.get("zone",-1))==207:
        test_return_attempts=0
        return
    # This client only renders Connacht. Preserve the actual bind point and ask
    # the server for the same GM transfer used on entry, after real revival.
    if not player_state.ready or int(player_state.vitals.get("health_pct",0))<=0:
        status="Outside Connacht: waiting for server recovery"
        return
    if not gm_mode.ready or gm_mode.uncertain or not gm_mode.pending.is_empty() or gm_mode.combat_test:
        status="Outside Connacht: waiting for GM protection confirmation"
        return
    if test_return_attempts>=3:
        status="GM return to Ardee was not confirmed. The destination region is not implemented."
        return
    if now-test_return_at<5000:return
    test_return_at=now;test_return_attempts+=1;home_jump_requested=true
    server.command("/jump to %d %d %d 200" % [roundi(initial_spawn.x*40)+35*8192,roundi(initial_spawn.z*40)+51*8192,roundi(initial_spawn.y*40)])
    status="Bind point is outside the test map: requesting GM return to Ardee"

func _process(_delta:float)->void:
    var now:=Time.get_ticks_msec()
    recover_test_region(now)
    player_state.advance(now)
    var gm_revision:int=gm_mode.revision
    gm_mode.advance(now)
    if gm_mode.revision!=gm_revision:player_state.revision+=1
    var release_revision:int=release_state.revision
    release_state.advance(now)
    if release_state.revision!=release_revision:player_state.revision+=1
    adapter.advance_corpses(now)
    if server.playing and not leaving and now-last_inventory_sync>=250:sync_inventory(now)
    if server.playing:ever_played=true
    if transport.peer!=null and transport.peer.get_status()==StreamPeerTCP.STATUS_CONNECTED:
        connected_once=true;last_peer=now
    elif connected_once and now-last_peer>3000:request_logout()
    if ever_played and not connected_once and now-began>180000:request_logout()
    if FileAccess.file_exists(folder.path_join("../Reports/live/logout.request")):request_logout()
    if server.playing and not leaving and int(server.entry.get("zone",-1))==207 and now-last_position_send>1000:
        send_position(0)
        last_position_send=now
    if server.playing:line_of_sight.maintain(server.client,now)
    if server.playing and now-last_ui_sync>=250:
        last_ui_sync=now
        var casting:Dictionary=spell_cast.snapshot("player:local",now)
        classic_ui.casting=casting.duplicate(true);classic_ui.casting_age_ms=int(casting.get("age_ms",0));classic_ui.casting.erase("age_ms")
        sync_party(now)
        journal.sync(server,now);classic_ui.journal=journal.snapshot()
        trainer.sync(server,server.client,now);classic_ui.trainer=trainer.snapshot()
        pet.sync(server,adapter.entities,adapter.oid_to_id);classic_ui.pet=pet.snapshot()
        concentration.sync(server,player_state.vitals,player_state.ready,now);classic_ui.concentration=concentration.snapshot()
        classic_ui.sync(server,inventory.snapshot(),now)
    if now-last_publish>=50:
        last_publish=now
        if server.playing and not leaving:
            interaction.local_target={"name":character_name,"health":float(player_state.vitals.get("health_pct",0))*.01 if player_state.ready else -1.0,"level":int(server.info.get("level",0)),"kind":"player","guild":""}
            interaction.maintain(server.client,adapter.entities,position)
        var rows:Array=[]
        if server.playing and not leaving and int(server.entry.get("zone",-1))==207:
            rows=adapter.entities.values().filter(func(row):return row.id!="player:local")
        if server.playing and not leaving and int(server.entry.get("zone",-1))==207:
            var angle:=-float(heading)*TAU/4096.0
            var health:=float(player_state.vitals.get("health_pct",100))*.01 if player_state.ready else 1.0
            rows.append({"id":"player:local","kind":"player","name":character_name,"model_id":local_model_id,
                "position_m":[position.x,position.y,position.z],"forward_xz":[sin(angle),cos(angle)],"state":"dead" if player_state.ready and health<=0 else "idle","health":health,"health_known":player_state.ready,"position_revision":entry_revision})
        if server.info is Dictionary:adapter.player_level=int(server.info.get("level",adapter.player_level))
        combat_visual.prune(adapter.entities)
        for row in rows:
            row["spell_cast"]=spell_cast.snapshot(String(row.id),now)
            row["combat_visual"]=combat_visual.snapshot(String(row.id),now)
            var fight:Dictionary=combat_visual.fighting.get(String(row.id),{})
            row["combat_active"]=now<int(fight.get("until_ms",0)) and float(row.get("health",1))>0
            row["combat_stance"]=String(fight.get("stance",""))
            if row.id!="player:local":
                row.nameplate=adapter.nameplate(row)
                if row.has("motion"):row.motion.age_ms=maxi(0,now-int(row.motion.at_ms))
        var pct:=int(server.max_speed_pct)
        transport.snapshot_metadata={"character":character_name,"status":status,"in_game":server.playing,
            "max_speed_mps":player_state.run_speed_mps(pct),"zone_lights":zone_lights}
        var states:Array=[]
        for id in door_states:states.append({"id":id,"open":door_states[id]})
        if chat_state!=null:transport.snapshot_metadata["chat"]=chat_state.snapshot()
        transport.snapshot_metadata["spell_visuals"]=spell_visuals.snapshot(now)
        transport.snapshot_metadata["los_queries"]=line_of_sight.snapshot()
        transport.snapshot_metadata["character_lobby"]=character_lobby.snapshot()
        transport.snapshot_metadata["exchange"]=exchange.snapshot()
        transport.snapshot_metadata["classic_ui"]=classic_ui.snapshot()
        transport.snapshot_metadata["messages"]=chat_lines.duplicate()
        transport.snapshot_metadata["doors"]=states
        transport.snapshot_metadata["interaction"]=interaction.snapshot(adapter.entities,position)
        transport.snapshot_metadata["inventory"]=inventory.snapshot()
        var player_snapshot:Dictionary=player_state.snapshot()
        player_snapshot["weapon_stance"]=local_weapon_stance()
        player_snapshot["gm_mode"]=gm_mode.snapshot()
        player_snapshot["release"]=release_state.snapshot()
        transport.snapshot_metadata["player_status"]=player_snapshot
        transport.publish(rows,207,"live-offlinedaoc")
    character_lobby.tick(now,server)
    if now-last_report>1000:last_report=now;write_report()

func sync_party(now:int)->void:
    party.sync(server,adapter.oid_to_id,player_state.vitals,classic_ui.effects.values(),now)
    interaction.group_targets.clear()
    for member in party.members:interaction.group_targets[int(member.oid)]=member
    classic_ui.party=party.snapshot()
    var oid:=int(server.me_oid) if interaction.selected_id=="player:local" else int(interaction.selected_id.get_slice(":",1))
    classic_ui.group_selected_oid=oid if party.members.any(func(m):return int(m.oid)==oid) else 0

func local_weapon_stance()->String:
    var active_slot:int={"standard":10,"twohand":12,"ranged":13}.get(inventory.weapon_set,10)
    var active_item:Dictionary=inventory.items.get(active_slot,{})
    var stance:=String(active_item.get("weapon_stance",""))
    if inventory.weapon_set=="ranged" and stance not in ["xbow","throw"]:stance="bow"
    return stance

func target_visible(now:int)->bool:
    var row:Dictionary=adapter.entities.get(interaction.selected_id,{})
    return target_sight and not target_sight_id.is_empty() and target_sight_id==interaction.selected_id and not row.is_empty() and float(row.get("health",1))>0 and bool(row.get("targetable",true)) and now-target_sight_at<=1500

func sync_attack_visibility()->void:
    # Use the latest native geometry result, not an unconditional visibility grant.
    # Refresh the server heading/action flags immediately before the attack request.
    var now:=Time.get_ticks_msec();var visible:=target_visible(now)
    var sitting:bool=player_state.ready and bool(player_state.vitals.get("sitting",false))
    var oid:=int(interaction.selected_id.get_slice(":",1)) if not interaction.selected_id.is_empty() else 0
    server.client.Heading(heading,oid,0x30 if visible else 0,0x10 if sitting else 0)
    attack_visibility_syncs+=1
    last_attack_visibility={"target":interaction.selected_id,"native_target":target_sight_id,"visible":visible,"age_ms":now-target_sight_at,"at_ms":now}

func send_position(speed:float)->void:
    var valid:bool=target_visible(Time.get_ticks_msec())
    var flags:=0x30 if valid else 0
    var sitting:bool=player_state.ready and bool(player_state.vitals.get("sitting",false))
    var health:=int(player_state.vitals.get("health_pct",100)) if player_state.ready else 100
    server.client.Position(position.x/.025+35*8192,position.z/.025+51*8192,position.y/.025,speed/.025,0,207,0x10 if sitting else 0,true,heading,flags,health,server.me_oid)

func sync_inventory(now:int)->void:
    last_inventory_sync=now
    vault.maintain(interaction,adapter.entities,position,player_state.ready and int(player_state.vitals.get("health_pct",0))>0)
    var vault_state:Dictionary=vault.snapshot()
    var slots:Array=inventory.EQUIPMENT+range(40,80)
    if vault.valid:slots.append_array(range(vault.first,vault.first+vault.count))
    var rows:Array=[]
    for slot in slots:
        if not server.inv.has(slot):continue
        var entry:Dictionary=server.inv[slot]
        var item:Dictionary=item_db.call("item",String(entry.get("id","")))
        var row:Dictionary={"slot":slot,"count":int(entry.get("count",1)),"name":String(item.get("name","")).left(160)}
        for key in ["item_type","object_type","model","icon","level","hand","type_damage","condition","durability","quality","bonus","weight","color","emblem","extension","effect","dps_af","spd_abs"]:row[key]=int(item.get(key,0))
        if weapon_models==null:weapon_models=load("res://game/weapon_models.gd")
        row["weapon_stance"]=String(weapon_models.call("stance",int(row.model)))
        row["equip_slots"]=inventory.slots_for(row)
        rows.append(row)
    inventory.sync(rows,server.money,server.gear,server.weapon_set,int(server.weight_now),int(server.weight_max),now,vault_state)
    exchange.maintain(interaction,adapter.entities,position,player_state.ready and int(player_state.vitals.get("health_pct",0))>0)
    exchange.sync(server,inventory,now)

func write_report()->void:
    var models:Dictionary={}
    if adapter!=null:
        for row in adapter.entities.values():
            if row.kind=="npc":models[str(row.model_id)]=true
    var report={"character":character_name,"status":status,"playing":server.playing,
        "zone":int(server.entry.get("zone",-1)),"npcs":adapter.entities.size() if adapter!=null else 0,
        "events":adapter.events if adapter!=null else 0,"elapsed_ms":Time.get_ticks_msec()-began,
        "position_m":[position.x,position.y,position.z],"messages":chat_lines,
        "source":"real-server","graphics_loaded":false,"model_ids":models.keys(),"entered_world":ever_played,
        "player_prefix":server.selected.get("prefix",""),"move_commands":move_commands,
        "bridge_commands":transport.commands,"bridge_rejected":transport.rejected}
    report["remote_motion"]=adapter.motion_report()
    report["attack_visibility"]={"syncs":attack_visibility_syncs,"last":last_attack_visibility,"selected":interaction.selected_id,"native_target":target_sight_id,"visible":target_visible(Time.get_ticks_msec()),"age_ms":Time.get_ticks_msec()-target_sight_at}
    report["corpse_count"]=adapter.corpses.size()
    report["gm_mode"]=gm_mode.snapshot()
    report["test_region_return"]={"attempts":test_return_attempts,"last_at_ms":test_return_at,"entry_revision":entry_revision}
    report["inventory"]={"slots":inventory.items.size(),"revision":inventory.state_revision,"requests":inventory.requests,"rejected":inventory.rejected,"pending":not inventory.pending.is_empty(),"feedback":inventory.feedback}
    report["combat_visual"]={"packets":combat_visual.packets,"emitted":combat_visual.emitted,"suppressed_ranged":combat_visual.suppressed_ranged}
    report["character_lobby"]=character_lobby.snapshot()
    report["exchange"]=exchange.snapshot()
    report["player_status"]=player_state.snapshot();report["player_status_events"]=player_state.status_events;report["attack_mode_events"]=player_state.mode_events;report["combat_events"]=player_state.combat_events;report["player_state_requests"]=player_state.requests;report["player_state_rejected"]=player_state.rejected
    if adapter.record_motion and not server.playing and ever_played:
        var trace:=FileAccess.open(folder.path_join("../Reports/movement/server_trace.json"),FileAccess.WRITE)
        if trace:trace.store_string(JSON.stringify(adapter.motion_trace));trace.close()
    report["nameplate_player_level"]=adapter.player_level
    var colors:Dictionary={}
    for row in adapter.entities.values():
        if row.kind=="npc":
            var rgb:Array=adapter.nameplate(row).color_rgb
            var key:=str(rgb);colors[key]=int(colors.get(key,0))+1
    report["nameplate_palette_counts"]=colors
    report["interaction_requests"]=interaction.requests;report["interaction_responses"]=interaction.responses;report["interaction_rejected"]=interaction.rejected
    report["selected_id"]=interaction.selected_id;report["interaction"]=interaction.snapshot(adapter.entities,position)
    report["door_requests"]=door_requests;report["door_events"]=door_events;report["door_states"]=door_states
    report["peak_move_speed_mps"]=peak_move_speed
    report["move_rejected"]=move_rejected;report["max_speed_percent"]=int(server.max_speed_pct)
    var available:Array=[]
    for c in server.characters_in("hib"):available.append({"name":String(c.name),"class_name":String(c.get("class_name","")),"class_id":int(c.get("class_id",0)),"level":int(c.get("level",0))})
    report["concentration"]={"requests":concentration.requests,"rejected":concentration.rejected,"state":concentration.snapshot()}
    report["pet"]={"requests":pet.requests,"rejected":pet.rejected,"state":pet.snapshot()}
    report["trainer"]={"requests":trainer.requests,"rejected":trainer.rejected,"state":trainer.snapshot()}
    report["journal"]={"requests":journal.requests,"rejected":journal.rejected,"state":journal.snapshot()}
    report["party"]={"requests":party.requests,"rejected":party.rejected,"state":party.snapshot()}
    report["available_characters"]=available
    report["line_of_sight"]={"requests":line_of_sight.requests,"near_replies":line_of_sight.near_replies,"native_replies":line_of_sight.native_replies,"timeouts":line_of_sight.timeouts,"rejected":line_of_sight.rejected}
    report["spell_cast_packets"]=spell_cast.packets;report["spell_cast"]=spell_cast.snapshot("player:local",Time.get_ticks_msec())
    var target:=folder.path_join("../Reports/live/godot_session.json")
    var file:=FileAccess.open(target,FileAccess.WRITE)
    if file:file.store_string(JSON.stringify(report,"  "));file.close()

func _exit_tree()->void:
    if is_instance_valid(server) and leaving and not server.playing and ever_played:
        status="Session closed through the normal protocol";write_report()
