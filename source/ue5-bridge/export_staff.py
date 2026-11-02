from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import os,subprocess,json,struct
from pathlib import Path
R=Path(__file__).resolve().parent;I=Path(str(INSTALL));D=R/'Reports/equipment';D.mkdir(exist_ok=True)
env=dict(os.environ,DOTNET_ROOT=str(ENGINE / 'Binaries/ThirdParty/DotNet/10.0/win-x64'),DOTNET_ROOT_X64=str(ENGINE / 'Binaries/ThirdParty/DotNet/10.0/win-x64'),APPDATA=str(D/'offline-save'))
with(D/'staff_export.log').open('w')as log:
 p=subprocess.run([str(I/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64.exe'),'--headless','--path',str(I/'new-client/godot'),'--script',str(R/'Godot/export_staff.gd')],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
text=(D/'staff_export.log').read_text(errors='replace');assert p.returncode==0 and 'STARTER_WEAPONS_PASS'in text and 'ERROR:'not in text,text[-2000:]
data=json.loads((R/'SourceWeapons_v02/exported.json').read_text());assert data['complete']
for row in data['models']:
 raw=Path(row['file']).read_bytes();assert raw[:4]==b'glTF'and struct.unpack_from('<I',raw,8)[0]==len(raw)
 gltf=json.loads(raw[20:20+struct.unpack_from('<I',raw,12)[0]]);assert gltf.get('meshes')and all(m.get('primitives')for m in gltf['meshes'])
print([(m['model'],m['vertices'])for m in data['models']])
