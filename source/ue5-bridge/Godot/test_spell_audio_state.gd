extends SceneTree

func _initialize()->void:
    var state=load(get_script().resource_path.get_base_dir().path_join("spell_visual_state.gd")).new()
    state.reset(100)
    state.consume("cast",{"caster":1,"spell":4101,"time":30},1,{},4000)
    state.consume("spell_effect",{"caster":1,"target":1,"spell":4101,"success":1,"no_sound":1},1,{},5000)
    var events:Array=state.snapshot(5001)
    assert(events.size()==2 and events[1].no_sound==true)
    assert(events[1].effect_id==4101 and events[1].target=="player:local")
    state.consume("cast",{"caster":1,"spell":4101,"time":30},1,{},5100)
    state.consume("interrupt",{"caster":1},1,{},5200)
    assert(state.snapshot(5200).back().reason=="interrupt")
    state.consume("death",{"oid":1},1,{},5300)
    assert(state.snapshot(5300).back().reason=="death")
    state.consume("spell_effect",{"caster":1,"target":1,"spell":4301},1,{},5400)
    assert(state.snapshot(5400).back().no_sound==false)
    var serial:int=state.sequence
    state.consume("you",{},1,{},5500)
    assert(state.snapshot(5500).is_empty() and state.sequence==serial)
    state.consume("spell_effect",{"caster":1,"target":1,"spell":4301},1,{},5501)
    assert(state.snapshot(5501).is_empty()) # Restored login buffs do not sound.
    state.consume("spell_effect",{"caster":99,"target":1,"spell":4301},1,{},9000)
    assert(state.snapshot(9000).is_empty()) # Unknown caster is never invented.
    print("SPELL_AUDIO_STATE_PASS: quiet pulses, interrupt/death distinction, login suppression and original effect identity")
    quit()
