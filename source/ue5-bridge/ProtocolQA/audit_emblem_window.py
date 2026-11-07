"""Read the original emblem UI, packet authority and already imported artwork."""
import argparse,json
from pathlib import Path
from prepare_combined_expansion_data import digest

def audit(workspace,install):
    source=Path(__file__).resolve().parents[1];repo=source.parents[1];game=install/'new-client/godot'
    refs=[game/'game/ui/emblem_window.gd',game/'game/emblems.gd',game/'game/net/server_world.gd',
      repo/'source/new-client/godot/game/net/DaocClient.cs',repo/'source/server/GameServer/packets/Client/168/EmblemDialogReponseHandler.cs',
      repo/'source/server/GameServer/gameutils/GuildMgr.cs',repo/'source/server/GameServer/commands/playercommands/guild.cs',
      source/'UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeEquipment.cpp',
      game/'content/emblems/emblems.json',game/'content/ui/classic/x4plus/emblempick.png',workspace/'equipment_catalog_v01.json']
    assert all(p.exists() for p in refs)
    palette=json.loads(refs[-3].read_text());equipment=json.loads(refs[-1].read_text());emblems=equipment['emblems']
    assert len(palette['primary'])==16 and len(palette['secondary'])==8 and len(palette['masks'])==4
    assert sorted(map(int,palette['logos']))==list(range(1,256)) and len(emblems['patterns'])==513 and len(emblems['logos'])==255
    assert equipment['models']['60']['info']['emblem']=='sh_metal01'
    report=dict(passed=True,phase='original_contract_audit',runtime_implemented=False,normal_installation_modified=False,database_modified=False,
      original_ui=dict(size=[219,288],preview_shield=60,logo_columns=8,controls=['PATTERN','FIELD','CHARGE','LOGO','SET EMBLEM','CANCEL']),
      source_options=dict(primary=16,secondary=8,patterns=4,logos=255),
      packet=dict(server_event='emblem_dialog',id='0xE2',response='EmblemChoice(primary,secondary,pattern,logo)',bytes=4,
        encoding='logo<<9 | pattern<<7 | primary<<3 | secondary',opens_only_after_server_event=True),
      authority=['guild leader permission remains on DOL','first choice requires a selected EmblemNPC','redo requires original server confirmation and sufficient funds before picker opens','duplicate emblems remain rejected by DOL','applying an emblem to an item is a separate NPC item trade'],
      current_emblem_source='Original client reads worn cloak slot 26, then shield slot 11; otherwise starts from zero.',
      acknowledgement='The original choice packet has no dedicated acceptance reply. Submission must never fabricate changed equipment or claim a successful purchase.',
      reusable_assets=dict(shield=equipment['models']['60']['asset'],material=emblems['material'],patterns=513,logos=255),
      excluded=['new emblem artwork','new guild permissions','new prices','world emblemer spawns','optimistic inventory changes'],
      input_hashes={str(p):digest(p) for p in refs})
    root=workspace/'EmblemWindowLab';root.mkdir(exist_ok=True);(root/'reference_audit.json').write_text(json.dumps(report,indent=2));return dict(passed=True,output=str(root/'reference_audit.json'),reused_logos=255)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--install',type=Path,required=True);a=p.parse_args();print(json.dumps(audit(a.workspace.resolve(),a.install.resolve())))
