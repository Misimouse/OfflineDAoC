from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
from pathlib import Path
R=Path(str(ROOT))
s='''extends RefCounted
## Authoritative UI lists and local shortcuts. Never grants skills, items or stats.
var revision:=0
var entries:Dictionary={}
var specs:Array=[]
var bars:Array=[]
var banks:Array=[0,0,0]
var skills_received:=false
var character:=""
var save_folder:=""
var feedback:=""
var signature:=""
var data:Dictionary={}
func _init()->void:
    for b in 3:
        var pages:Array=[]
        for k in 10:
            var slots:Array=[]
            for i in 10:slots.append({})
            pages.append(slots)
        bars.append(pages)
func storage_path()->String:return save_folder.path_join(character.to_lower().sha256_text()+".json")
func open_character(name:String,folder:String,legacy_path:String="")->void:
    if character==name:return
    character=name;save_folder=folder
    DirAccess.make_dir_recursive_absolute(save_folder)
    var path:=storage_path()
    if not FileAccess.file_exists(path):path=legacy_path
    if FileAccess.file_exists(path):
        var value=JSON.parse_string(FileAccess.get_file_as_string(path))
        if value is Dictionary:
            var old=value.get("bars",value.get("quickbars",[]));var pages=value.get("banks",value.get("bank",[]))
            if old is Array and old.size()==3:
                for b in 3:
                    if not old[b] is Array or old[b].size()!=10:continue
                    for k in 10:
                        if not old[b][k] is Array or old[b][k].size()!=10:continue
                        for i in 10:
                            if old[b][k][i] is Dictionary:bars[b][k][i]=old[b][k][i].duplicate(true)
            if pages is Array and pages.size()==3:
                for b in 3:banks[b]=clampi(int(pages[b]),0,9)
    revision+=1
func save()->void:
    if character.is_empty() or save_folder.is_empty():return
    var path:=storage_path();var file:=FileAccess.open(path+".tmp",FileAccess.WRITE)
    if file==null:feedback="No se pudo guardar la barra.";return
    file.store_string(JSON.stringify({"bars":bars,"banks":banks}));file.close()
    if DirAccess.rename_absolute(path+".tmp",path)!=OK:feedback="No se pudo guardar la barra."
func entry(id:String,name:String,kind:String,icon:int,border:int=-1,level:int=0,line:String="")->Dictionary:
    var row:={"id":id,"name":name,"kind":kind,"icon":icon,"border":border,"level":level,"line":line}
    row["token"]=JSON.stringify(row).sha256_text();return row
func sync(server:Node,inventory:Dictionary,now:int)->void:
    var next:Dictionary={};var next_specs:Array=[];var first:int=server.skills.size()
    for i in server.skills.size():
        if int(server.skills[i].page)!=0:first=i;break
    for i in server.skills.size():
        var sk:Dictionary=server.skills[i];var page:=int(sk.page)
        if page==0:
            next_specs.append({"name":String(sk.name),"level":int(sk.level),"bonus":int(sk.get("bonus",0))});continue
        var kind:="style" if page==2 else "spell" if page in [3,4] else "ability"
        var ic:Array=server.skill_icon("style" if kind=="style" else "spell" if kind=="spell" else "icon",int(sk.icon))
        var group:=""
        if kind=="spell":
            var special:=int(sk.get("special",254));group="SONGS" if page==4 or special==255 else "SPELLS"
            if special>=0 and special<server.skills.size() and int(server.skills[special].page)==0:group=String(server.skills[special].name)
        var id:="srv:skill:%d" % (i-first)
        next[id]=entry(id,String(sk.name),kind,int(ic[0]),int(ic[1]),int(sk.level),group)
    for li in server.spell_lines.size():
        var line:Dictionary=server.spell_lines[li]
        for sp in line.spells:
            var kind:=String(sp.get("kind","spell"));var ic:Array=server.skill_icon("style" if kind=="style" else "spell",int(sp.icon));var id:="srv:spell:%d:%d" % [li,int(sp.level)]
            next[id]=entry(id,String(sp.name),kind,int(ic[0]),int(ic[1]),int(sp.level),String(line.name))
    for it in inventory.get("items",[]):
        var id:="srv:%d" % int(it.slot);next[id]=entry(id,String(it.name),"item",int(it.get("icon",-1)))
    entries=next;specs=next_specs
    var stable:={"character":character,"ready":not server.info.is_empty(),"skills_ready":skills_received,"info":server.info.duplicate(true),"points":server.points.duplicate(true),"stats":server.stats.duplicate(),"stat_buffs":server.stat_buffs.duplicate(),"resists":server.resists.duplicate(),"con_lost":int(server.con_lost),"weapon_stats":server.weapon_stats.duplicate(true),"specs":specs,"entries":entries.values(),"group":server.group_members.duplicate(true),"bars":bars,"banks":banks,"feedback":feedback}
    var stamp:=JSON.stringify(stable)
    if stamp!=signature:signature=stamp;revision+=1
    data=stable
    var reuse:Dictionary={}
    for id in entries:
        var left:float=server.reuse_left(id)
        if left>0:reuse[id]=roundi(left*1000)
    data["reuse_ms"]=reuse;data["revision"]=revision
func fail(text:String)->bool:feedback=text;revision+=1;return false
func resolve(id:String,token:String="")->Dictionary:
    var e:Dictionary=entries.get(id,{})
    return e if not e.is_empty() and (token.is_empty() or String(e.token)==token) else {}
func request(value:Dictionary,server:Node,player:Node3D,zone:int,visible:bool,alive:bool)->bool:
    var action:=String(value.get("action",""))
    if action=="ui_bank":
        var b:=int(value.get("bar",-1));var k:=int(value.get("bank",-1))
        if b<0 or b>2 or k<0 or k>9:return fail("Barra no válida.")
        banks[b]=k;revision+=1;save();return true
    if action in ["ui_assign","ui_clear"]:
        var b:=int(value.get("bar",-1));var k:=int(value.get("bank",-1));var i:=int(value.get("slot",-1))
        if b<0 or b>2 or k<0 or k>9 or i<0 or i>9:return fail("Casilla no válida.")
        var e:Dictionary={}
        if action=="ui_assign":
            e=resolve(String(value.get("entry_id","")),String(value.get("entry_token","")))
            if e.is_empty() or String(value.get("entry_token",""))!=String(e.token):return fail("La lista ha cambiado. Vuelve a elegir la entrada.")
        bars[b][k][i]=e.duplicate(true);feedback="";revision+=1;save();return true
    if action not in ["ui_use","ui_use_slot"]:return false
    var e:Dictionary={}
    if action=="ui_use_slot":
        var b:=int(value.get("bar",-1));var i:=int(value.get("slot",-1))
        if b<0 or b>2 or i<0 or i>9:return false
        var old:Dictionary=bars[b][int(banks[b])][i];e=resolve(String(old.get("id","")),String(old.get("token","")))
        if e.is_empty() or String(e.get("name",""))!=String(old.get("name","")):return fail("El acceso ya no coincide con la lista actual.")
    else:
        e=resolve(String(value.get("entry_id","")),String(value.get("entry_token","")))
        if e.is_empty() or String(value.get("entry_token",""))!=String(e.token):return fail("La lista ha cambiado.")
    if not alive or zone!=207:return fail("No puedes usar esa acción ahora.")
    if server.reuse_left(String(e.id))>0:return fail("La acción aún se está recuperando.")
    if not server.use_entry(String(e.id),player,zone,visible):return fail("El servidor no reconoce esa entrada.")
    feedback="Solicitud enviada al servidor.";revision+=1;return true
func snapshot()->Dictionary:
    var out:Dictionary=data.duplicate(true);out["revision"]=revision;out["bars"]=bars;out["banks"]=banks;out["feedback"]=feedback;return out
'''
(R/'Godot/classic_ui_state.gd').write_text(s,encoding='utf-8')
(R/'Godot/ui_player_pose.gd').write_text('''extends Node3D
var velocity:=Vector3.ZERO
var heading:=0
func facing()->float:return -float(heading)*TAU/4096.0
''',encoding='utf-8')
p=R/'Godot/live_gateway.gd';s=p.read_text(encoding='utf-8').replace('var release_state:RefCounted','var release_state:RefCounted\nvar classic_ui:RefCounted\nvar ui_pose:Node3D\nvar last_ui_sync:=0\nvar last_move_speed:=0.0');s=s.replace('release_state=load(folder.path_join("player_release.gd")).new()','release_state=load(folder.path_join("player_release.gd")).new()\n    classic_ui=load(folder.path_join("classic_ui_state.gd")).new()\n    ui_pose=load(folder.path_join("ui_player_pose.gd")).new();add_child(ui_pose)');s=s.replace('server.characters_ready.connect(characters_ready)','server.skills_changed.connect(func():classic_ui.skills_received=true)\n    server.characters_ready.connect(characters_ready)');s=s.replace('entered=true;character_name=chosen.name;status=', 'entered=true;character_name=chosen.name;classic_ui.open_character(character_name,folder.path_join("../Client/Saved/ClassicUI"),server.quickbars_path(character_name));status=');s=s.replace('peak_move_speed=maxf(peak_move_speed,speed)','last_move_speed=speed\n        peak_move_speed=maxf(peak_move_speed,speed)');s=s.replace('    elif action=="player_release":','''    elif action in ["ui_bank","ui_assign","ui_clear","ui_use","ui_use_slot"]:
        sync_inventory(Time.get_ticks_msec());classic_ui.sync(server,inventory.snapshot(),Time.get_ticks_msec())
        ui_pose.global_position=position;ui_pose.heading=heading;ui_pose.velocity=Vector3(0,0,last_move_speed if Time.get_ticks_msec()-last_position_send<300 else 0)
        classic_ui.request(value,server,ui_pose,int(server.entry.get("zone",-1)),target_visible(Time.get_ticks_msec()),player_state.ready and int(player_state.vitals.get("health_pct",0))>0)
    elif action=="player_release":''');s=s.replace('    if now-last_publish>=50:','    if server.playing and now-last_ui_sync>=250:\n        last_ui_sync=now;classic_ui.sync(server,inventory.snapshot(),now)\n    if now-last_publish>=50:');s=s.replace('transport.snapshot_metadata["messages"]=chat_lines.duplicate()','transport.snapshot_metadata["classic_ui"]=classic_ui.snapshot()\n        transport.snapshot_metadata["messages"]=chat_lines.duplicate()');p.write_text(s,encoding='utf-8')
p=R/'Godot/visual_bridge.gd';s=p.read_text(encoding='utf-8').replace('"player_status","messages"]','"player_status","messages","classic_ui"]').replace('"gm_test_mode","player_release"]','"gm_test_mode","player_release","ui_bank","ui_assign","ui_clear","ui_use","ui_use_slot"]');p.write_text(s,encoding='utf-8')
print('Estado completo del panel y barras conectado al gateway')
