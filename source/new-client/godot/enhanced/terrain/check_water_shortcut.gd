extends "res://enhanced/terrain/preview_water_trial.gd"
func _initialize() -> void:call_deferred("check_shortcut")
func check_shortcut() -> void:
	await run()
	assert(trial.bindings.size()==1 and trial.mode==2)
	var key:=InputEventKey.new()
	key.pressed=true;key.ctrl_pressed=true;key.alt_pressed=true;key.keycode=KEY_U;key.physical_keycode=KEY_U
	for expected in [0,1,2]:
		trial._input(key)
		assert(trial.mode==expected)
	key.ctrl_pressed=false;key.keycode=KEY_F9;key.physical_keycode=KEY_F9
	trial._input(key)
	assert(trial.mode==2)
	print("WATER_SHORTCUT_OK ctrl_alt_u_cycles=3 alt_f9_unused=true")
	trial.restore()
	await process_frame
	quit()
