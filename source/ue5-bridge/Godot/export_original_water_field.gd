extends SceneTree
func _initialize()->void:
    var input:="";var output:=""
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--water-input="):input=arg.trim_prefix("--water-input=")
        if arg.begins_with("--water-output="):output=arg.trim_prefix("--water-output=")
    assert(not input.is_empty() and not output.is_empty())
    var image:=Image.load_from_file(input)
    assert(image!=null and image.get_width()==256 and image.get_height()==256)
    var rows:Array=[]
    for y in 256:
        for x in 256:rows.append(roundi(image.get_pixel(x,y).r*255.0))
    var file:=FileAccess.open(output,FileAccess.WRITE);assert(file!=null)
    file.store_string(JSON.stringify({"passed":true,"width":256,"height":256,"mask":rows}));file.close();quit()
