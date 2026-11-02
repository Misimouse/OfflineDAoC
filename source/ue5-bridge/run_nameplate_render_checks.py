from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json,subprocess,time,sys
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/nameplates';prefix=D/'render'
project=R/('Client/DAoCBridgeClient.uproject'if'--installed'in sys.argv else'ProfilingHost/BridgeHost.uproject')
start=time.time();cmd=[str(ENGINE / 'Binaries/Win64/UnrealEditor-Cmd.exe'),str(project),'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeNameplateRender='+str(prefix),'-d3d11','-windowed','-ResX=1280','-ResY=720','-unattended','-nosound','-nosplash']
with (D/'render.log').open('w')as log:p=subprocess.run(cmd,cwd=R,stdout=log,stderr=subprocess.STDOUT,timeout=180)
output=Path(str(prefix)+'.json');assert p.returncode==0 and output.stat().st_mtime>=start
x=json.loads(output.read_text(encoding='utf-8-sig'));print(json.dumps(x));assert x['passed']
for i in range(4):assert Path(str(prefix)+'-angle'+str(i)+'.png').stat().st_mtime>=start

# Guard against a render counter passing while the glyphs themselves are absent.
import sys
sys.path.insert(0,str(R.parent/'DAoC-Enhanced-Unreal/.terrain-python'))
from PIL import Image
pixel_results=[]
for i in range(4):
 pixels=Image.open(Path(str(prefix)+'-angle'+str(i)+'.png')).convert('RGB').get_flattened_data()
 counts={'red':0,'aqua':0,'white':0}
 for a,b,c in pixels:
  counts['red']+=int(a>90 and b<50 and c<50)
  counts['aqua']+=int(b>120 and c>100 and b>a+10)
  counts['white']+=int(min(a,b,c)>180 and max(a,b,c)-min(a,b,c)<15)
 assert min(counts.values())>10,(i,counts)
 pixel_results.append({'angle':i*90,**counts})
(D/'render_pixels.json').write_text(json.dumps({'passed':True,'angles':pixel_results},indent=2))
print('Actual friendly, selected and enemy glyphs detected in all four images.')
