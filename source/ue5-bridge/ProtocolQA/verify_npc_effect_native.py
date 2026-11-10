"""Exercise original persistent NPC effects and existing spell/gameplay contracts privately."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import shutil
import subprocess
from prepare_combined_expansion_data import digest


def verify(workspace,engine,installed=False):
    lab = workspace/'NpcEffectsLab'
    build_path = lab/'native_build.json'
    build = json.loads(build_path.read_text())
    source = Path(__file__).resolve().parents[1]/'UnrealPlugin/DAoCVisualBridge/Source'
    assert build['passed'] and all(digest(source/p) == sha for p,sha in build['source_sha256'].items())
    normal = workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    assert digest(normal) == (build['binaries_sha256'][normal.name] if installed else build['normal_binary_sha256'])
    catalog = workspace/'models.json' if installed else lab/'models_candidate.json'
    assert digest(catalog) == json.loads((lab/'catalog_verified.json').read_text())['sha256']
    out = lab/('InstalledNativeAcceptance' if installed else 'NativeAcceptance')/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    out.mkdir(parents=True)
    cases = [('npc',None,'DaocBridgeNpcEffectsTest','',31),
             ('spell',None,'DaocBridgeSpellVisualAcceptance','',20),
             ('ghost',None,'DaocBridgeNpcGhostMaterialsTest','',48),
             ('torch',None,'DaocBridgePersonalTorchTest','',19),
             ('pose',None,'DaocBridgePoseTest','',55),
             ('combat',workspace/'Reports/combat_visual/fixture.json','DaocBridgeCombatVisualTest','.native.json',25),
             ('motion',workspace/'Reports/movement/server_trace.json','DaocBridgeMotionTest','.motion-results.json',387)]
    reports = []
    for name,original,flag,suffix,minimum in cases:
        fixture = out/(name+'.json')
        if original:
            shutil.copy2(original,fixture)
        args = [str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),(str(workspace/'Client/DAoCBridgeClient.uproject') if installed else build['project']),
                '/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeReadOnly',
                '-DaocBridgeCatalog='+str(catalog),'-'+flag+'='+str(fixture),
                '-unattended','-nosound','-nosplash','-abslog='+str(out/(name+'.log'))]
        if name == 'ghost':
            args += ['-DaocBridgeNpcGhostMaterials='+str(workspace/'NpcVisualFlagsLab/npc_ghost_materials.json'),
                     '-DaocBridgeNpcGhostSamples='+str(workspace/'NpcVisualFlagsLab/samples_imported.json')]
        args += ['-DaocBridgeRemotePlayerTest','-d3d11','-RenderOffscreen','-windowed','-ResX=1280','-ResY=720'] if name == 'pose' else ['-nullrhi']
        for key,filename in [('DisplaySettings','display.ini'),('InterfaceSettings','interface.ini'),
                             ('KeyConfiguration','keys.ini'),('ControlsSettings','camera.json'),('AudioSettings','audio.ini')]:
            args.append('-DaocBridge'+key+'='+str(out/filename))
        with (out/(name+'_stdout.log')).open('w') as log:
            process = subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=180,
                                     creationflags=subprocess.CREATE_NO_WINDOW)
        report = Path(str(fixture)+suffix)
        assert process.returncode == 0 and report.is_file(),str(out)
        data = json.loads(report.read_text(encoding='utf-8-sig'))
        assert data['passed'] and data['checks'] >= minimum,data
        reports.append(dict(name=name,checks=data['checks'],report=str(report),sha256=digest(report)))
    assert digest(normal) == (build['binaries_sha256'][normal.name] if installed else build['normal_binary_sha256'])
    result = dict(passed=True,installed=installed,real_server=False,reports=reports,
                  build_sha256=digest(build_path),normal_binary_unchanged=True,
                  catalog_sha256=digest(catalog),owner_gameplay_accepted=False)
    (out/'verified.json').write_text(json.dumps(result,indent=2))
    return dict(passed=True,output=str(out),reports=reports)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--engine',type=Path,required=True)
    parser.add_argument('--installed',action='store_true')
    options = parser.parse_args()
    print(json.dumps(verify(options.workspace.resolve(),options.engine.resolve(),options.installed)))
