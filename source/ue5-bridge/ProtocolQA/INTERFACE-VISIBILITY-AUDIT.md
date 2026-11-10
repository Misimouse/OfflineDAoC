# Original interface visibility: bounded delivery

The original game_ui.gd hides its UI root with Toggle Interface or hard-coded Alt+Z. The bridge has nineteen separate game overlay roots, so hiding one panel would leave chat, services and other windows drawn and clickable.

This bounded candidate adds an editable Alt+Z default in the existing Controls page. It temporarily collapses existing game roots, retaining their individual visibility and widget instances. Windows created by later snapshots are included. Showing restores prior visibility, including roots that were already hidden or collapsed. Window positions, open flags, server requests and saved character/interface files are unaffected. Options and character menus stay available; character exit clears transient hiding. Opening chat restores visibility to avoid invisible typing. This editable dispatch does not claim the original additional hard-coded alias after rebinding or complete original presets.

Native acceptance exercises actual controller input, restoration, continued server-window creation, options/chat/disconnected gates, rebinding and previous controls. Candidate proof, installed proof and owner gameplay review must remain distinct. No new game UI, transport command, server rule, database content, map or art resources are added.

Candidate acceptance passes463 native checks, including previous weapon, keyboard-turning, group, ground-object and private-reply controls. The15-file exact predecessor delivery passes55 simulated chain checks. Two startup attempts timed out while another character-project build held shared Unreal tools; neither changed the normal runtime. The first semantic verifier incorrectly assumed all visible Slate widgets use the same hit-test visibility enum; the check was corrected to accept their original visible modes, without changing gameplay behavior.

All463 checks also pass against the installed normal client. Exact predecessor verification and rollback preview pass. Owner gameplay review remains pending; no server or WORK resources were changed.
