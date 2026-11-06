"""Verify merged catalogs and material isolation in a separate native host."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def verify(workspace, engine, installed=False, audio_candidate=False, combat_audio_candidate=False):
    lab = workspace/'ExpansionRaceLab'
    delivery = lab/'CentralDelivery'
    output = delivery/('NativeInstalledAcceptance' if installed else 'NativeAcceptance')
    output.mkdir(exist_ok=True)
    project = lab/'CentralDeliveryHost/CentralDeliveryHost.uproject'
    catalogs = {name: delivery/(name+'.json') for name in ['models', 'equipment', 'appearance', 'tasks', 'lore']}
    assert not(audio_candidate and combat_audio_candidate)
    if audio_candidate or combat_audio_candidate:
        assert not installed, 'Use the separate audio candidate host without overwriting installed proof hosts'
        audio_lab=workspace/('CombatAudioLab' if combat_audio_candidate else 'SpellAudioLab')
        build = json.loads((audio_lab/'native_build.json').read_text())
        assert build['passed'] and not build['normal_binary_modified']
        project = Path(build['project'])
        output = audio_lab/'CharacterRegression'
        output.mkdir(exist_ok=True)
        manifest = json.loads((delivery/'manifest.json').read_text())
        catalogs = {name: Path(row['target']) for name, row in manifest['catalogs'].items()}
        for name, sha in build['binaries_sha256'].items():
            assert hashlib.sha256((project.parent/'Plugins/DAoCVisualBridge/Binaries/Win64'/name).read_bytes()).hexdigest() == sha
    if installed:
        receipt = json.loads((delivery/'installed_client.json').read_text())
        assert receipt['installed'] and receipt['client_only'] and not receipt['normal_database_modified']
        manifest = json.loads((delivery/'manifest.json').read_text())
        catalogs = {name: Path(row['target']) for name, row in manifest['catalogs'].items()}
        host = lab/'CentralInstalledHost'
        plugin = host/'Plugins/DAoCVisualBridge'
        plugin.mkdir(parents=True, exist_ok=True)
        central = workspace/'Client/Plugins/DAoCVisualBridge'
        quote = lambda value: "'"+str(value).replace("'", "''")+"'"
        for target, source in [(host/'Content', workspace.parent/'DAoC-Enhanced-Unreal/Content'),
                               (plugin/'Content', central/'Content')]:
            if target.exists():
                assert target.is_junction() and target.resolve() == source.resolve()
            else:
                subprocess.run(['powershell.exe', '-NoProfile', '-Command',
                                'New-Item -ItemType Junction -Path '+quote(target)+' -Target '+quote(source)+' | Out-Null'],
                               check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        shutil.copy2(central/'DAoCVisualBridge.uplugin', plugin/'DAoCVisualBridge.uplugin')
        binary = plugin/'Binaries/Win64'
        binary.mkdir(parents=True, exist_ok=True)
        for name in ['UnrealEditor-DAoCVisualBridge.dll', 'UnrealEditor.modules']:
            shutil.copy2(central/'Binaries/Win64'/name, binary/name)
        project = host/'CentralInstalledHost.uproject'
        project.write_text(json.dumps({'FileVersion': 3, 'EngineAssociation': '5.8',
                                      'Plugins': [{'Name': 'DAoCVisualBridge', 'Enabled': True}]}), encoding='utf-8')
    dll = project.parent/'Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    read = lambda p: json.loads(p.read_bytes().decode('utf-16' if p.read_bytes()[:2] in [b'\xff\xfe', b'\xfe\xff'] else 'utf-8-sig'))
    inputs = list(catalogs.values())+[dll]
    hashes = {str(path): digest(path) for path in inputs}
    common = [str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'), str(project), '/Engine/Maps/Entry',
              '-game', '-EnablePlugins=DAoCVisualBridge', '-DaocBridge',
              '-DaocBridgeCatalog='+str(catalogs['models']),
              '-DaocBridgeEquipmentCatalog='+str(catalogs['equipment']),
              '-DaocBridgeLobbyAppearance='+str(catalogs['appearance']),
              '-DaocBridgeLobbyLore='+str(catalogs['lore']), '-unattended', '-nosound', '-nosplash']

    def run(name, flags):
        with (output/(name+'_stdout.log')).open('w', encoding='utf-8') as log:
            result = subprocess.run(common+flags+['-abslog='+str(output/(name+'_engine.log'))],
                                    stdout=log, stderr=subprocess.STDOUT, timeout=300,
                                    creationflags=subprocess.CREATE_NO_WINDOW)
        assert result.returncode == 0, ('Native host failed', name, result.returncode)

    native = output/'appearance.json'
    run('appearance', ['-DaocBridgeArmourTest='+str(native), '-DaocBridgeAppearanceTest', '-nullrhi'])
    appearance = read(native)
    known = ['world and frozen miniature publish actual facial render weights 1419']
    assert appearance['failures'] == known, ('Unexpected appearance/material failure', appearance['failures'])
    assert appearance['checks'] >= 4263 and not appearance['passed']
    print('appearance: existing source-empty horn limitation only; material checks passed', flush=True)
    # A partial figure override must independently inherit the central hair material.
    partial = copy.deepcopy(read(catalogs['appearance']))
    del partial['figures']['1419']['materials']['hair']
    partial_path = output/'partial_appearance.json'
    partial_path.write_text(json.dumps(partial), encoding='utf-8')
    partial_equipment = copy.deepcopy(read(catalogs['equipment']))
    partial_equipment['armour']['figures'] = {k: v for k, v in partial_equipment['armour']['figures'].items() if v['base_id'] == '1419'}
    partial_equipment_path = output/'partial_equipment.json'
    partial_equipment_path.write_text(json.dumps(partial_equipment), encoding='utf-8')
    # Replace the two catalog arguments for this isolated inheritance witness.
    original_common = list(common)
    common[:] = [arg for arg in common if not arg.startswith(('-DaocBridgeEquipmentCatalog=', '-DaocBridgeLobbyAppearance='))]
    common += ['-DaocBridgeEquipmentCatalog='+str(partial_equipment_path), '-DaocBridgeLobbyAppearance='+str(partial_path)]
    partial_native = output/'partial.json'
    run('partial', ['-DaocBridgeArmourTest='+str(partial_native), '-DaocBridgeAppearanceTest', '-nullrhi'])
    partial_report = read(partial_native)
    assert partial_report['failures'] == known
    common[:] = original_common
    screens = {}
    for screen in ['create', 'customize']:
        folder = output/screen
        folder.mkdir(exist_ok=True)
        fixture = folder/'fixture.json'
        shutil.copy2(lab/'CombinedExpansionLobbyAcceptance/fixture.json', fixture)
        run(screen, ['-DaocBridgeCharacterLobbyTest='+str(fixture),
                     '-DaocBridgeCharacterLobbyCapture='+str(folder/'screen.png'),
                     '-DaocBridgeCharacterLobbyScreen='+screen, '-d3d11', '-RenderOffscreen',
                     '-windowed', '-ForceRes', '-ResX=1600', '-ResY=900'])
        row = read(Path(str(fixture)+'.native.json'))
        assert row['passed'] and not row['failures']
        assert all(row[k] for k in ['minotaur_creation_tested', 'shar_creation_tested', 'shar_vampiir_creation_tested'])
        assert (folder/'screen.png').read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
        screens[screen] = row
        print(screen, 'passed', row['checks'], flush=True)
    assert hashes == {str(path): digest(path) for path in inputs}
    result = {'passed': True, 'normal_installation_modified': False, 'inputs': hashes,
              'installed_client_resources_only': installed,
              'audio_candidate': audio_candidate,
              'combat_audio_candidate': combat_audio_candidate,
              'native_appearance_checks': appearance['checks'], 'full_appearance_passed': False,
              'known_source_geometry_failure': known, 'material_isolation_passed': True,
              'partial_override_inherits_central_hair': True, 'lobby': screens,
              'screenshots_require_visual_review': True}
    (output/'verified.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--engine', type=Path, required=True)
    parser.add_argument('--installed', action='store_true')
    parser.add_argument('--audio-candidate', action='store_true')
    parser.add_argument('--combat-audio-candidate', action='store_true')
    args = parser.parse_args()
    verify(args.workspace.resolve(), args.engine.resolve(), args.installed, args.audio_candidate, args.combat_audio_candidate)
