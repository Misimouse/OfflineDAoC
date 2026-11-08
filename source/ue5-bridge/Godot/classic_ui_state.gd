extends RefCounted
## Authoritative UI lists and local shortcuts. Never grants skills, items or stats.
var revision:=0
var entries:Dictionary={}
var macros:Dictionary={}
var macro_request:Callable
var spec_request:Callable
var effects:Dictionary={}
var concentration:Dictionary={}
var pet:Dictionary={}
var pet_request:Callable
var trainer:Dictionary={}
var journal:Dictionary={}
var party:Dictionary={}
var group_selected_oid:=0
var casting:Dictionary={}
var casting_age_ms:=0
var specs:Array=[]
var bars:Array=[]
var banks:Array=[0,0,0]
var skills_received:=false
var catalog_loading:=false
var skills_loading:=false
var spells_loading:=false
var skill_rows:Array=[]
var spell_rows:Array=[]
var group_vitals:Dictionary={}
var character:=""
var save_folder:=""
var feedback:=""
var signature:=""
var data:Dictionary={}
var server_window:Dictionary={}
var window_serial:=0
var detail:Dictionary={}
var detail_started:=0
var hover:Dictionary={}
var hover_started:=0
var hover_request:Array=[]
var item_detail_refresh:Dictionary={}
var item_detail_serial:=0
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
    hover.clear();item_detail_refresh.clear()
    macros.clear();entries.clear()
    for b in 3:
        for k in 10:
            for i in 10:bars[b][k][i]={}
    character=name;save_folder=ProjectSettings.globalize_path(folder).simplify_path()
    DirAccess.make_dir_recursive_absolute(save_folder)
    var path:=storage_path()
    if not FileAccess.file_exists(path):path=legacy_path
    if FileAccess.file_exists(path):
        var value=JSON.parse_string(FileAccess.get_file_as_string(path))
        if value is Dictionary:
            for macro in value.get("macros",[]):
                if macro is Dictionary:register_macro(String(macro.get("name","")),String(macro.get("macro_command","")))
            var old=value.get("bars",value.get("quickbars",[]));var pages=value.get("banks",value.get("bank",[]))
            if old is Array and old.size()==3:
                for b in 3:
                    if not old[b] is Array or old[b].size()!=10:continue
                    for k in 10:
                        if not old[b][k] is Array or old[b][k].size()!=10:continue
                        for i in 10:
                            if old[b][k][i] is Dictionary:
                                var stored:Dictionary=old[b][k][i]
                                if String(stored.get("kind",""))=="macro":
                                    var command:=String(stored.get("macro_command",""))
                                    if command.is_empty() and not String(stored.get("id","")).begins_with("macro:"):command=String(stored.get("id",""))
                                    var macro:Dictionary=register_macro(String(stored.get("name","")),command)
                                    if not macro.is_empty():bars[b][k][i]=macro.duplicate(true)
                                else:bars[b][k][i]=stored.duplicate(true)
            if pages is Array and pages.size()==3:
                for b in 3:banks[b]=clampi(int(pages[b]),0,9)
    revision+=1
func save()->void:
    if character.is_empty() or save_folder.is_empty():return
    var path:=storage_path();var file:=FileAccess.open(path+".tmp",FileAccess.WRITE)
    if file==null:feedback="Could not save the quickbar.";return
    file.store_string(JSON.stringify({"bars":bars,"banks":banks,"macros":macros.values()}));file.close()
    if DirAccess.rename_absolute(path+".tmp",path)!=OK:feedback="Could not save the quickbar."
func entry(id:String,name:String,kind:String,icon:int,border:int=-1,level:int=0,line:String="",item_token:String="")->Dictionary:
    var row:={"id":id,"name":name,"kind":kind,"icon":icon,"border":border,"level":level,"line":line,"item_token":item_token}
    row["token"]=JSON.stringify(row).sha256_text();return row
