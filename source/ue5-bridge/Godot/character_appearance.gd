extends RefCounted
## Original figure options, validated before the original server API sees a look.
const KEYS=["face","eyes","skin","hair","hair_color","tattoo","size","sliders"]
var metadata:Dictionary={}
func normalise(value:Variant,prefix:String,trusted_saved:=false)->Dictionary:
    if not value is Dictionary:return {"ok":false,"error":"Invalid character appearance."}
    for key in value:
        if not key in KEYS and not trusted_saved:return {"ok":false,"error":"Unknown appearance option."}
    if not prefix in ["cel_m","cel_f","elf_m","elf_f","fir_m","fir_f","lur_m","lur_f","syl_m","syl_f","sha_m","sha_f"]:return {"ok":false,"error":"Appearance is unavailable for this race."}
    if not metadata.has(prefix):
        var path:="res://content/characters/races/"+prefix+"/figure.json"
        var parsed:Variant=JSON.parse_string(FileAccess.get_file_as_string(path)) if FileAccess.file_exists(path) else null
        if not parsed is Dictionary:return {"ok":false,"error":"Original appearance data is missing."}
        metadata[prefix]=parsed
    var meta:Dictionary=metadata[prefix]
    var look:Dictionary={}
    var fields:Dictionary={"face":"faces","eyes":"eyes","skin":"skin_tones","hair":"hair_styles","tattoo":"tattoos"}
    for key in ["face","eyes","skin","hair","hair_color","tattoo","size"]:
        var chosen:Variant=value.get(key,1 if key=="size" else 0)
        if not (chosen is int or chosen is float) or not is_finite(float(chosen)) or float(chosen)!=floor(float(chosen)):
            if not trusted_saved:return {"ok":false,"error":"Invalid appearance option."}
            chosen=1 if key=="size" else 0
        var count:int=3 if key=="size" else 0
        if fields.has(key):count=(meta.get(fields[key],[]) as Array).size()
        if key=="hair_color":
            var styles:Array=meta.get("hair_styles",[])
            if not styles.is_empty():count=(styles[look.get("hair",0)].get("colours",[]) as Array).size()
        if trusted_saved:chosen=clampi(int(chosen),0,maxi(1,count)-1)
        if int(chosen)<0 or int(chosen)>=maxi(1,count):return {"ok":false,"error":"Appearance option is outside this race's choices."}
        look[key]=int(chosen)
    var sliders:Variant=value.get("sliders",[])
    if not sliders is Array:
        if not trusted_saved:return {"ok":false,"error":"Invalid facial features."}
        sliders=[]
    if not trusted_saved and sliders.size()>(meta.get("sliders",[]) as Array).size():return {"ok":false,"error":"Invalid facial features."}
    look["sliders"]=[]
    for i in (meta.get("sliders",[]) as Array).size():
        var v:Variant=sliders[i] if i<sliders.size() else 4
        if trusted_saved:
            v=clampi(int(v),0,8) if (v is int or v is float) and is_finite(float(v)) else 4
        if not (v is int or v is float) or not is_finite(float(v)) or float(v)!=floor(float(v)) or float(v)<0 or float(v)>8:return {"ok":false,"error":"Facial features must be between 0 and 8."}
        look.sliders.append(int(v))
    return {"ok":true,"look":look}
