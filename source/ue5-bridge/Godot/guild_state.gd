extends RefCounted
## Original CT_SocialInterface roster and /gc commands. Rank rights remain on the DOL server.
const ACTIONS=["guild_open","guild_refresh","guild_member","guild_info","guild_motd","guild_leave"]
var character:=""
var guild:=""
var visible:=false
var tab:="guild"
var sort:=1
var page:=1
var show_offline:=false
var total:=0
var roster_ready:=false
var members:Array=[]
var generation:=0
var revision:=0
var token:=""
var pending:Dictionary={}
var feedback:=""
var refresh_at:=0
var last_request:=-100000
var requests:=0
var rejected:=0
var social_rejected:=0

func reset(keep_visible:bool=false)->void:
    generation+=1;revision+=1;roster_ready=false;members.clear();pending.clear();total=0;page=1;sort=1;tab="guild";show_offline=false;refresh_at=0;feedback=""
    if not keep_visible:visible=false
    token=JSON.stringify([generation,character,guild]).sha256_text()

func sync(server:Node,name:String,now:int)->void:
    var next_guild:=String(server.info.get("guild","")).strip_edges()
    if next_guild.to_lower()=="none":next_guild=""
    if not server.playing:next_guild=""
    if name!=character or next_guild!=guild:
        var same_character:bool=name==character
        character=name;guild=next_guild;reset(same_character and visible)
    if not server.playing:
        if visible or not members.is_empty():reset()
        return
    if not pending.is_empty() and now-int(pending.at)>4000:
        pending.clear();revision+=1;feedback="Guild roster response timed out. Refresh to try again."
    if visible and refresh_at>0 and now>=refresh_at:
        refresh_at=0;query(server,now)

func fail(text:String)->bool:
    feedback=text;rejected+=1;revision+=1;return false

func query(server:Node,now:int)->bool:
    if not visible or not server.playing or guild.is_empty():return fail("You are not in a guild.")
    if not pending.is_empty() or now-last_request<550:return fail("Wait for the server response.")
    roster_ready=false;members.clear();total=0
    pending={"at":now,"tab":tab,"page":page,"generation":generation,"header":false,"count":0,"seen":{}}
    last_request=now;feedback="Loading guild roster...";requests+=1;revision+=1
    server.command("/gc who window %d %d %d%s" % [sort,page,1 if show_offline else 0," 1" if tab=="alliance" else ""])
    return true

static func csv(text:String)->Array:
    if text.length()>4096:return []
    var fields:Array=[];var value:="";var quoted:=false;var i:=0
    while i<text.length():
        var ch:=text[i]
        if ch=='"':
            if quoted and i+1<text.length() and text[i+1]=='"':value+='"';i+=2;continue
            quoted=not quoted
        elif ch=="," and not quoted:
            fields.append(value);value=""
            if fields.size()>10:return []
        else:value+=ch
        i+=1
    if quoted:return []
    fields.append(value);return fields

static func valid_name(name:String)->bool:
    if name.is_empty() or name.length()>64:return false
    for ch in ["\r","\n","\t"," ","/","\\",'"',","]:
        if name.contains(ch):return false
    return true

