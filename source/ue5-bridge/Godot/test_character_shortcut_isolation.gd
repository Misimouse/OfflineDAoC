extends SceneTree
var checks:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func _initialize()->void:
    var model=load("res://classic_ui_state.gd").new()
    model.open_character("Private Old Character","user://character_shortcuts")
    var old:Dictionary=model.register_macro("OLD","/loc")
    model.banks=[2,3,4];model.bars[2][4][9]=old.duplicate(true);model.save()
    var old_path:String=model.storage_path()
    model.open_character("Private New Character",model.save_folder)
    check(model.banks==[0,0,0],"new character starts with default pages rather than preceding character pages")
    check(model.macros.is_empty() and model.entries.is_empty(),"new character cannot inherit preceding macro catalogue")
    check(model.resolve(old.id,old.token).is_empty(),"old character macro token does not resolve for new character")
    check(model.bars[2][4][9].is_empty(),"preceding character shortcut is absent from new character")
    check(model.storage_path()!=old_path,"characters have separate shortcut save paths")
    var fresh:Dictionary=model.register_macro("NEW","/help")
    model.banks=[5,6,7];model.bars[0][5][0]=fresh.duplicate(true);model.save()
    model.open_character("Private Old Character",model.save_folder)
    check(model.banks==[2,3,4],"existing character restores its own saved pages")
    check(model.bars[2][4][9].get("name")=="OLD","existing character restores its own shortcut")
    check(model.resolve(fresh.id,fresh.token).is_empty(),"new character macro is not exposed in original catalogue")
    check(model.bars[0][5][0].is_empty(),"new character shortcut cannot overwrite original character slot")
    model.open_character("Private New Character",model.save_folder)
    check(model.banks==[5,6,7] and model.bars[0][5][0].get("name")=="NEW","returning new character restores its saved pages and shortcut")
    model.banks[0]=8;model.open_character("Private New Character",model.save_folder)
    check(model.banks[0]==8,"refreshing the same open character preserves current working page")
    model.open_character("Private Third Character",model.save_folder)
    check(model.banks==[0,0,0],"another fresh character also gets default pages")
    check(model.macros.is_empty() and model.bars[0][5][0].is_empty(),"another fresh character has no previous shortcuts")
    print(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures,"real_server":false}));quit(0 if failures.is_empty() else 1)
