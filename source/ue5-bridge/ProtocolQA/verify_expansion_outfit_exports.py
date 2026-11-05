"""Verify original Shar clothing/cloak exports against their original bind skeletons."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from densify_appearance_morphs import read_glb, accessor_bytes


def values(document, binary, index):
    accessor = document['accessors'][index]
    count = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}[accessor['type']]
    kind = {5121: 'B', 5123: 'H', 5125: 'I', 5126: 'f'}[accessor['componentType']]
    result = list(struct.iter_unpack('<' + kind * count, accessor_bytes(document, binary, index)))
    assert len(result) == accessor['count'] and all(math.isfinite(x) for row in result for x in row)
    return result


def verify(lab, game, output):
    lab, game, output = lab.resolve(), game.resolve(), output.resolve()
    assert output.is_relative_to(lab) and not lab.is_relative_to(game)
    rows = json.loads((lab / 'SourceCosmetics/exported.json').read_text(encoding='utf-8-sig'))
    original = json.loads((lab / 'SourceFigures/exported.json').read_text(encoding='utf-8-sig'))
    assert {row['race'] for row in rows} == {'sha_m', 'sha_f'} and len(rows) == 2
    report = {'passed': False, 'installed': False, 'races': {}, 'scope': 'Outfit topology, variants, weights, cloak UV channels and bind skeleton only; not native rendering or race activation.'}
    for row in rows:
        race = row['race']
        assert str(row['base_id']) == {'sha_m': '1075', 'sha_f': '1087'}[race]
        file = Path(row['file']).resolve()
        assert file.is_relative_to(lab / 'SourceCosmetics')
        document, binary = read_glb(file)
        source_row = next(r for r in original if str(r['id']) == str(row['base_id']))
        source_file = Path(source_row['file']).resolve()
        assert source_file.is_relative_to(lab / 'SourceFigures')
        source, source_binary = read_glb(source_file)
        assert len(document['skins']) == len(source['skins']) == 1
        skin, source_skin = document['skins'][0], source['skins'][0]
        names = [document['nodes'][i]['name'] for i in skin['joints']]
        assert names == [source['nodes'][i]['name'] for i in source_skin['joints']]
        matrices = values(document, binary, skin['inverseBindMatrices'])
        original_matrices = values(source, source_binary, source_skin['inverseBindMatrices'])
        assert len(matrices) == len(original_matrices)
        assert all(abs(a - b) < .00001 for matrix, before in zip(matrices, original_matrices) for a, b in zip(matrix, before)), 'Original bind transforms changed'
        meta_path = game / 'content/characters/races' / race / 'figure.json'
        metadata = json.loads(meta_path.read_text(encoding='utf-8-sig'))
        assert row['clothes'] == metadata['clothes'] and row['variants'] == metadata['variants'] and row['cloaks'] == metadata['cloaks']
        sections = {r['material']: r for r in row['sections']}
        assert len(sections) == len(row['sections'])
        seen = set()
        vertices = triangles = 0
        cloak_channels = {}
        for mesh in document['meshes']:
            for primitive in mesh['primitives']:
                name = document['materials'][primitive['material']]['name']
                assert name in sections and name not in seen
                seen.add(name)
                attributes = primitive['attributes']
                positions, weights, joints = (values(document, binary, attributes[k]) for k in ['POSITION', 'WEIGHTS_0', 'JOINTS_0'])
                assert len(positions) == len(weights) == len(joints)
                assert all(abs(sum(w) - 1) < .002 for w in weights)
                assert all(0 <= j < len(names) for row_j in joints for j in row_j)
                indices = values(document, binary, primitive['indices'])
                assert len(indices) % 3 == 0 and all(0 <= i[0] < len(positions) for i in indices)
                for key in ['NORMAL', 'TANGENT', 'TEXCOORD_0']:
                    assert len(values(document, binary, attributes[key])) == len(positions)
                if sections[name]['cosmetic']:
                    assert not sections[name]['default_visible']
                    for key in ['TEXCOORD_1', 'TEXCOORD_2']:
                        assert len(values(document, binary, attributes[key])) == len(positions)
                    cloak_channels[sections[name]['part']] = ['TEXCOORD_0', 'TEXCOORD_1', 'TEXCOORD_2']
                vertices += len(positions)
                triangles += len(indices) // 3
        assert seen == sections.keys()
        for slot, variants in metadata['variants'].items():
            actual = {int(s['variant']) for s in sections.values() if s['modular'] and s['slot'] == slot}
            assert actual == {int(v) for v in variants}, (race, slot, actual, variants)
        assert set(cloak_channels) == {'cloak_' + str(int(v)) for v in metadata['cloaks']}
        report['races'][race] = {'id': row['base_id'], 'sha256': hashlib.sha256(file.read_bytes()).hexdigest(), 'source_figure_sha256': hashlib.sha256(source_file.read_bytes()).hexdigest(),
                                  'source_metadata_sha256': hashlib.sha256(meta_path.read_bytes()).hexdigest(), 'sections': len(sections), 'joints': len(names), 'vertices': vertices, 'triangles': triangles,
                                  'bind_transforms_preserved': True, 'original_variants_preserved': True, 'cloak_uv_channels': cloak_channels}
    report['passed'] = True
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['lab', 'game', 'output']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.lab, args.game, args.output)))