func consume(kind:String,data:Dictionary,server:Node,now:int)->bool:
    if kind in ["you","quit"]:reset();return false
    if kind!="message" or int(data.get("type",-1))!=0x64:return false
    var f:=csv(String(data.get("text","")))
    if f.is_empty() or String(f[0]) not in ["TE","TA","E","A"]:return false
    if not visible or pending.is_empty() or int(pending.generation)!=generation:return true
    var alliance:bool=String(f[0]) in ["TA","A"]
    if ("alliance" if alliance else "guild")!=String(pending.tab):return true
    if String(f[0]) in ["TE","TA"]:
        if f.size()!=4 or not String(f[1]).is_valid_int() or not String(f[2]).is_valid_int() or not String(f[3]).is_valid_int():social_rejected+=1;return true
        var p:=int(f[1]);var n:=int(f[2]);var count:=int(f[3])
        if p!=int(pending.page) or n<0 or n>1000000 or count<0 or count>10 or count>maxi(0,n-(p-1)*10):social_rejected+=1;return true
        page=p;total=n;members.clear();pending.header=true;pending.count=count;pending.seen={};revision+=1
        if count==0:roster_ready=true;pending.clear();feedback="No alliance members found." if alliance else "No members found. Try Show Offline."
        return true
    if not bool(pending.header) or f.size()!=10:return true
    for i in [1,2,4,5,6,7]:
        if not String(f[i]).is_valid_int():social_rejected+=1;return true
    var pos:=int(f[1]);var rank:=int(f[6]);var group:=int(f[7]);var name:=String(f[3])
    if int(f[2])!=total or pos<(page-1)*10+1 or pos>(page-1)*10+int(pending.count) or int(f[4])<1 or int(f[4])>255 or int(f[5])<1 or int(f[5])>255 or rank<0 or rank>9 or group<0 or group>8 or not valid_name(name):social_rejected+=1;return true
    if pending.seen.has(pos):return true
    pending.seen[pos]=true
    var row:Dictionary={"position":pos,"name":name,"level":int(f[4]),"class_id":int(f[5]),"class_name":server.class_name_of(int(f[5])),"rank":rank,"group":group,"online":group>0,"zone":String(f[8]).left(256),"note":"","guild":""}
    if String(row.class_name).is_empty():row.class_name=String({51:"Magician",52:"Guardian",53:"Naturalist",54:"Stalker",57:"Forester"}.get(int(f[5]),"Class %d" % int(f[5])))
    row["guild" if alliance else "note"]=String(f[9]).left(512)
    row.token=JSON.stringify([generation,tab,pos,name,rank,group]).sha256_text();members.append(row);members.sort_custom(func(a,b):return int(a.position)<int(b.position));revision+=1
    if pending.seen.size()==int(pending.count):roster_ready=true;pending.clear();feedback=""
    return true

func member(row_token:String)->Dictionary:
    for row in members:
        if String(row.token)==row_token:return row
    return {}

func request(value:Dictionary,server:Node,now:int)->bool:
    var action:=String(value.get("action",""))
    if action not in ACTIONS:return false
    if not server.playing:return fail("Enter the world to use the guild window.")
    if action=="guild_open":
        visible=bool(value.get("open",true));revision+=1
        if not visible:pending.clear();refresh_at=0;return true
        if guild.is_empty():members.clear();total=0;feedback="You are not in a guild.";return true
        return query(server,now)
    if not visible or String(value.get("guild_token",""))!=token:return fail("Guild membership has changed.")
    if guild.is_empty():return fail("You are not in a guild.")
    if action=="guild_refresh":
        if not pending.is_empty() or now-last_request<550:return fail("Wait for the server response.")
        var next_tab:=String(value.get("tab",tab));var next_sort:=int(value.get("sort",sort));var next_page:=int(value.get("page",page))
        if next_tab not in ["guild","alliance"] or next_sort==0 or absi(next_sort)>8 or next_page<1 or next_page>100000:return fail("Invalid guild page or sort.")
        tab=next_tab;sort=next_sort;page=next_page;show_offline=bool(value.get("show_offline",show_offline));return query(server,now)
    if not pending.is_empty() or refresh_at>0:return fail("Wait for the server response.")
    var command:=""
    if action in ["guild_info","guild_motd"]:command="/gc info" if action=="guild_info" else "/gc motd"
    elif action=="guild_leave":
        if not bool(value.get("confirmed",false)):return fail("Confirm leaving the guild first.")
        command="/gc quit"
    elif action=="guild_member":
        if not roster_ready:return fail("Refresh the guild roster before acting on a member.")
        var row:=member(String(value.get("member_token","")));var verb:=String(value.get("verb",""))
        if row.is_empty() or not valid_name(String(row.name)):return fail("That member is no longer available.")
        if verb=="invite":command="/invite "+String(row.name)
        elif verb in ["promote","demote","remove"]:
            if tab!="guild":return fail("Guild rank actions are unavailable on the alliance tab.")
            if verb=="remove":
                if not bool(value.get("confirmed",false)):return fail("Confirm removing this member first.")
                command="/gc remove "+String(row.name)
            else:
                var rank:=int(row.rank)+(-1 if verb=="promote" else 1)
                if rank<0 or rank>9:return fail("That member cannot change rank any further.")
                command="/gc %s %s %d" % [verb,String(row.name),rank]
        else:return fail("Unsupported guild action.")
    if command.is_empty():return false
    server.command(command);requests+=1;revision+=1;feedback="Request sent to server."
    if action in ["guild_member","guild_leave"]:refresh_at=now+800
    return true

func snapshot()->Dictionary:
    return {"visible":visible,"revision":revision,"token":token,"guild":guild,"tab":tab,"sort":sort,"page":page,"show_offline":show_offline,"total":total,"stale":not roster_ready,"members":members.duplicate(true),"pending":not pending.is_empty() or refresh_at>0,"feedback":feedback}
