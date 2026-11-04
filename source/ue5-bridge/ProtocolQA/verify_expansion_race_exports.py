"""Verify original expansion figure exports before any native asset import."""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path


def verify(folder, report_path):
    folder = folder.resolve()
    tasks = json.loads((folder / 'tasks.json').read_text())
    exported = json.loads((folder / 'exported.json').read_text())
    assert len(tasks) == len(exported) == 3
    expected = {str(row['id']): row for row in tasks}
    report = {'passed': False, 'installed': False, 'models': {}}
    for row in exported:
        ident = str(row['id'])
        task = expected.pop(ident)
        path = Path(row['file']).resolve()
        assert path.is_relative_to(folder)
        raw = path.read_bytes()
        assert raw[:4] == b'glTF' and struct.unpack_from('<II', raw, 4) == (2, len(raw))
        size = struct.unpack_from('<I', raw, 12)[0]
        data = json.loads(raw[20:20+size])
        start = 20+size
        binary = raw[start+8:start+8+struct.unpack_from('<I', raw, start)[0]]
        assert len(data['skins']) == 1
        skin = data['skins'][0]
        assert len(skin['joints']) > 20
        def values(index):
            accessor = data['accessors'][index]
            assert 'sparse' not in accessor
            formats = {5121: ('B', 1), 5123: ('H', 2), 5125: ('I', 4), 5126: ('f', 4)}
            char, width = formats[accessor['componentType']]
            count = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}[accessor['type']]
            view = data['bufferViews'][accessor['bufferView']]
            offset = view.get('byteOffset', 0)+accessor.get('byteOffset', 0)
            stride = view.get('byteStride', count*width)
            assert offset+(accessor['count']-1)*stride+count*width <= len(binary)
            result = [struct.unpack_from('<'+char*count, binary, offset+i*stride) for i in range(accessor['count'])]
            assert all(math.isfinite(x) for value in result for x in value)
            return result
        triangles = vertices = 0
        for mesh in data['meshes']:
            for primitive in mesh['primitives']:
                attrs = primitive['attributes']
                positions, weights, joints = (values(attrs[name]) for name in ['POSITION', 'WEIGHTS_0', 'JOINTS_0'])
                assert len(positions) == len(weights) == len(joints)
                assert all(abs(sum(v)-1) < .002 for v in weights)
                assert all(0 <= j < len(skin['joints']) for v in joints for j in v)
                assert len(values(attrs['TEXCOORD_0'])) == len(positions)
                indices = values(primitive['indices'])
                assert len(indices) % 3 == 0 and all(0 <= i[0] < len(positions) for i in indices)
                triangles += len(indices)//3
                vertices += len(positions)
        clips = {animation['name'] for animation in data['animations']}
        original = set(task['info']['clip_seconds'])
        aliases = task['info'].get('cast_clips', {})
        represented = {target for alias, target in aliases.items() if alias in clips}
        assert original <= clips | represented, (ident, sorted(original-clips-represented))
        for animation in data['animations']:
            for sampler in animation['samplers']:
                times = values(sampler['input'])
                assert times and all(a[0] <= b[0] for a, b in zip(times, times[1:]))
                values(sampler['output'])
        assert triangles > 0 and vertices > 0
        report['models'][ident] = {'sha256': hashlib.sha256(raw).hexdigest(), 'original_clips': len(original),
                                  'exported_clips': len(clips), 'source_cast_names_represented_by_aliases': sorted(original-clips), 'vertices': vertices, 'triangles': triangles,
                                  'joints': len(skin['joints']), 'creation_accepted': False}
    assert not expected
    report['passed'] = True
    report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.folder, args.report)))
