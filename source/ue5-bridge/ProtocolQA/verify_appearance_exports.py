"""Validate exported original appearance geometry, morph deltas, UVs, skinning and PNG dimensions."""
from pathlib import Path
import json,struct,math
import argparse
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source',type=Path);parser.add_argument('--report',type=Path);parser.add_argument('--expected-figures',type=int,default=10);args=parser.parse_args()
source=json.loads((args.source/'exported.json').read_text());assert source['complete'] and len(source['races'])==args.expected_figures and not source['missing_textures']
parts=morphs=vertices=0
for race,row in source['races'].items():
    assert 'head' in row['parts'] and row['meta']['prefix']==race
    for name,part in row['parts'].items():
        raw=Path(part['file']).read_bytes();assert raw[:4]==b'glTF' and struct.unpack_from('<II',raw,4)==(2,len(raw));size=struct.unpack_from('<I',raw,12)[0];gltf=json.loads(raw[20:20+size]);assert len(gltf['meshes'])==1 and len(gltf['skins'])==1,(race,name)
        mesh=gltf['meshes'][0];actual=mesh.get('extras',{}).get('targetNames',[]);assert set(actual)==set(part['morphs']),(race,name,actual,part['morphs'])
        offset=20+size;binary=raw[offset+8:offset+8+struct.unpack_from('<I',raw,offset)[0]]
        def values(index):
            accessor=gltf['accessors'][index]
            formats={5120:('b',1),5121:('B',1),5122:('h',2),5123:('H',2),5125:('I',4),5126:('f',4)}
            char,width=formats[accessor['componentType']]
            components={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[accessor['type']]
            def read(view_id,offset,count,fmt,n,width):
                view=gltf['bufferViews'][view_id];stride=view.get('byteStride',width*n);start=view.get('byteOffset',0)+offset
                assert view.get('buffer',0)==0
                return [struct.unpack_from('<'+fmt*n,binary,start+i*stride) for i in range(count)]
            result=read(accessor['bufferView'],accessor.get('byteOffset',0),accessor['count'],char,components,width) if 'bufferView' in accessor else [tuple(0 for _ in range(components)) for _ in range(accessor['count'])]
            if 'sparse' in accessor:
                sparse=accessor['sparse'];indices=sparse['indices'];data=sparse['values'];ic,iw=formats[indices['componentType']]
                changed=read(indices['bufferView'],indices.get('byteOffset',0),sparse['count'],ic,1,iw)
                replacements=read(data['bufferView'],data.get('byteOffset',0),sparse['count'],char,components,width)
                assert len(set(i[0] for i in changed))==len(changed)
                for at,value in zip(changed,replacements):
                    assert 0<=at[0]<len(result);result[at[0]]=value
            return result
        for primitive in mesh['primitives']:
            count=gltf['accessors'][primitive['attributes']['POSITION']]['count']
            assert len(primitive.get('targets',[]))==len(actual)
            for target in primitive.get('targets',[]):
                for accessor in target.values():
                    assert gltf['accessors'][accessor]['count']==count
                    assert all(math.isfinite(v) for delta in values(accessor) for v in delta)
            attrs=primitive['attributes'];positions=values(attrs['POSITION']);uv=values(attrs['TEXCOORD_0']);bones=values(attrs['JOINTS_0']);weights=values(attrs['WEIGHTS_0'])
            assert len(positions)==len(uv)==len(bones)==len(weights)==count
            assert all(math.isfinite(v) for xyz in positions+uv for v in xyz)
            assert all(0<=b<len(gltf['skins'][0]['joints']) for indices in bones for b in indices)
            assert all(abs(sum(w)-1)<.002 and all(0<=v<=1.0001 for v in w) for w in weights)
            assert all(0<=index[0]<count for index in values(primitive['indices']))
            vertices+=count
        parts+=1;morphs+=len(actual)
for name,texture in source['textures'].items():
    data=Path(texture['file']).read_bytes();assert data[:8]==b'\x89PNG\r\n\x1a\n';assert struct.unpack_from('>II',data,16)==(texture['width'],texture['height'])
result={'passed':True,'races':len(source['races']),'parts':parts,'morph_targets':morphs,'vertices':vertices,'textures':len(source['textures']),'installed':False}
if args.report:
    args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
