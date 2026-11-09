"""Pin NPC appearance contracts against original Godot and the production DOL packet writer."""
import argparse,json
from pathlib import Path
from prepare_combined_expansion_data import digest

def audit(workspace,install):
 source=Path(__file__).resolve().parents[1];game=install/'new-client/godot/game';native=source/'UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private';server=source.parent/'server/GameServer'
 paths=[game/'npcs/npc.gd',game/'npcs/ghost_glow.gdshader',game/'net/server_world.gd',server/'packets/Server/PacketLib1124.cs',source/'Godot/decoded_world_adapter.gd',native/'DAoCBridgePersonalTorch.cpp'];text=[p.read_text(encoding='utf-8-sig') for p in paths]
 checks={'ghost_create_bit_01':'const FLAG_GHOST := 0x01' in text[0],'original_race_and_monster_ghost_paths':'ghost_look(model, model is Fig3Figure)' in text[0],'equipment_ghosted_too':'ghost_look(w as Node3D, _weapon_root is Fig3Figure)' in text[0],'monster_base_alpha_half':'uniform float ghost_alpha = 0.5;' in text[0],'race_figure_alpha_nine_tenths':'uniform float ghost_alpha = 0.9;' in text[0],'face_depth_pass':'depth.next_pass = look' in text[0],'subtle_white_rim':'uniform float strength = 0.05;' in text[1] and 'uniform float rim = 0.2;' in text[1],'original_normalized_torch_separate':'if f & 0x04: flags |= 0x40' in text[2],'original_normalized_stealth_separate':'if f2 & 0x04: flags |= 0x02' in text[2],'production_server_ghost':'GameNPC.eFlags.GHOST' in text[3],'production_server_torch':'GameNPC.eFlags.TORCH' in text[3],'native_personal_light_excludes_npcs':'if(Kind!=TEXT("player"))continue' in text[5]};assert all(checks.values()),checks
 result=dict(passed=True,audit_only=True,checks=checks,installed=False,normal_runtime_modified=False,source_inputs={str(p):digest(p) for p in paths},findings=['Installed NPC-create ghost0x01 has no native rendering contract yet; a separate candidate adapter object is tested but not installed.','Original torch flag is decoded/stored by Godot but no NPC torch renderer exists in the original NPC view; do not invent NPC map lights.','Ghost figure appearance differs from ordinary player stealth: separate material mapping and front-surface depth treatment needed.','Keep original equipment colors and textures; subtle white rim.'],next_step='Private original monster and race-figure render comparison; metadata must survive movement without mixing packet bits. No runtime installation before native material acceptance.')
 out=workspace/'NpcVisualFlagsLab';out.mkdir(exist_ok=True);(out/'audit.json').write_text(json.dumps(result,indent=2));return dict(passed=True,checks=len(checks),installed=False)
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for name in ['workspace','install']:p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();print(json.dumps(audit(a.workspace.resolve(),a.install.resolve())))
