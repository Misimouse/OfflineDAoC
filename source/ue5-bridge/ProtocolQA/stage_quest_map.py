"""Stage original projected quest step coordinates for the zone map."""
from pathlib import Path
import shutil


def stage_gateway(godot):
    path = godot / "live_gateway.gd"
    text = path.read_text(encoding="utf-8-sig")
    changes = [
        ("var entry_revision:=0", 'var entry_revision:=0\nvar quest_map_state = preload("quest_map_state.gd")'),
        ("    if entered or server.playing:return",
         "    if entered or server.playing:return\n    quest_map_state.reset(server)"),
        ('    world_event("quit",data)', '    world_event("quit",data)\n    quest_map_state.reset(server)'),
        ('        transport.snapshot_metadata["classic_ui"]=classic_ui.snapshot()',
         '        var classic_snapshot:Dictionary=classic_ui.snapshot()\n        classic_snapshot["quest_map_marks"]=quest_map_state.snapshot(server,leaving)\n        transport.snapshot_metadata["classic_ui"]=classic_snapshot'),
    ]
    for before, after in changes:
        assert text.count(before) == 1, before
        text = text.replace(before, after, 1)
    path.write_text(text, encoding="utf-8")
    source = Path(__file__).resolve().parents[1] / "Godot/quest_map_state.gd"
    shutil.copy2(source, godot / source.name)
