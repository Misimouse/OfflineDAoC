extends RefCounted
## Character lists and creation remain authoritative on the original server.
signal enter_requested(character:Dictionary)
var enabled:=false
var ready:=false
var pending:=false
var revision:=0
var feedback:="Connecting to the character server..."
var roster:Array=[]
var choices:Array=[]
var pending_until:=0
var pending_creation:Dictionary={}
var realm:="hib"
var appearance:RefCounted

func validated_look(value:Variant,prefix:String)->Dictionary:
    if appearance==null:appearance=load(get_script().resource_path.get_base_dir().path_join("character_appearance.gd")).new()
    return appearance.normalise(value,prefix)

func stored_look(character:Dictionary)->Dictionary:
    # Only original server/local-store data uses this compatibility view.
    # Commands remain strict and opening a menu never rewrites saved appearance.
    if appearance==null:appearance=load(get_script().resource_path.get_base_dir().path_join("character_appearance.gd")).new()
    var original:Variant=character.get("look",{})
    if not original is Dictionary:original={}
    var checked:Dictionary=appearance.normalise(original,String(character.get("prefix","")),true)
    return checked.look if checked.ok else original.duplicate(true)

func refresh(server:Node)->void:
    if not enabled or server.playing:return
    roster=[];choices=[]
    for c in server.characters_in(realm):
        var caption:=String(c.get("class_name",""))
        # Some overview packets omit a base-class caption. The numeric class is
        # still authoritative; do not render an incomplete "NAME THE" heading.
        if caption.is_empty():
            caption=String({51:"Magician",52:"Guardian",53:"Naturalist",54:"Stalker",57:"Forester"}.get(int(c.get("class_id",0)),""))
        roster.append({"name":String(c.name),"slot":int(c.slot),"race":String(c.get("race","")),"gender":String(c.get("gender","")),"level":int(c.get("level",1)),"class_name":caption,"prefix":String(c.get("prefix","")),"location":String(c.get("location_text","")),"look":stored_look(c),"overview":c.get("server",{}).duplicate(true)})
    for race_name in ["Celt","Firbolg","Elf","Lurikeen","Sylvan","Shar","Minotaur"]:
        if not server.RACE_BY_NAME.has(race_name):continue
        var race_id:int=int(server.RACE_BY_NAME[race_name])
        for female in [false,true]:
            var race_gender:String=String(server.classes.get("race_genders",{}).get(str(race_id),""))
            if race_gender not in ["","female","male"]:continue
            if race_gender!="" and female!=(race_gender=="female"):continue
            for cls in server.classes_for(realm,race_id,female):
                var definition:Dictionary=server.classes.get("classes",{}).get(str(int(cls[0])),{})
                var constraint:String=String(definition.get("gender",""))
                if constraint not in ["","female","male"]:continue
                if constraint!="" and female!=(constraint=="female"):continue
                choices.append({"id":race_name+":"+("f" if female else "m")+":"+str(int(cls[0])),"race":race_name,"female":female,"class_id":int(cls[0]),"class_name":String(cls[1])})
    ready=not server.character_list_pending();revision+=1
    if not pending:feedback="Choose a character or create a new one."

func creation_result(ok:bool,why:String)->void:
    pending=false;pending_until=0;pending_creation.clear();feedback="Character created. Select it to enter the realm." if ok else why;revision+=1

func tick(now:int,server:Node)->void:
    if pending and pending_until>0 and now>=pending_until:
        var checking_name:=not pending_creation.is_empty()
        pending=false;pending_until=0;pending_creation.clear();revision+=1
        if checking_name:
            feedback="The server did not answer the name check. Please try again."
        else:
            feedback="The server has not confirmed creation yet. Refresh the list before trying again."
            ready=false;server.request_characters(realm)

func name_result(name:String,result:int,server:Node,now:int)->void:
    if not pending or pending_creation.is_empty() or name.nocasecmp_to(String(pending_creation.name))!=0:return
    if result!=0:
        creation_result(false,"That name is already in use." if result==2 else "The server does not allow that name.")
        return
    var request:=pending_creation.duplicate(true)
    pending_creation.clear()
    var error:String=server.create_character(realm,String(request.race),bool(request.female),int(request.class_id),String(request.name),request.look)
    if error!="":creation_result(false,error);return
    pending_until=now+30000;feedback="Waiting for the server to create the character...";revision+=1

func fail(why:String)->bool:
    feedback=why;revision+=1;return false

func execute(value:Dictionary,server:Node,now:int)->bool:
    if not enabled or not ready or server.playing:return fail("Character selection is not available.")
    if pending:return fail("Wait for the server to finish creating the character.")
    if server.character_list_pending():return fail("Wait for the character list to finish refreshing.")
    var action:=String(value.get("action",""))
    if action=="character_refresh":server.request_characters(realm);return true
    if int(value.get("lobby_revision",-1))!=revision:return fail("The character list has changed. Select again.")
    if action=="character_enter":
        var name:=String(value.get("name",""))
        for c in server.characters_in(realm):
            if String(c.name)==name:pending=true;feedback="Entering the realm...";revision+=1;enter_requested.emit(c);return true
        return fail("That character is no longer in the server's list.")
    if action=="character_customize":
        for c in server.characters_in(realm):
            if String(c.name)!=String(value.get("name","")):continue
            var checked:Dictionary=validated_look(value.get("look",{}),String(c.get("prefix","")))
            if not checked.ok:return fail(String(checked.error))
            server.save_look(String(c.name),checked.look);refresh(server)
            feedback="Character appearance saved.";return true
        return fail("That character is no longer in the server's list.")
    if action!="character_create":return false
    if roster.size()>=10:return fail("This realm has no free character slot.")
    var selected:Dictionary={}
    for choice in choices:
        if choice.id==String(value.get("choice_id","")):selected=choice;break
    if selected.is_empty():return fail("Choose a valid race and class.")
    var name:=String(value.get("name",""));var error:String=server.name_error(name)
    if error!="":return fail(error)
    for c in roster:
        if String(c.name).nocasecmp_to(name)==0:return fail("You already have a character with that name.")
    var prefixes:Dictionary={"Celt":"cel","Firbolg":"fir","Elf":"elf","Lurikeen":"lur","Sylvan":"syl","Shar":"sha","Minotaur":"mino"}
    var prefix:String=String(prefixes[selected.race])
    if selected.race!="Minotaur":prefix+="_f" if selected.female else "_m"
    var checked:Dictionary=validated_look(value.get("look",{}),prefix)
    if not checked.ok:return fail(String(checked.error))
    var look:Dictionary=checked.look
    pending_creation={"race":String(selected.race),"female":bool(selected.female),"class_id":int(selected.class_id),"name":name,"look":look}
    pending=true;pending_until=now+30000;feedback="Checking character name...";revision+=1
    server.check_name(name)
    return true

func snapshot()->Dictionary:
    return {"enabled":enabled,"ready":ready,"pending":pending,"revision":revision,"realm":realm,"characters":roster.duplicate(true),"choices":choices.duplicate(true),"feedback":feedback}
