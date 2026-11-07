"""Read-only guild migration contract from original Godot and local DOL sources."""
import argparse,json
from pathlib import Path
from prepare_combined_expansion_data import digest

def audit(workspace,install):
    source=Path(__file__).resolve().parents[1];repo=source.parents[1];game=install/'new-client/godot/game'
    refs=[game/'ui/guild_window.gd',game/'ui/classic_window.gd',game/'net/server_world.gd',game/'net/server.gd',repo/'source/server/GameServer/commands/playercommands/guild.cs',source/'Godot/live_gateway.gd',source/'Godot/visual_bridge.gd']
    assert all(p.exists() for p in refs)
    report=dict(passed=True,phase='reference_audit_only',runtime_implemented=False,original_ui='GuildWindow: GUILD/ALLIANCE, ten rows per page, original classic framing',
      data_contract=dict(packet_chat_type='CT_SocialInterface 0x64',headers=['TE','TA'],members=['E','A'],fields=['kind','position','total','name','level','class_id','rank','group_size','zone_or_last_on','note_or_guild']),
      requests=['/gc who window <sort> <page> <show_offline> [1 for alliance]','/gc info','/gc motd'],
      original_member_actions=['send','group invite','promote','demote','remove','leave guild'],original_shortcut='Shift+G',
      destructive_actions_require_original_confirmation=['remove member','leave guild'],
      headless_transport='Server.world emits message events; chat_state already skips social payloads; guild state must consume those payloads before snapshot publication',
      authority='DOL server checks rank permissions; bridge must not emulate rank rules or perform direct guild DB updates',
      invariants=['original CSV quoting preserves commas in note/name fields','guild and alliance responses stay separated','bounded pages and sorting','clear stale roster on character change/logout','no duplicate social payloads in ordinary chat'],
      excluded=['guild emblem editing','guild creation automation','world population import','new guild rules'],
      input_hashes={str(p):digest(p) for p in refs},normal_installation_modified=False,database_modified=False)
    root=workspace/'GuildWindowLab';root.mkdir(exist_ok=True);(root/'reference_audit.json').write_text(json.dumps(report,indent=2));return dict(passed=True,phase='reference_audit_only',output=str(root/'reference_audit.json'))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--install',type=Path,required=True);a=p.parse_args();print(json.dumps(audit(a.workspace,a.install)))