func register_macro(label:String,command:String)->Dictionary:
    label=label.strip_edges().left(14);command=command.strip_edges()
    if label.is_empty() or command.is_empty() or command.length()>240 or command.find("\n")!=-1 or command.find("\r")!=-1 or label.find("\n")!=-1 or label.find("\r")!=-1:return {}
    var id:="macro:"+JSON.stringify([label,command]).sha256_text()
    if not macros.has(id) and macros.size()>=300:return {}
    var macro:Dictionary=entry(id,label,"macro",-1);macro["macro_command"]=command
    macros[id]=macro;entries[id]=macro.duplicate(true);return macro
func create_macro(text:String)->bool:
    var parts:=text.strip_edges().split(" ",false,2)
    if parts.is_empty() or String(parts[0]).to_lower()!="/macro":return false
    if parts.size()<3:fail("Usage: /macro Name /command");return true
    var macro:Dictionary=register_macro(String(parts[1]),String(parts[2]))
    if macro.is_empty():fail("Invalid macro or macro catalogue is full.");return true
    var placed:=false
    for b in 3:
        for i in 10:
            if bars[b][int(banks[b])][i].is_empty():bars[b][int(banks[b])][i]=macro.duplicate(true);placed=true;break
        if placed:break
    feedback="Macro created in the first free slot of the visible quickbars." if placed else "Macro saved in Abilities. Change page and drag it to a slot."
    revision+=1;save();return true
func observe(kind:String,packet:Dictionary,server:Node)->void:
    if kind in ["you","region_changed","quit"]:detail.clear();hover.clear();item_detail_refresh.clear();server_window.clear()
    if kind=="detail" and not server.take_detail(packet):
        window_serial+=1
        server_window={"caption":String(packet.get("caption","Information")),"lines":packet.get("lines",[]).duplicate(true),"status":"ready","token":str(window_serial)}
    if kind in ["group","you","region_changed","quit"]:group_vitals.clear()
    if kind!="group_update":return
    for u in packet.get("list",[]):
        var i:=int(u.get("index",-1))
        if i<0 or i>=server.group_members.size():continue
        var oid:=str(int(server.group_members[i].get("oid",0)))
        if not group_vitals.has(oid):group_vitals[oid]={}
        for key in ["hp","power","end"]:
            if u.has(key):group_vitals[oid][key]=int(u[key])
func capture_lists(server:Node)->void:
    skill_rows=server.skills.duplicate(true);spell_rows=server.spell_lines.duplicate(true);skills_received=true
