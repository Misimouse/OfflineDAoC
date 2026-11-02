"""Compare source geometry/skin bytes while allowing additional animation tracks."""
import json,struct,hashlib,re
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/pose_animations'
def load(path):
 raw=path.read_bytes();assert raw[:4]==b'glTF';pos=12;chunks={}
 while pos<len(raw):
  n,t=struct.unpack_from('<II',raw,pos);chunks[t]=raw[pos+8:pos+8+n];pos+=8+n
 return json.loads(chunks[0x4E4F534A]),chunks[0x004E4942]
def geometry(path):
 g,b=load(path)
 def accessor(index):
  a=g['accessors'][index];v=g['bufferViews'][a['bufferView']];start=v.get('byteOffset',0)+a.get('byteOffset',0)
  size={5120:1,5121:1,5122:2,5123:2,5125:4,5126:4}[a['componentType']]*{'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']];stride=v.get('byteStride',size)
  data=b''.join(b[start+i*stride:start+i*stride+size]for i in range(a['count']))
  return {'type':a['type'],'component':a['componentType'],'count':a['count'],'sha':hashlib.sha256(data).hexdigest()}
 meshes=[[{'attributes':{k:accessor(v)for k,v in p['attributes'].items()},'indices':accessor(p['indices'])if'indices'in p else None,'mode':p.get('mode',4),'material':p.get('material')}for p in m['primitives']]for m in g['meshes']]
 skins=[{'inverse':accessor(s['inverseBindMatrices']),'joints':s['joints']}for s in g.get('skins',[])]
 nodes=[{k:v for k,v in n.items() if k not in ['extras','extensions']}for n in g['nodes']]
 # Godot assigns per-process counters to two unnamed container types. They are
 # not bones; preserve every bone name, transform and hierarchy index exactly.
 for n in nodes:
  if re.fullmatch(r'_(Node3D|PhysicalBoneSimulator3D)_\d+',n.get('name','')):n['name']=re.sub(r'_\d+$','',n['name'])
 return {'meshes':meshes,'skins':skins,'nodes':nodes},g
result={'models':{},'passed':True}
for ident in [t['id']for t in json.loads((R/'SourceAnimations_v02/tasks.json').read_text())]:
 old,_=geometry(R/f'SourceModels/model_{ident}.glb');new,g=geometry(R/f'SourceAnimations_v02/model_{ident}.glb');same=old==new
 clips=[a['name']for a in g.get('animations',[])];result['models'][ident]={'geometry_skin_nodes_identical':same,'animations':clips};result['passed']&=same
(D/'export_verification.json').write_text(json.dumps(result,indent=2));print({k:{'unchanged':v['geometry_skin_nodes_identical'],'clips':len(v['animations'])}for k,v in result['models'].items()});assert result['passed']
