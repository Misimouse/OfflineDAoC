"""Seal private Minotaur UI and equipment evidence without activating a race."""
import argparse
import copy
import hashlib
import json
from pathlib import Path


def read(path):
    raw = path.read_bytes()
    return json.loads(raw.decode('utf-16' if raw[:2] in [b'\xff\xfe', b'\xfe\xff'] else 'utf-8-sig'))


def verify(lab):
    lab = lab.resolve()
    package = lab / 'MinotaurModularCandidate'
    folder = package / 'LobbyAcceptance'
    summary = read(folder / 'summary.json')
    assert set(summary) == {'create', 'customize'}
    for screen, result in summary.items():
        assert result['passed'] and result['exit'] == 0 and not result['failures']
        assert result['minotaur_creation_tested'] and not result['live_account']
        assert result['preview_model'] == 1419 and result['checks'] >= 70
        image = folder / screen / 'screen.png'
        assert image.read_bytes().startswith(b'\x89PNG\r\n\x1a\n') and image.stat().st_size > 10000
    figure = read(folder / 'appearance.json')['figures']['1419']
    original = read(package / 'appearance_catalog_candidate.json')['figures']['1419']
    assert summary['customize']['original_feature_geometry_missing']
    assert {'FM1', 'FM2'} <= set(original['parts']['head']['empty_source_morphs'])
    unchanged = copy.deepcopy(figure)
    palette = unchanged.pop('swatches')
    assert unchanged == original, 'Palette controls must not modify original materials or morphs'
    assert len(palette['eyes']) == len(palette['skin']) == 8
    assert len(palette['hair']) == len(figure['meta']['hair_styles']) == 10
    for index, style in enumerate(figure['meta']['hair_styles']):
        assert len(palette['hair'][str(index)]) == len(style['colours'])
    outfit = read(package / 'OutfitAcceptance/native.json')
    assert outfit['passed'] and not outfit['real_server'] and not outfit['failures'] and outfit['checks'] >= 35
    imported = read(package / 'native_outfit_import.json')
    assert imported['passed'] and not imported['installed'] and imported['races']['mino']['sections'] == 31
    inputs = [folder / name for name in ['models.json', 'equipment.json', 'appearance.json']]
    inputs += list((lab / 'SharLobbyHost/Plugins/DAoCVisualBridge/Binaries/Win64').glob('*.dll'))
    assert any(path.suffix == '.dll' for path in inputs)
    # Pin the private acceptance inputs so later edits invalidate this seal.
    recorded = read(folder / 'inputs.json')
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    assert recorded == {str(path): digest(path) for path in inputs}
    evidence = [folder / 'summary.json', package / 'OutfitAcceptance/native.json', package / 'native_outfit_import.json']
    report = {'passed': True, 'installed': False, 'activated': False,
              'native_ui_checks': sum(result['checks'] for result in summary.values()),
              'native_equipment_checks': outfit['checks'], 'inputs': recorded,
              'evidence': {str(path.relative_to(lab)): digest(path) for path in evidence},
              'original_horn_size_geometry_missing': True,
              'pending': ['Original Horn Size geometry (FM1/FM2 have zero source deltas)',
                          'Original helmets', 'Original trainer promotion', 'Live playable session and owner review']}
    (package / 'verified_lobby.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lab', type=Path, required=True)
    report = verify(parser.parse_args().lab)
    print(json.dumps({key: report[key] for key in ['passed', 'installed', 'native_ui_checks', 'native_equipment_checks']}))
