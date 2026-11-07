"""Restart the candidate with saved resolution despite launcher's conflicting dimensions."""
import argparse,json,subprocess,struct
from datetime import datetime
from pathlib import Path
from prepare_combined_expansion_data import digest
from verify_options_audio_native import read

def image_size(path):
    data=path.read_bytes()
    if data.startswith(b'\x89PNG'):return struct.unpack('>II',data[16:24])
    assert data.startswith(b'\xff\xd8');i=2
    while i<len(data):
        assert data[i]==255;i+=1
        while data[i]==255:i+=1
        marker=data[i];i+=1
        if marker in [0xd8,0xd9] or 0xd0<=marker<=0xd7:continue
        n=struct.unpack('>H',data[i:i+2])[0]
        if marker in [0xc0,0xc1,0xc2]:
            height,width=struct.unpack('>HH',data[i+3:i+7]);return width,height
        i+=n
    raise AssertionError('No image dimensions')

def verify(workspace,engine):
    root=workspace/'DisplaySettingsFixLab';bp=root/'native_build.json';build=read(bp);normal=workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll';assert digest(normal)==build['normal_binary_sha256']
    out=root/'StartupAcceptance'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True)
    settings=out/'display.ini';settings.write_text('[Display]\nVersion=1\nWidth=960\nHeight=540\nMode=2\nFrameCap=60\n',encoding='utf-8');saved=digest(settings)
    reports=[]
    for restart in range(2):
        run=out/str(restart);run.mkdir();report=run/'controls.json';camera=run/'camera.json';camera.write_text(json.dumps({'mouse_sensitivity':.25,'invert_mouse':False,'preserved_test_field':'retained'}))
        args=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),build['project'],'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeReadOnly',
          '-DaocBridgeKeyConfigurationTest='+str(report),'-DaocBridgeDisplaySettings='+str(settings),'-DaocBridgeKeyConfiguration='+str(run/'keys.ini'),'-DaocBridgeControlsSettings='+str(camera),'-DaocBridgeAudioSettings='+str(run/'audio.ini'),
          '-nosound','-unattended','-nosplash','-d3d11','-RenderOffscreen','-windowed','-ResX=1280','-ResY=720','-abslog='+str(run/'engine.log')]
        with (run/'stdout.log').open('w',encoding='utf-8') as log:r=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
        assert r.returncode==0 and report.exists(),str(run);data=read(report);assert data['passed'] and not data['failures']
        shot=Path(str(report)+'.png');size=image_size(shot);assert size==(960,540),(size,str(run))
        assert digest(settings)==saved and digest(normal)==build['normal_binary_sha256']
        reports.append(dict(passed=True,restart=restart+1,viewport_size=size,controls_checks=data['checks'],saved_preferences_unchanged=True))
    proof=dict(passed=True,reports=reports,build_receipt_sha256=digest(bp),saved_settings_sha256=saved,normal_installation_modified=False,server_started=False)
    (out/'verified.json').write_text(json.dumps(proof,indent=2));return dict(passed=True,restarts=2,viewport_size=[960,540],output=str(out))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--engine',type=Path,required=True);a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.engine.resolve())))
