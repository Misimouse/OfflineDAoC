import json
import shutil
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
CLIENT=ROOT/'Client';CLIENT.mkdir(exist_ok=True)
source=ROOT.parent/'DAoC-Enhanced-Unreal'
project=json.loads((source/'DAoCEnhanced.uproject').read_text())
project['Description']='Isolated playable Connacht bridge; shared art is read-only at runtime.'
project['Plugins'].append(dict(Name='DAoCVisualBridge',Enabled=True))
(CLIENT/'DAoCBridgeClient.uproject').write_text(json.dumps(project,indent=2))
plugin=ROOT/'Build/DAoCVisualBridge'
destination=CLIENT/'Plugins/DAoCVisualBridge'
destination.mkdir(exist_ok=True,parents=True)
for name in ['DAoCVisualBridge.uplugin','Binaries','Resources']:
    item=plugin/name
    if item.is_dir():shutil.copytree(item,destination/name,dirs_exist_ok=True)
    elif item.exists():shutil.copy2(item,destination/name)
config=CLIENT/'Config';config.mkdir(exist_ok=True)
text=(source/'Config/DefaultEngine.ini').read_text()
# No editor startup scripts or experimental art command bridges in the playable client.
text='\n'.join(line for line in text.splitlines() if not line.startswith('+StartupScripts='))
destination_map=json.loads((ROOT/'bridge_config.json').read_text())['destination_map']
text=re.sub(r'(?m)^(EditorStartupMap|GameDefaultMap)=.*$',lambda match:match.group(1)+'='+destination_map,text)
(config/'DefaultEngine.ini').write_text(text)
(ROOT/'models.json').write_text('{}') if not (ROOT/'models.json').exists() else None
print('Native bridge client prepared; Content must be a junction to the art project.')
