"""Capture a real figure with the candidate personal source off, day-scaled and night-scaled."""
import argparse,json,subprocess
from pathlib import Path
from datetime import datetime
from prepare_combined_expansion_data import digest
from verify_stealth_render_native import png_rgb

def verify(workspace,engine):
 lab=workspace/'PersonalTorchLab';bp=lab/'native_build.json';build=json.loads(bp.read_text());assert build['passed'];out=lab/'VisualAcceptance'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True)
 proof=next(p for p in reversed(sorted((lab/'RealProtocol').glob('*/verified.json'))) if json.loads(p.read_text())['passed']);fixture=proof.parent/'active_snapshot.json'
 normal=workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll';assert digest(normal)==build['normal_binary_sha256']
 args=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),build['project'],'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeReadOnly','-DaocBridgeCatalog='+str(workspace/'models.json'),'-DaocBridgePersonalTorchVisual='+str(out),'-DaocBridgePersonalTorchFixture='+str(fixture),'-d3d11','-RenderOffscreen','-windowed','-ResX=800','-ResY=600','-unattended','-nosound','-nosplash','-abslog='+str(out/'render.log')]
 for k,v in [('ControlsSettings','camera.json'),('KeyConfiguration','keys.ini'),('DisplaySettings','display.ini'),('InterfaceSettings','interface.ini'),('AudioSettings','audio.ini')]:args+=['-DaocBridge'+k+'='+str(out/v)]
 with (out/'stdout.log').open('w') as log:result=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
 assert result.returncode==0
 images={n:png_rgb(out/(n+'.png')) for n in ['off','day','night']};assert len({v[0] for v in images.values()})==1
 measure={n:dict(mean=sum(v[1])/len(v[1]),peak=max(v[1])) for n,v in images.items()}
 assert measure['off']['mean']<.01 and measure['day']['mean']>.1 and measure['night']['mean']>measure['day']['mean']*2 and measure['night']['peak']<250,measure
 assert digest(normal)==build['normal_binary_sha256']
 data=dict(passed=True,rendered_private_character=True,owner_gameplay_accepted=False,world_map_modified=False,measurements=measure,build_sha256=digest(bp),source_inputs={str(p):digest(p) for p in [fixture,workspace/'models.json']},images={str(out/(n+'.png')):digest(out/(n+'.png')) for n in images});(out/'verified.json').write_text(json.dumps(data,indent=2));return dict(passed=True,output=str(out),measurements=measure)
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for name in ['workspace','engine']:p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.engine.resolve())))
