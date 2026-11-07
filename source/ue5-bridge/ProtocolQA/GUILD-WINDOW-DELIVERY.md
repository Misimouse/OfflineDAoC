# Original guild window migration

The bridge now carries the original DOL social roster into Unreal: GUILD and ALLIANCE tabs, ten rows per page, sorting, offline members, rank/group/zone columns and notes or guild names. Shift+G opens the window; it is editable alongside the other controls. Existing saved controls retain priority if they already use that new shortcut. Labels and the original frame/radio artwork remain in English.

Actions use the original server commands. Send prepares a private-message draft; it never sends a message automatically. Invite is a group invitation. Promote/demote derive the requested rank from the current roster. Remove and Leave require confirmation; DOL additionally retains its original leave dialog. The client never invents a changed rank, removal or membership. Character changes, logout, stale snapshots and delayed responses cannot reuse old member selections.

## Server correction found during integration

The real disposable-server test exposed a pre-existing DOL cache problem: authorized rank changes or removal of an offline character were saved, but the social roster kept the old cached entry. `prepare_guild_server_variants.py` adds cache synchronization after the four existing offline-character save sites. It also supplies the actual guild name to offline alliance rows. Permission checks and gameplay rules remain unchanged. The separate build keeps the already-delivered Vampiir and Hibernian Minotaur source variants and canonical GM overlay. No world or player database is migrated.

DOL can return no roster packet for an account without an alliance. The bounded request times out with feedback, clears old rows and permits refreshing or returning to GUILD; the client does not label an unreceived response as a successful empty roster. Requests also respect DOL's guild-command throttle.

## Validation and installation

Evidence stays under `GuildWindowLab` in the local workspace. It includes the headless state and gateway tests, actual Unreal window/input/confirmation checks, real DOL roster and saved mutation checks against a marked disposable database, and regression checks for controls, display settings, movement, jump, tracking, water and audio. Failed trial evidence is retained separately. Automated tests do not replace the owner's gameplay review.

The installer accepts only the exact verified source/build hashes and the predecessor display receipt. It backs up the client and server files, refuses occupied normal ports, verifies every replacement and supports bounded rollback. The original radio artwork is byte-copied only into a new private content directory. Played databases, original client art and accounts are never published.

## Completed evidence

Installed after 54 state checks, 10 gateway checks, 33 native checks, 12 real administrator checks and five real restricted-member checks. The final native artifact also passed 257 controls, 47 display, 53 movement, nine jump, 35 tracking, 65,559 water-data checks and the established 265 audio/UI checks. All 33 installed-window checks passed using the installed artwork path. The 104 synthetic receipt checks reject tampered client/server/artwork/predecessor files. Owner gameplay review remains pending. The installation replaced 23 bounded files with backups and preserved the played database.

## Owner review

Use the same normal OfflineDAoC server launcher and `INICIAR-ARDEE-GM.cmd`. In world, use Shift+G (or its assigned control). Check the empty state without a guild, and if a guild is available, tabs, Show Offline, sorting, pages and selection. Send must only open a draft; Cancel must leave membership unchanged. Administrative actions must be approved or denied by the actual server. The normal server needs the installed cache correction on its next start.

Emblem editing, guild-creation automation and world population import are separate packages. This delivery does not claim full client migration is complete.
