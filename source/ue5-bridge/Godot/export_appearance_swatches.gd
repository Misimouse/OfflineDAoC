extends SceneTree
## Reuse the original menu's texture sampling for its colour buttons.
func _initialize()->void:run.call_deferred()
func rgb(values:Array)->Array:
    var out:Array=[]
    for c in values:out.append([c.r,c.g,c.b])
    return out
func run()->void:
    var input:="";var output:=""
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--catalog="):input=arg.trim_prefix("--catalog=")
        if arg.begins_with("--output="):output=arg.trim_prefix("--output=")
    assert(not input.is_empty() and not output.is_empty() and input!=output)
    var catalog:Dictionary=JSON.parse_string(FileAccess.get_file_as_string(input))
    var menu=load("res://game/pregame.gd").new()
    for key in catalog.figures:
        var row:Dictionary=catalog.figures[key]
        var figure=load("res://game/fig3_figure.gd").new();root.add_child(figure)
        assert(figure.load_figure(String(row.race)))
        menu._figure=figure
        menu.draft={"look":figure.look}
        var palette:Dictionary={"eyes":rgb(menu._eye_colours()),"skin":rgb(menu._skin_colours()),"hair":{}}
        for i in (figure.meta.get("hair_styles",[]) as Array).size():
            figure.look["hair"]=i;palette.hair[str(i)]=rgb(menu._hair_colours())
            assert(palette.hair[str(i)].size()==figure.meta.hair_styles[i].colours.size())
        assert(palette.eyes.size()==figure.meta.get("eyes",[]).size() and palette.skin.size()==figure.meta.get("skin_tones",[]).size())
        row["swatches"]=palette
        menu._figure=null;figure.free();await process_frame
    menu.free()
    var file:=FileAccess.open(output,FileAccess.WRITE);file.store_string(JSON.stringify(catalog));file.close()
    print("APPEARANCE_SWATCHES_PASS figures=",catalog.figures.size());quit()
