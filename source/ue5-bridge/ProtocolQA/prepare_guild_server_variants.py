"""Synchronize the existing offline guild view after authorized saved changes only."""
import hashlib,json
from pathlib import Path

def variants(server_source,output):
    changes={};name='GameServer/gameutils/GuildMgr.cs';raw=(server_source/name).read_text(encoding='utf-8-sig')
    anchor='        public static Dictionary<string, GuildMemberView> GetGuildMemberViews(Guild guild)'
    assert raw.count(anchor)==1
    method='        /// <summary>Refresh the social roster only after a guild command saved an offline character.</summary>\n        public static void SynchronizeOfflineGuildMember(Guild guild, DbCoreCharacter character)\n        {\n            if (guild == null || character == null)\n                return;\n            lock (_lock)\n            {\n                if (!_guildMemberViews.TryGetValue(guild, out Dictionary<string, GuildMemberView> members))\n                    return;\n                if (character.GuildID != guild.GuildID)\n                {\n                    members.Remove(character.ObjectId);\n                    return;\n                }\n                if (members.TryGetValue(character.ObjectId, out GuildMemberView member))\n                {\n                    member.Rank = character.GuildRank.ToString();\n                    member.Note = character.GuildNote;\n                }\n            }\n        }\n\n'
    raw=raw.replace(anchor,method+anchor)
    # Offline alliance rows need the actual guild name, just like online/bot rows.
    anchor='                    character.GuildNote,\n                    null);';assert raw.count(anchor)==1
    changes[name]=raw.replace(anchor,'                    character.GuildNote,\n                    guild.Name);')
    name='GameServer/commands/playercommands/guild.cs';raw=(server_source/name).read_text(encoding='utf-8-sig')
    anchor='GameServer.Database.SaveObject(ch);';assert raw.count(anchor)==4
    changes[name]=raw.replace(anchor,anchor+'\n                            GuildMgr.SynchronizeOfflineGuildMember(client.Player.Guild, ch);')
    result={}
    for name,text in changes.items():
        p=output/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8')
        result[name]=dict(path=str(p),original_sha256=hashlib.sha256((server_source/name).read_bytes()).hexdigest(),candidate_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),scope='Server-authoritative offline roster cache synchronization; no permission or gameplay-rule changes.')
    return dict(passed=True,files=result)