func sync(server:Node,inventory:Dictionary,now:int)->void:
    var next:Dictionary={};var next_specs:Array=[];var first:int=skill_rows.size()
    for i in skill_rows.size():
        if int(skill_rows[i].page)!=0:first=i;break
    for i in skill_rows.size():
        var sk:Dictionary=skill_rows[i];var page:=int(sk.page)
        if page==0:
            next_specs.append({"name":String(sk.name),"level":int(sk.level),"bonus":int(sk.get("bonus",0))})
            # Original panel_sheets exposes the Stealth specialization as a usable ability.
            # Its index is the original type-zero UseSkill index, not a non-spec skill index.
            if String(sk.name)=="Stealth" and int(sk.level)>0:
                var id:="srv:spec:%d" % i
                var ic:Array=server.skill_icon("icon",403)
                next[id]=entry(id,"Stealth","ability",int(ic[0]),int(ic[1]),int(sk.level),"Stealth")
            continue
        var kind:="style" if page==2 else "spell" if page in [3,4] else "ability"
        var ic:Array=server.skill_icon("style" if kind=="style" else "spell" if kind=="spell" else "icon",int(sk.icon))
        var group:=""
        if kind=="spell":
            var special:=int(sk.get("special",254));group="SONGS" if page==4 or special==255 else "SPELLS"
            if special>=0 and special<skill_rows.size() and int(skill_rows[special].page)==0:group=String(skill_rows[special].name)
        var id:="srv:skill:%d" % (i-first)
        next[id]=entry(id,String(sk.name),kind,int(ic[0]),int(ic[1]),int(sk.level),group)
    for li in spell_rows.size():
        var line:Dictionary=spell_rows[li]
        for sp in line.spells:
            var kind:="style" if String(sp.get("kind","spell"))=="style" else "spell";var ic:Array=server.skill_icon("style" if kind=="style" else "spell",int(sp.icon));var id:="srv:spell:%d:%d" % [li,int(sp.level)]
            next[id]=entry(id,String(sp.name),kind,int(ic[0]),int(ic[1]),int(sp.level),String(line.name))
    for it in inventory.get("items",[]):
        var id:="srv:%d" % int(it.slot);next[id]=entry(id,String(it.name),"item",int(it.get("icon",-1)),-1,0,"",String(it.get("token","")))
    for it in inventory.get("items",[]):
        if int(it.slot)>=110:next["srv:%d" % int(it.slot)]["stored"]=true
    for id in macros:next[String(id)]=macros[id].duplicate(true)
    for command in pet.get("entries",[]):next[String(command.id)]=command.duplicate(true)
    entries=next;specs=next_specs
    effects.clear()
    var remaining:Dictionary={};var indices:Array=server.effects.keys();indices.sort()
    for index in indices:
        var fx:Dictionary=server.effects[index];var ic:Array=server.skill_icon("spell",int(fx.icon));var id:="srv:effect:%d" % int(index)
        var row:Dictionary=entry(id,String(fx.name),"effect",int(ic[0]),int(ic[1]))
        row["effect_icon"]=int(fx.icon);row["negative"]=int(fx.get("negative",0))!=0;row["until_ms"]=int(fx.get("until",0));row["token"]=JSON.stringify(row).sha256_text()
        effects[id]=row;remaining[id]=maxi(0,int(row.until_ms)-now) if int(row.until_ms)>0 else -1

    sync_item_details(server,now)
    if not detail.is_empty():
        var current:Dictionary=detail_entry(String(detail.entry_id),String(detail.entry_token))
        if current.is_empty():detail.clear()
        elif detail.get("status","")=="pending" and not item_refreshing(current):
            var response:Dictionary=server.item_lines(String(detail.key))
            if not response.is_empty():
                detail["caption"]=String(response.get("caption",current.name));detail["lines"]=response.get("lines",[]).duplicate(true);detail["status"]="ready"
            elif now-detail_started>=4000:detail["status"]="unavailable"

    if not hover.is_empty():
        var current:Dictionary=detail_entry(String(hover.entry_id),String(hover.entry_token))
        if current.is_empty():hover.clear()
        elif current.kind!="macro" and not item_refreshing(current):
            # Share the original cache keys and its inventory/skill invalidation rules.
            var response:Dictionary=server.item_lines(hover.key)
            if not response.is_empty():
                hover["caption"]=String(response.get("caption",current.name));hover["lines"]=response.get("lines",[]).duplicate(true);hover["status"]="ready"
            elif hover.status=="ready":
                hover["lines"]=[];hover["status"]="pending";hover_started=now
                server.prefetch_detail(hover.key,int(hover_request[0]),int(hover_request[1]),String(current.name))
            elif hover.status=="pending" and now-hover_started>=4000:hover["status"]="unavailable"

    var changed:=false
    for b in 3:
        for k in 10:
            for i in 10:
                var old:Dictionary=bars[b][k][i];var current:Dictionary=entries.get(String(old.get("id","")),{})
                if not current.is_empty() and old.get("name","")==current.name and old.get("kind","")==current.kind and old.get("token","")!=current.token:
                    bars[b][k][i]=current.duplicate(true);changed=true
    if changed:save()
    var group:Array=[]
    for member in server.group_members:
        var row:Dictionary=member.duplicate(true);row.merge(group_vitals.get(str(int(row.get("oid",0))),{}),true);group.append(row)
    var stable:={"character":character,"ready":not server.info.is_empty(),"skills_ready":skills_received,"info":server.info.duplicate(true),"points":server.points.duplicate(true),"stats":server.stats.duplicate(),"stat_buffs":server.stat_buffs.duplicate(),"resists":server.resists.duplicate(),"con_lost":int(server.con_lost),"weapon_stats":server.weapon_stats.duplicate(true),"specs":specs,"entries":entries.values(),"concentration":concentration.duplicate(true),"pet":pet.duplicate(true),"trainer":trainer.duplicate(true),"journal":journal.duplicate(true),"party":party.duplicate(true),"group_selected_oid":group_selected_oid,"effects":effects.values(),"casting":casting.duplicate(true),"group":party.get("members",group),"bars":bars,"banks":banks,"feedback":feedback,"detail":detail.duplicate(true),"server_window":server_window.duplicate(true)}
    var stamp:=JSON.stringify(stable)
    if stamp!=signature:signature=stamp;revision+=1
    data=stable;data["hover"]=hover.duplicate(true)
    var reuse:Dictionary={}
    for id in entries:
        var left:float=server.reuse_left(id)
        if left>0:reuse[id]=roundi(left*1000)
    data["casting_age_ms"]=casting_age_ms;data["effects_remaining_ms"]=remaining;data["reuse_ms"]=reuse;data["revision"]=revision
