from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
from pathlib import Path
import json,struct,base64,collections
R=Path(__file__).resolve().parent
G=Path(str(INSTALL / 'new-client/godot/content/weapons'))
def load(p):
    if p.suffix=='.glb':
        b=p.read_bytes();n=struct.unpack_from('<I',b,12)[0]
        return json.loads(b[20:20+n]),b[28+n:]
    d=json.loads(p.read_text());uri=d['buffers'][0]['uri']
    return d,base64.b64decode(uri.split(',',1)[1]) if uri.startswith('data:') else (p.parent/uri).read_bytes()
def uvsets(d,b,ch):
    rows=[]
    for mesh in d['meshes']:
        for prim in mesh['primitives']:
            attr=prim['attributes']
            if ch not in attr:continue
            a=d['accessors'][attr[ch]];v=d['bufferViews'][a['bufferView']]
            assert a['componentType']==5126 and a['type']=='VEC2'
            off=v.get('byteOffset',0)+a.get('byteOffset',0);stride=v.get('byteStride',8)
            rows.extend(tuple(round(x,5) for x in struct.unpack_from('<2f',b,off+i*stride)) for i in range(a['count']))
    return rows
catalog=json.loads((R/'equipment_catalog_v01.json').read_text())['models']
exports=json.loads((R/'SourceWeapons_All_v01/exported.json').read_text())['models']
by={str(row['model']):row for row in exports if not row.get('left')}
results=[]
for ident,row in catalog.items():
    if not row.get('info',{}).get('emblem'):continue
    original,ob=load(G/row['info']['file'])
    # Geometry aliases in the catalogue deliberately share a single canonical export.
    export_id=row['asset'].split('/Model_')[1].split('/')[0]
    baked,bb=load(R/'SourceWeapons_All_v01'/('weapon_'+export_id+'.glb'))
    match={};errors={}
    for ch in ['TEXCOORD_0','TEXCOORD_1','TEXCOORD_3']:
        a=uvsets(original,ob,ch);b=uvsets(baked,bb,ch)
        error=max((abs(x-y) for v,w in zip(a,b) for x,y in zip(v,w)),default=999)
        errors[ch]=error;match[ch]=len(a)==len(b) and error<.001
    results.append({'model':ident,'uv_sets_match':match,'max_quantization_error':errors})
report={'passed':all(all(x['uv_sets_match'].values()) for x in results),'models':len(results),'entries':results}
(R/'Reports/training_staff_fx_pets/emblem_source_uvs.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print({'passed':report['passed'],'models':len(results),'failed':[x for x in results if not all(x['uv_sets_match'].values())][:5]})
assert report['passed']
