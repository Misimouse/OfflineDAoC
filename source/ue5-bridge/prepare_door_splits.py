"""Match original animated leaves to the imported, closed static mesh triangles."""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import base64,json,re,sys
from pathlib import Path
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R.parent/'DAoC-Enhanced-Unreal/.terrain-python'))
import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation
D=R/'Reports/navigation/traversal';survey=json.loads((D/'survey.json').read_text())
ZONE=Path(str(INSTALL / 'new-client/godot/content/zones/zone207'))
zone=json.loads((ZONE/'zone.json').read_text());output={}
def read_gltf(path):
    d=json.loads(path.read_text());buffers=[base64.b64decode(b['uri'].split(',',1)[1])if b['uri'].startswith('data:')else(path.parent/b['uri']).read_bytes()for b in d['buffers']]
    def read(index):
        a=d['accessors'][index];v=d['bufferViews'][a['bufferView']];dt={5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[a['componentType']];size={'VEC3':3,'VEC2':2,'SCALAR':1}[a['type']]
        item=np.dtype(dt).itemsize;offset=v.get('byteOffset',0)+a.get('byteOffset',0)
        return np.ndarray((a['count'],size),dtype=dt,buffer=buffers[v['buffer']],offset=offset,strides=(v.get('byteStride',item*size),item)).copy()
    return d,read
swap=np.array([[1,0,0],[0,0,1],[0,1,0]])
for path,entry in survey['meshes'].items():
    name=path.rsplit('/',1)[-1].split('.')[0];source=ZONE/'models'/(name+'.gltf')
    if name not in ('helfshack','elftavern2'):continue
    if not source.exists():continue
    gltf,read=read_gltf(source);specs={s['id']:s for s in gltf.get('extras',{}).get('nif_doors',[])}
    if not specs:continue
    old=json.loads((D/entry['file']).read_text());triangles=np.array(old['vertices'])[old['triangles']];tree=cKDTree(triangles.mean(1));leaves=[];remove=set()
    for leafid,spec in specs.items():
        closed=np.array(spec['closed']);basis=closed[:9].reshape(3,3).T;pivot=closed[9:]
        opened=np.array(spec['open']);ob=opened[:9].reshape(3,3).T
        ids=[];collision=[];expected=0
        for node in gltf['nodes']:
            match=re.match(r'^door(col)?(\d+)_',node.get('name',''))
            if not match or int(match[2])!=leafid:continue
            for primitive in gltf['meshes'][node['mesh']]['primitives']:
                vertices=read(primitive['attributes']['POSITION']);indices=read(primitive['indices']).reshape(-1,3)
                posed=((vertices@basis.T+pivot)@swap.T*100)[indices]
                for triangle in posed:
                    tolerance=6 if match[1] else .5
                    candidates=tree.query_ball_point(triangle.mean(0),tolerance)
                    matches=[i for i in candidates if max(min(np.linalg.norm(p-triangles[i],axis=1))for p in triangle)<tolerance]
                    assert matches,(name,leafid,triangle.tolist())
                    (collision if match[1] else ids).extend(matches);remove.update(matches);expected+=1
        if ids:
            leaves.append(dict(id=leafid,group=spec['group'],triangle_ids=sorted(set(ids)),triangles=triangles[sorted(set(ids))].tolist(),pivot_cm=(pivot@swap.T*100).tolist(),
                open_pivot_cm=(opened[9:]@swap.T*100).tolist(),open_quat=Rotation.from_matrix(swap@ob@np.linalg.inv(basis)@swap.T).as_quat().tolist(),seconds=spec['seconds']))
        print(name,leafid,'visual',len(set(ids)),'collision',len(set(collision)),'source_triangles',expected)
    fixtures=[]
    for component in survey['components']:
        if component['mesh']!=path:continue
        point=np.array(component['position'])[[0,2,1]]/100+np.array([1364,130,1263])
        matches=[f for f in zone['fixtures']if Path(zone['models'][f['m']]['file']).stem==name and np.linalg.norm(np.array(f['pos'])-point)<.1]
        assert len(matches)==1,(component['actor'],point.tolist())
        fid=matches[0].get('id',-1)
        centre=(triangles[sorted(remove)].min(axis=(0,1))+triangles[sorted(remove)].max(axis=(0,1)))/2
        centre=Rotation.from_quat(component['rotation']).apply(centre*np.array(component['scale']))+component['position']
        centre_m=centre[[0,2,1]]/100+np.array([1364,130,1263])
        fixtures.append(dict(component=component['component'],actor=component['actor'],fixture_id=fid,position_m=centre_m.tolist(),
            groups={g:207000000+fid*100+int(re.search(r'\d+',g)[0]) for g in {leaf['group']for leaf in leaves}}))
    output[path]=dict(remove_triangle_ids=sorted(remove),remove_triangles=triangles[sorted(remove)].tolist(),leaves=leaves,fixtures=fixtures)
(D/'door_splits.json').write_text(json.dumps(output,indent=2));print('models',len(output))
