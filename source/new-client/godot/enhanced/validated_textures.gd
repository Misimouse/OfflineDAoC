extends RefCounted
## Private, zone207-only approved atlas overlay. No source image or material spec is edited.
const ACTIVE="res://.enhanced-session/validated_zone207/active.json"
var approved:Dictionary={}

func _init(folders:Dictionary, initial_set:String) -> void:
	if OS.get_cmdline_user_args().has("--validated-textures-original"):return
	if not FileAccess.file_exists(ACTIVE):return
	var pointer=JSON.parse_string(FileAccess.get_file_as_string(ACTIVE))
	if not pointer is Dictionary or pointer.get("disabled",true):return
	var path=String(pointer.get("manifest",""))
	if path.is_empty() or FileAccess.get_sha256(path)!=pointer.get("sha256",""):return
	var manifest=JSON.parse_string(FileAccess.get_file_as_string(path))
	if not manifest is Dictionary or int(manifest.get("zone",-1))!=207:return
	if FileAccess.get_sha256("res://content/zones/zone207/zone.json")!=manifest.get("zone_sha256",""):return
	var expected=ProjectSettings.globalize_path("res://content/zones/zone207/textures/x4plus").replace("\\","/").trim_suffix("/")
	var given=ProjectSettings.globalize_path(String(folders.get("x4plus",""))).replace("\\","/").trim_suffix("/")
	if given!=expected:return
	var pending:Dictionary={}
	for item in manifest.get("textures",[]):
		var name=String(item.name)
		var image_path=String(item.path)
		if name!=name.get_file() or name.contains(".") or pending.has(name):return
		if FileAccess.get_sha256(image_path)!=item.get("sha256",""):return
		pending[name]=image_path
	if pending.size()!=int(manifest.get("texture_count",-1)):return
	approved=pending
	print("VALIDATED_TEXTURES zone=207 count=",approved.size()," originals_preserved=true")
