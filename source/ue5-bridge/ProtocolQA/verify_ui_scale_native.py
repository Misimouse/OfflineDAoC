"""Verify original UI scale, actual slider geometry and a fresh-process reload."""
import argparse,json,shutil,subprocess
from datetime import datetime
from pathlib import Path
from central_activation_receipts import verify_files
from prepare_combined_expansion_data import digest

def verify(workspace,engine,installed=False,lab_name="UIScaleLab"):
    assert lab_name in ["UIScaleLab","WindowRecoveryLab","PlayerVitalsLab","CompassLab","WorldClockLab"]
    root=workspace/lab_name;bp=root/'native_build.json';build=json.loads(bp.read_text());assert build['passed']
    source=Path(__file__).resolve().parents[1]/'UnrealPlugin/DAoCVisualBridge/Source'
    assert all(digest(source/p)==h for p,h in build['source_sha256'].items())
    if installed:assert verify_files(workspace)['window_recovery_installed' if lab_name=='WindowRecoveryLab' else 'ui_scale_installed']
    normal=workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    expected=build['binaries_sha256'][normal.name] if installed else build['normal_binary_sha256'];assert digest(normal)==expected
    out=root/('InstalledScaleAcceptance' if installed else 'ScaleAcceptance')/datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True)
    fixture=out/'fixture.json';shutil.copy2(workspace/'Reports/vault/fixture.json',fixture);settings=out/'interface.ini';reports={}
    project=str(workspace/'Client/DAoCBridgeClient.uproject') if installed else build['project']
    for name,scale in [('first',1),('restart',1.35)]:
        report=out/(name+'.json')
        args=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),project,'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeReadOnly','-DaocBridgeInterfaceScaleTest='+str(report),'-DaocBridgeInterfaceSettings='+str(settings),'-DaocBridgeExpectedInterfaceScale='+str(scale),'-DaocBridgeUIScaleFixture='+str(fixture),'-DaocBridgeDisplaySettings='+str(out/'display.ini'),'-DaocBridgeControlsSettings='+str(out/'camera.json'),'-DaocBridgeKeyConfiguration='+str(out/'keys.ini'),'-DaocBridgeAudioSettings='+str(out/'audio.ini'),'-nosound','-unattended','-nosplash','-d3d11','-RenderOffscreen','-windowed','-ResX=1280','-ResY=720','-abslog='+str(out/(name+'.log'))]
        with (out/(name+'.stdout.log')).open('w') as log:r=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=360,creationflags=subprocess.CREATE_NO_WINDOW)
        assert r.returncode==0 and report.exists(),str(out)
        value=json.loads(report.read_text(encoding='utf-8-sig'));assert value['passed'] and not value['failures'] and value['checks']>=218,value
        reports[name]=value
    assert digest(normal)==expected and all(digest(source/p)==h for p,h in build['source_sha256'].items())
    result=dict(passed=True,checks=sum(v['checks'] for v in reports.values()),reports=reports,build_receipt_sha256=digest(bp),normal_installation_modified=False,server_started=False)
    (out/'verified.json').write_text(json.dumps(result,indent=2));(root/('installed_scale_acceptance.json' if installed else 'scale_acceptance.json')).write_text(json.dumps(dict(passed=True,proof=str(out/'verified.json'),proof_sha256=digest(out/'verified.json')),indent=2))
    return dict(passed=True,checks=result['checks'],output=str(out))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--engine',type=Path,required=True);p.add_argument('--installed',action='store_true');a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.engine.resolve(),a.installed)))