func fail(text:String)->bool:feedback=text;revision+=1;return false
func item_refreshing(e:Dictionary)->bool:
    return e.get("kind","")=="item" and item_detail_refresh.has(int(String(e.id).trim_prefix("srv:")))
func refresh_used_item(server:Node,e:Dictionary)->void:
    # Original DOL can change charges without an inventory packet. Discard
    # cached text only; never predict charges or acknowledge a successful use.
    var cache:Variant=server.get("_item_lines")
    if not cache is Dictionary:return
    var slot:=int(String(e.id).trim_prefix("srv:"));item_detail_serial+=1
    cache.erase(slot);cache.erase("bridge-ui:"+String(e.token))
    var key:="bridge-use-refresh:%d:%d" % [slot,item_detail_serial]
    item_detail_refresh[slot]={"key":key,"id":e.id,"token":e.token,"until_ms":Time.get_ticks_msec()+4000}
    for panel in [hover,detail]:
        if panel.get("entry_id","")==e.id and panel.get("entry_token","")==e.token:panel["lines"]=[];panel["status"]="pending"
    # A separate queue key preserves any older in-flight Detail response.
    server.prefetch_detail(key,1,slot,String(e.name))
func sync_item_details(server:Node,now:int)->void:
    if item_detail_serial==0:return
    var cache:Variant=server.get("_item_lines")
    if not cache is Dictionary:return
    for slot in item_detail_refresh.keys():
        var request:Dictionary=item_detail_refresh[slot];var current:Dictionary=detail_entry(request.id,request.token)
        var response:Dictionary=server.item_lines(request.key)
        if current.is_empty():item_detail_refresh.erase(slot)
        elif not response.is_empty():
            cache[slot]=response.duplicate(true);cache["bridge-ui:"+String(request.token)]=response.duplicate(true);item_detail_refresh.erase(slot)
        elif now>=int(request.until_ms):
            cache.erase(slot);cache.erase("bridge-ui:"+String(request.token));item_detail_refresh.erase(slot)
            for panel in [hover,detail]:
                if panel.get("entry_id","")==request.id and panel.get("entry_token","")==request.token:panel["lines"]=[];panel["status"]="unavailable"
    var waiting:Array=[]
    for request in item_detail_refresh.values():waiting.append(request.key)
    for key in cache.keys():
        if key is String and String(key).begins_with("bridge-use-refresh:") and not key in waiting:cache.erase(key)
