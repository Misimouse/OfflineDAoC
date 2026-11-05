"""Complete private Shar palette controls from the already exported original textures."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageStat


def prepare(catalog, textures, workspace, output):
    catalog, textures, workspace, output = (p.resolve() for p in (catalog, textures, workspace, output))
    assert output.is_relative_to(workspace) and output != catalog
    source = json.loads(catalog.read_text(encoding='utf-8-sig'))
    result = copy.deepcopy(source)
    files = {p.stem.lower(): p for p in textures.glob('*.png')}
    evidence = {}
    def colour(name):
        path = files[name.lower()]
        evidence[name.lower()] = hashlib.sha256(path.read_bytes()).hexdigest()
        with Image.open(path) as image:
            image = image.convert('RGB')
            # Eye maps place a tiny iris in a mostly white colour mask; use
            # coloured pixels rather than averaging the surrounding face mask.
            if name.lower().startswith('eyecolor_'):
                pixels = [rgb for rgb in image.getdata() if max(rgb)-min(rgb)>24 and min(rgb)<180]
                if not pixels:
                    pixels = [rgb for rgb in image.getdata() if max(rgb)<180]
                assert pixels, ('Missing iris colour', name)
                return [sum(rgb[i] for rgb in pixels)/(255*len(pixels)) for i in range(3)]
            return [v/255 for v in ImageStat.Stat(image).mean]
    for ident in ['1075', '1087']:
        figure = result['figures'][ident]
        meta = figure['meta']
        palette = figure.setdefault('swatches', {})
        palette['eyes'] = [colour(name) for name in meta['eyes']]
        palette['hair'] = {}
        for index, style in enumerate(meta['hair_styles']):
            palette['hair'][str(index)] = [[v*t for v,t in zip(colour(row['tex']), row['tint'])] for row in style['colours']]
        assert len(palette['eyes']) == 8
        # Only picker display colours change; original materials, textures and morphs stay intact.
        check = copy.deepcopy(figure); check['swatches'] = source['figures'][ident]['swatches']
        assert check == source['figures'][ident]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    receipt = {'passed': True, 'installed': False, 'source_sha256': hashlib.sha256(catalog.read_bytes()).hexdigest(),
               'candidate_sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'original_textures': evidence,
               'scope': 'Shar eye and hair picker swatches only; no rendered colour or existing race edits.'}
    output.with_suffix('.source.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ['catalog', 'textures', 'workspace', 'output']:
        parser.add_argument('--'+key, type=Path, required=True)
    args = parser.parse_args()
    report = prepare(args.catalog, args.textures, args.workspace, args.output)
    print(json.dumps({'passed': report['passed'], 'original_textures': len(report['original_textures']), 'installed': False}))
