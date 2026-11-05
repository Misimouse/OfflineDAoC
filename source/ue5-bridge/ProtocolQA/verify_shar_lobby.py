"""Seal private Shar lobby acceptance against the exact catalogues and native library tested."""
import argparse
import hashlib
import json
from pathlib import Path


def verify(lab):
    lab = lab.resolve()
    folder = lab/'SharLobbyAcceptance'
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    inputs = json.loads((folder/'inputs.json').read_text(encoding='utf-8-sig'))
    assert inputs and all(digest(Path(path)) == expected for path, expected in inputs.items())
    assert {lab/'Delivery'/name for name in ['models.json', 'equipment.json', 'appearance.json', 'lore.json']} <= set(map(Path, inputs))
    assert any(Path(path).suffix.lower() == '.dll' for path in inputs)
    summary = json.loads((folder/'summary.json').read_text(encoding='utf-8-sig'))
    expected = {prefix+'_'+screen for prefix in ['sha_m', 'sha_f'] for screen in ['create', 'customize']}
    assert set(summary) == expected
    captures = {}
    for case, result in summary.items():
        assert result['passed'] and result['exit'] == 0 and result['checks'] >= 60 and not result['failures']
        assert result['shar_creation_tested'] and not result['live_account']
        assert result['preview_model'] == (1087 if case.startswith('sha_f') else 1075)
        assert result['preview_head_bone'] == 'Bip01-Head'
        image = folder/case/'screen.png'
        assert image.read_bytes().startswith(b'\x89PNG\r\n\x1a\n') and image.stat().st_size > 10000
        captures[case] = {'sha256':digest(image), 'path':str(image), 'checks':result['checks']}
    appearance = json.loads((lab/'Delivery/appearance.json').read_text(encoding='utf-8-sig'))
    for ident in ['1075', '1087']:
        figure = appearance['figures'][ident]
        assert len(figure['swatches']['eyes']) == len(figure['meta']['eyes']) == 8
        assert len({tuple(colour) for colour in figure['swatches']['eyes']}) == 8
        assert all(min(colour) < .8 for colour in figure['swatches']['eyes']), 'Eye pickers must not average the white face mask'
        for index, style in enumerate(figure['meta']['hair_styles']):
            assert len(figure['swatches']['hair'][str(index)]) == len(style['colours'])
    report = {'passed':True, 'installed':False, 'live_account':False, 'native_inputs':inputs,
              'cases':captures, 'summary_sha256':digest(folder/'summary.json'),
              'scope':'Private native UI acceptance. Captures require separate visual review; this does not activate Shar on the normal server.'}
    (folder/'verified.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lab', type=Path, required=True)
    report = verify(parser.parse_args().lab)
    print(json.dumps({'passed':report['passed'], 'cases':len(report['cases']), 'checks':sum(row['checks'] for row in report['cases'].values()), 'installed':False}))
