"""Stage original per-player NPC quest flags in the private bridge."""
from pathlib import Path


def stage_markers(godot: Path, telemetry=False) -> None:
    def edit(name, pairs):
        path = godot / name
        code = path.read_text(encoding="utf-8-sig")
        for before, after in pairs:
            assert code.count(before) == 1, (name, before)
            code = code.replace(before, after, 1)
        path.write_text(code, encoding="utf-8")

    edit("decoded_world_adapter.gd", [
        ("func consume_world(kind: String, data: Dictionary) -> void:", '''# Mirrors ServerWorld._quest_indicator for 1.127 NPCCreate.
static func _quest_indicator(data: Dictionary) -> int:
    var flags2 := int(data.get("flags2", 0))
    var flags3 := int(data.get("flags3", 0))
    if flags2 & 0x08: return 1
    if flags2 & 0x10: return 2
    if flags3 & 0x01: return 4
    if flags3 & 0x02: return 8
    if flags3 & 0x20: return 16
    return 0

func consume_world(kind: String, data: Dictionary) -> void:'''),
        ('    if kind=="equipment":', '''    if kind == "visual_effect":
        if int(data.get("effect", -1)) != 7:
            return
        var indicator: int = int(data.get("value", -1))
        var row: Dictionary = entities.get(oid_to_id.get(oid, ""), {})
        if indicator in [0, 1, 2, 4, 8, 16] and row.get("kind", "") == "npc" and float(row.get("health", 0)) > 0:
            row["quest_indicator"] = indicator
        return
    if kind=="equipment":'''),
        ("            row.npc_visual=NPCVisualFlags.decode(data)", '''            row.npc_visual=NPCVisualFlags.decode(data)
            row["quest_indicator"] = _quest_indicator(data) if float(row.get("health", 0)) > 0 else 0'''),
        ("    row.targetable=false;row.show_name=false;row.combat_active=false", '''    row.targetable=false;row.show_name=false;row.combat_active=false
    row.erase("quest_indicator")'''),
        ('                row.state="dead";row.speed_mps=0.0;_motion_sample(row,{},"death")', '''                row.state="dead";row.speed_mps=0.0;_motion_sample(row,{},"death")
                row.erase("quest_indicator")'''),
        ('            row.health=0.0;row.state="dead";row.speed_mps=0.0', '''            row.health=0.0;row.state="dead";row.speed_mps=0.0
            row.erase("quest_indicator")'''),
    ])
    edit("live_gateway.gd", [
        ('"remove","region_changed","quit","model_change","death","revive","object","combat","equipment"]:adapter.consume_world',
         '"remove","region_changed","quit","model_change","death","revive","object","combat","equipment","visual_effect"]:adapter.consume_world'),
    ])
    if telemetry:
        edit("live_gateway.gd", [
            ("var quest_conversation_epoch:=0", "var quest_conversation_epoch:=0\nvar qa_marker_updates:Array=[]"),
            ("    if kind==\"quest_dialog\":", '''    if kind=="visual_effect" and int(data.get("effect",-1))==7:
        if qa_marker_updates.size()>=128:qa_marker_updates.pop_front()
        qa_marker_updates.append({"oid":int(data.get("oid",0)),"value":int(data.get("value",-1))})
    if kind=="quest_dialog":'''),
            ('        transport.snapshot_metadata["quest_rewards"]=quest_rewards.snapshot()', '''        transport.snapshot_metadata["qa_marker_updates"]=qa_marker_updates.duplicate(true)
        transport.snapshot_metadata["quest_rewards"]=quest_rewards.snapshot()'''),
        ])
        edit("visual_bridge.gd", [
            ('"player_trade","quest_rewards","exchange"', '"player_trade","quest_rewards","qa_marker_updates","exchange"'),
        ])
