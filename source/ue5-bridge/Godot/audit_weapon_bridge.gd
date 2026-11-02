extends SceneTree
func _initialize()->void:
    var source:Script=load("res://game/weapon_models.gd")
    var data=JSON.parse_string(FileAccess.get_file_as_string("res://content/weapons/weapons.json"))
    var report:Dictionary={"passed":true,"checks":0,"families":{},"starter_models":{}}
    var families:Dictionary={2:"2h",3:"pole",4:"staff",5:"bow",6:"xbow",7:"1ht",8:"throw",9:"fws",10:"fwm",11:"fwl",13:"h2h",14:"scy"}
    for id in data.models:
        var info:Dictionary=data.models[id];var raw:=int(info.get("stance",1))
        if report.families.has(str(raw)):continue
        var actual:=String(source.call("stance",int(id)));var expected:=String(families.get(raw,""))
        report.checks+=1;report.passed=report.passed and actual==expected;report.families[str(raw)]={"example_model":int(id),"stance":actual,"expected":expected}
    for model in [445,59]:report.starter_models[str(model)]={"info":source.call("info",model),"stance":source.call("stance",model)}
    var out:String=get_script().resource_path.get_base_dir().path_join("../Reports/pose_animations/weapon_metadata_audit.json")
    var file:=FileAccess.open(out,FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close();print("WEAPON_METADATA checks=",report.checks," passed=",report.passed);quit(0 if report.passed else 1)
