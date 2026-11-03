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
var realm:="hib"

func refresh(server:Node)->void:
    if not enabled or server.playing:return
    roster=[];choices=[]
    for c in server.characters_in(realm):
        roster.append({"name":String(c.name),"slot":int(c.slot),"race":String(c.get("race","")),"gender":String(c.get("gender","")),"level":int(c.get("level",1)),"class_name":String(c.get("class_name","")),"prefix":String(c.get("prefix",""))})
    for race_name in ["Celt","Firbolg","Elf","Lurikeen","Sylvan"]:
        var race_id:int=int(server.RACE_BY_NAME[race_name])
        for female in [false,true]:
            for cls in server.classes_for(realm,race_id,female):
                choices.append({"id":race_name+":"+("f" if female else "m")+":"+str(int(cls[0])),"race":race_name,"female":female,"class_id":int(cls[0]),"class_name":String(cls[1])})
    ready=not server.character_list_pending();revision+=1
    if not pending:feedback="Choose a character or create a new one."

func creation_result(ok:bool,why:String)->void:
    pending=false;pending_until=0;feedback="Character created. Select it to enter the realm." if ok else why;revision+=1

func tick(now:int,server:Node)->void:
    if pending and pending_until>0 and now>=pending_until:
        pending=false;pending_until=0;feedback="The server has not confirmed creation yet. Refresh the list before trying again.";revision+=1;server.request_characters(realm)

func fail(why:String)->bool:
    feedback=why;revision+=1;return false

func execute(value:Dictionary,server:Node,now:int)->bool:
    if not enabled or not ready or server.playing:return fail("Character selection is not available.")
    if pending:return fail("Wait for the server to finish creating the character.")
    var action:=String(value.get("action",""))
    if action=="character_refresh":server.request_characters(realm);return true
    if int(value.get("lobby_revision",-1))!=revision:return fail("The character list has changed. Select again.")
    if action=="character_enter":
        var name:=String(value.get("name",""))
        for c in server.characters_in(realm):
            if String(c.name)==name:pending=true;feedback="Entering the realm...";revision+=1;enter_requested.emit(c);return true
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
    # Appearance defaults follow the original client; no arbitrary packet fields are accepted.
    var look:Dictionary={"size":1,"face":0,"hair":0,"hair_color":0,"eyes":0,"skin":0,"tattoo":0}
    error=server.create_character(realm,String(selected.race),bool(selected.female),int(selected.class_id),name,look)
    if error!="":return fail(error)
    pending=true;pending_until=now+30000;feedback="Waiting for the server to create the character...";revision+=1;return true

func snapshot()->Dictionary:
    return {"enabled":enabled,"ready":ready,"pending":pending,"revision":revision,"realm":realm,"characters":roster.duplicate(true),"choices":choices.duplicate(true),"feedback":feedback}
