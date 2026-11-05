"""Check converted helmet geometry/skin/UVs without Unreal or a live account."""
import argparse,hashlib,json,math,struct
from pathlib import Path

def inspect(row):
    data=Path(row['file']).read_bytes()
    assert data[:4]==b'glTF' and struct.unpack_from('<I',data,8)[0]==len(data)
    size=struct.unpack_from('<I',data,12)[0];doc=json.loads(data[20:20+size])
    offset=20+size;binary=data[offset+8:offset+8+struct.unpack_from('<I',data,offset)[0]]
    assert len(doc['meshes'])==1 and len(doc['skins'])==1,'Expected one original skeleton assembly'
    formats={5120:('b',1),5121:('B',1),5122:('h',2),5123:('H',2),5125:('I',4),5126:('f',4)}
    widths={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}
    def values(index):
        accessor=doc['accessors'][index];view=doc['bufferViews'][accessor['bufferView']]
        char,width=formats[accessor['componentType']];count=widths[accessor['type']]
        stride=view.get('byteStride',width*count);start=view.get('byteOffset',0)+accessor.get('byteOffset',0)
        return [struct.unpack_from('<'+char*count,binary,start+n*stride) for n in range(accessor['count'])]
    vertices=0;materials=[];joints=len(doc['skins'][0]['joints'])
    for primitive in doc['meshes'][0]['primitives']:
        attr=primitive['attributes'];p=values(attr['POSITION']);uv=values(attr['TEXCOORD_0']);bones=values(attr['JOINTS_0']);weights=values(attr['WEIGHTS_0'])
        assert len(p)==len(uv)==len(bones)==len(weights) and p
        assert all(math.isfinite(v) for xyz in p+uv for v in xyz)
        assert all(0<=bone<joints for indices in bones for bone in indices)
        assert all(abs(sum(w)-1)<.002 for w in weights)
        assert all(0<=v[0]<len(p) for v in values(primitive['indices']))
        materials.append(doc['materials'][primitive['material']]['name']);vertices+=len(p)
    assert sorted(materials)==sorted(section['material'] for section in row['sections'])
    return vertices

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory',type=Path);parser.add_argument('--expected',type=int,default=540);args=parser.parse_args()
    rows=json.loads((args.directory/'exported.json').read_text(encoding='utf-8-sig'));assert len(rows)==args.expected
    vertices=0;keys=set();sources={}
    for row in rows:
        key=(row['race'],row['model']);assert key not in keys;keys.add(key)
        path=Path(row['file']).resolve();assert path.is_relative_to(args.directory.resolve())
        before=hashlib.sha256(path.read_bytes()).hexdigest();vertices+=inspect(row)
        assert hashlib.sha256(path.read_bytes()).hexdigest()==before
        sources[row['race']+'/'+str(row['model'])]=before
    report={'passed':True,'assemblies':len(rows),'races':len({row['race'] for row in rows}),'vertices':vertices,'real_server':False,
            'manifest_sha256':hashlib.sha256((args.directory/'exported.json').read_bytes()).hexdigest(),'source_sha256':sources}
    (args.directory/'verified.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='source_sha256'}))

if __name__=='__main__':main()
