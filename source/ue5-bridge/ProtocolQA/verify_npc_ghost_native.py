"""Exercise actor-local ghost materials in a private native client, plus movement/combat regressions."""
import argparse
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from prepare_combined_expansion_data import digest


def verify(workspace, engine, materials=None, installed=False):
    lab = workspace/'NpcVisualFlagsLab'
    materials = materials or (workspace/'Client/Plugins/DAoCVisualBridge/Content/ClassicUI/npc_ghost_materials.json' if installed else lab/'MaterialsCandidate/prepared.json')
    material_sha = digest(materials)
    build_path = lab/'native_build.json'
    build = json.loads(build_path.read_text())
    assert build['passed']
    normal = workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    expected_normal = build['binaries_sha256'][normal.name] if installed else build['normal_binary_sha256']
    assert digest(normal) == expected_normal
    if installed:
        assert json.loads((lab/'installed.json').read_text())['installed']
    source = Path(__file__).resolve().parents[1]/'UnrealPlugin/DAoCVisualBridge/Source'
    assert all(digest(source/path) == sha for path, sha in build['source_sha256'].items())
    project = workspace/'Client/DAoCBridgeClient.uproject' if installed else Path(build['project'])
    binary = project.parent/'Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    assert digest(binary) == build['binaries_sha256'][binary.name]
    out = lab/('InstalledNativeAcceptance' if installed else 'NativeAcceptance')/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    out.mkdir(parents=True)
    reports = []
    cases = [('ghost', None, 'DaocBridgeNpcGhostMaterialsTest', '', 48),
             ('torch', None, 'DaocBridgePersonalTorchTest', '', 19),
             ('pose', None, 'DaocBridgePoseTest', '', 55),
             ('combat', workspace/'Reports/combat_visual/fixture.json', 'DaocBridgeCombatVisualTest', '.native.json', 25),
             ('motion', workspace/'Reports/movement/server_trace.json', 'DaocBridgeMotionTest', '.motion-results.json', 387)]
    for name, original, flag, suffix, minimum in cases:
        fixture = out/(name+'.json')
        if original:
            shutil.copy2(original, fixture)
        args = [str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'), str(project),
                '/Engine/Maps/Entry', '-game', '-DaocBridge', '-DaocBridgeReadOnly',
                '-DaocBridgeCatalog='+str(workspace/'models.json'), '-'+flag+'='+str(fixture),
                '-unattended', '-nosound', '-nosplash', '-abslog='+str(out/(name+'.log'))]
        if name == 'ghost':
            args += ['-DaocBridgeNpcGhostMaterials='+str(materials),
                     '-DaocBridgeNpcGhostSamples='+str(lab/'samples_imported.json')]
        args += ['-DaocBridgeRemotePlayerTest', '-d3d11', '-RenderOffscreen', '-windowed',
                 '-ResX=1280', '-ResY=720'] if name == 'pose' else ['-nullrhi']
        for key, filename in [('DisplaySettings', 'display.ini'), ('InterfaceSettings', 'interface.ini'),
                              ('KeyConfiguration', 'keys.ini'), ('ControlsSettings', 'camera.json'),
                              ('AudioSettings', 'audio.ini')]:
            args.append('-DaocBridge'+key+'='+str(out/filename))
        with (out/(name+'_stdout.log')).open('w') as log:
            process = subprocess.run(args, stdout=log, stderr=subprocess.STDOUT,
                                     timeout=180, creationflags=subprocess.CREATE_NO_WINDOW)
        report = Path(str(fixture)+suffix)
        assert process.returncode == 0 and report.is_file(), str(out)
        data = json.loads(report.read_text(encoding='utf-8-sig'))
        assert data['passed'] and data['checks'] >= minimum, data
        reports.append(dict(name=name, report=str(report), sha256=digest(report), checks=data['checks']))
    assert digest(normal) == expected_normal and digest(materials) == material_sha
    result = dict(passed=True, installed=installed, real_server=False, reports=reports,
                  material_manifest=str(materials), material_sha256=material_sha,
                  build_sha256=digest(build_path), normal_binary_unchanged=True,
                  owner_gameplay_accepted=False)
    (out/'verified.json').write_text(json.dumps(result, indent=2))
    return dict(passed=True, output=str(out), reports=reports)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--engine', type=Path, required=True)
    parser.add_argument('--materials', type=Path)
    parser.add_argument('--installed', action='store_true')
    options = parser.parse_args()
    print(json.dumps(verify(options.workspace.resolve(), options.engine.resolve(), options.materials, options.installed)))
