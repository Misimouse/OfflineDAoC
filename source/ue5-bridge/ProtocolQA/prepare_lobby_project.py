"""Copy the installed gameplay scripts into a disposable headless QA project.

Content/import caches are shared for reading. Do not open this project in the
editor or import assets into it. No installed gameplay script is modified.
"""
from qa_runtime import *
import shutil,subprocess,sqlite3

with sqlite3.connect(DB) as db:
    assert db.execute('SELECT RunId FROM CodexQaIsolationMarker').fetchone()[0]==RUN.name
game=INSTALL/'new-client/godot';project=(RUN/'LobbyProject').resolve()
assert project.is_relative_to(RUN) and project!=game.resolve()
project.mkdir(exist_ok=True)
shutil.copytree(game/'game',project/'game',dirs_exist_ok=True)
for name in ['project.godot','icon.png']:
    if (game/name).exists():shutil.copy2(game/name,project/name)
cache=project/'.godot';cache.mkdir(exist_ok=True)
for name in ['global_script_class_cache.cfg','uid_cache.bin']:
    if (game/'.godot'/name).exists():shutil.copy2(game/'.godot'/name,cache/name)
shutil.copytree(game/'.godot/mono/temp/bin/Debug',cache/'mono/temp/bin/Debug',dirs_exist_ok=True)
for dest,target in [(project/'content',game/'content'),(cache/'imported',game/'.godot/imported')]:
    if dest.exists():
        assert dest.resolve()==target.resolve(),'QA cache points at an unexpected location'
    else:
        # Keep paths out of executable shell text, including paths containing quotes.
        link_env=dict(os.environ,DAOC_QA_LINK_DEST=str(dest),DAOC_QA_LINK_SOURCE=str(target))
        script='New-Item -ItemType Junction -Path $env:DAOC_QA_LINK_DEST -Target $env:DAOC_QA_LINK_SOURCE | Out-Null'
        subprocess.run(['powershell','-NoProfile','-Command',script],env=link_env,check=True,capture_output=True,text=True)
server=project/'game/net/server.gd';text=server.read_text(encoding='utf-8-sig')
old='\tif key == _asking or protocol_profile == "lab":\n'
new='\tif key == _asking or realm_id == int(REALM_IDS.get(_asking, -1)) or protocol_profile == "lab":\n'
if old in text:
    assert text.count(old)==1;text=text.replace(old,new)
else:
    assert new in text,'Review the original server realm queue before preparing QA'
if 'func character_list_pending()' not in text:
    anchor='func characters_in(realm: String) -> Array:';assert text.count(anchor)==1
    text=text.replace(anchor,'func character_list_pending() -> bool:\n\treturn _asking != "" or not _want.is_empty()\n\n\n'+anchor)
server.write_text(text,encoding='utf-8')
print('Isolated gameplay project prepared; installed scripts unchanged')