func resolve(id:String,token:String="")->Dictionary:
    var e:Dictionary=entries.get(id,{})
    return e if not e.is_empty() and (token.is_empty() or String(e.token)==token) else {}
func detail_entry(id:String,token:String)->Dictionary:
    var e:Dictionary=effects.get(id,{}) if id.begins_with("srv:effect:") else entries.get(id,{})
    return e if not e.is_empty() and String(e.token)==token else {}
func index(value:Dictionary,key:String,limit:int)->int:
    var v=value.get(key,-1)
    if not (v is int or v is float) or not is_finite(float(v)) or float(v)!=floor(float(v)) or v<0 or v>=limit:return -1
    return int(v)
func request(value:Dictionary,server:Node,player:Node3D,zone:int,visible:bool,alive:bool)->bool:
    var action:=String(value.get("action",""))
    if action=="ui_hover":
        var e:Dictionary=detail_entry(String(value.get("entry_id","")),String(value.get("entry_token","")))
        if e.is_empty() or zone!=207 or catalog_loading:return false
        if not hover.is_empty() and hover.entry_id==e.id and hover.entry_token==e.token and (hover.status!="unavailable" or Time.get_ticks_msec()-hover_started<5000):return true
        if e.kind=="macro":
            hover={"entry_id":e.id,"entry_token":e.token,"key":"macro-local","caption":e.name,"lines":[String(e.macro_command)],"status":"ready"};return true
        var request:Array=[5,int(e.effect_icon)] if e.kind=="effect" else [1,int(String(e.id).trim_prefix("srv:"))] if e.kind=="item" else server.skill_detail(e)
        if request.is_empty():return false
        var key:Variant=int(request[1]) if e.kind=="item" else "fx:%d" % int(request[1]) if e.kind=="effect" else "sk:%d:%d" % [int(request[0]),int(request[1])]
        hover_request=request.duplicate()
        hover={"entry_id":e.id,"entry_token":e.token,"key":key,"caption":e.name,"lines":[],"status":"pending"};hover_started=Time.get_ticks_msec()
        server.prefetch_detail(key,int(request[0]),int(request[1]),String(e.name));return true
    if action=="ui_server_window_close":
        if server_window.is_empty():return true
        if String(value.get("window_token",""))!=String(server_window.token):return fail("The window has changed. Close it again.")
        server_window.clear();revision+=1;return true
    if action=="ui_detail_close":detail.clear();revision+=1;return true
    if action=="ui_detail":
        var e:Dictionary=detail_entry(String(value.get("entry_id","")),String(value.get("entry_token","")))
        if e.is_empty() or String(value.get("entry_token",""))!=String(e.token):return fail("The entry has changed. Select it again.")
        if e.kind=="macro":
            server_window.clear();detail={"entry_id":e.id,"entry_token":e.token,"key":"macro-local","caption":e.name,"lines":[String(e.macro_command)],"status":"ready"};revision+=1;return true
        if zone!=207 or catalog_loading:return fail("Wait for the list to finish updating.")
        var request:Array=[5,int(e.effect_icon)] if e.kind=="effect" else [1,int(String(e.id).trim_prefix("srv:"))] if e.kind=="item" else server.skill_detail(e)
        if request.is_empty():return fail("No information is available for this entry.")
        var key:="bridge-ui:"+String(e.token)
        server_window.clear()
        detail={"entry_id":e.id,"entry_token":e.token,"key":key,"caption":e.name,"lines":[],"status":"pending"};detail_started=Time.get_ticks_msec()
        server.prefetch_detail(key,int(request[0]),int(request[1]),String(e.name));revision+=1;return true
    if action=="ui_bank":
        var b:=index(value,"bar",3);var k:=index(value,"bank",10)
        if b<0 or b>2 or k<0 or k>9:return fail("Invalid quickbar.")
        banks[b]=k;revision+=1;save();return true
    if action in ["ui_assign","ui_clear"]:
        var b:=index(value,"bar",3);var k:=index(value,"bank",10);var i:=index(value,"slot",10)
        if b<0 or b>2 or k<0 or k>9 or i<0 or i>9:return fail("Invalid slot.")
        var e:Dictionary={}
        if action=="ui_assign":
            e=resolve(String(value.get("entry_id","")),String(value.get("entry_token","")))
            if e.is_empty() or String(value.get("entry_token",""))!=String(e.token):return fail("The list has changed. Select the entry again.")
        if action=="ui_assign":
            if bool(e.get("stored",false)):return fail("Withdraw the item from the vault before assigning it to a quickbar.")
            var fb:=index(value,"from_bar",3);var fk:=index(value,"from_bank",10);var fi:=index(value,"from_slot",10)
            if fb>=0 and fb<3 and fk>=0 and fk<10 and fi>=0 and fi<10 and not (fb==b and fk==k and fi==i):
                var old:Dictionary=bars[fb][fk][fi]
                if old.get("id","")!=e.id or old.get("token","")!=e.token:return fail("The dragged shortcut has changed.")
                bars[fb][fk][fi]={}
        bars[b][k][i]=e.duplicate(true);feedback="";revision+=1;save();return true
    if action not in ["ui_use","ui_use_slot"]:return false
    var e:Dictionary={}
    if action=="ui_use_slot":
        var b:=index(value,"bar",3);var i:=index(value,"slot",10)
        if b<0 or b>2 or i<0 or i>9:return false
        var old:Dictionary=bars[b][int(banks[b])][i];e=resolve(String(old.get("id","")),String(old.get("token","")))
        if e.is_empty() or String(e.get("name",""))!=String(old.get("name","")):return fail("This shortcut no longer matches the current list.")
    else:
        e=resolve(String(value.get("entry_id","")),String(value.get("entry_token","")))
        if e.is_empty() or String(value.get("entry_token",""))!=String(e.token):return fail("The list has changed.")
    if e.kind=="macro":
        var macro:Dictionary=macros.get(String(e.id),{})
        if macro.is_empty() or String(macro.get("macro_command",""))!=String(e.get("macro_command","")):return fail("The macro has changed.")
        if macro_request.is_valid():
            if not bool(macro_request.call(String(macro.macro_command))):return fail("Could not send the macro.")
        else:server.command(String(macro.macro_command))
        feedback="Macro requested.";revision+=1;return true
    if bool(e.get("stored",false)):return fail("Withdraw the item from the vault before using it.")
    if not alive or zone!=207:return fail("You cannot use this action now.")
    if e.kind=="petcmd":
        if not pet_request.is_valid():return fail("Pet commands are not available yet.")
        var accepted:bool=pet_request.call({"command":String(e.command),"pet_token":String(e.pet_token)})
        feedback="Command sent." if accepted else "Could not send the command. Check the pet window.";revision+=1;return accepted
    if catalog_loading:return fail("The server is updating the lists.")
    if server.reuse_left(String(e.id))>0:return fail("This action is still recovering.")
    if String(e.id).begins_with("srv:spec:"):
        if not spec_request.is_valid() or not bool(spec_request.call(e)):return fail("The server does not recognize this specialization action.")
        feedback="Request sent to server.";revision+=1;return true
    if not server.use_entry(String(e.id),player,zone,visible):return fail("The server does not recognize this entry.")
    if e.kind=="item":refresh_used_item(server,e)
    feedback="Request sent to server.";revision+=1;return true
func snapshot()->Dictionary:
    var out:Dictionary=data.duplicate(true);out["revision"]=revision;out["bars"]=bars;out["banks"]=banks;out["feedback"]=feedback;out["detail"]=detail.duplicate(true);out["hover"]=hover.duplicate(true);out["server_window"]=server_window.duplicate(true);return out
