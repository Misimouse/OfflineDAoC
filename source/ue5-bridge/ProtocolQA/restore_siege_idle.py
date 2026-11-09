"""Retain source constant idle tracks that Godot's glTF exporter intentionally omits."""
import base64,copy,json,struct
from pathlib import Path
COMP={'SCALAR':1,'VEC3':3,'VEC4':4}
def restore(source,target,duration):
 original=json.loads(source.read_text());idle=next(a for a in original['animations'] if a['name']=='idle')
 raw=target.read_bytes();size=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+size]);offset=20+size;binary=bytearray(raw[offset+8:offset+8+struct.unpack_from('<I',raw,offset)[0]])
 if any(a.get('name')=='idle' for a in doc.get('animations',[])):return dict(restored=False,already_present=True)
 srcbuf=base64.b64decode(original['buffers'][0]['uri'].split(',')[1]);anim=dict(name='idle',channels=[],samplers=[])
 def values(index):
  a=original['accessors'][index];assert a['componentType']==5126 and not a.get('normalized');v=original['bufferViews'][a['bufferView']];n=COMP[a['type']];off=v.get('byteOffset',0)+a.get('byteOffset',0);stride=v.get('byteStride',n*4)
  return a,[struct.unpack_from('<'+'f'*n,srcbuf,off+i*stride) for i in range(a['count'])]
 def add(data,kind):
  while len(binary)%4:binary.append(0)
  start=len(binary);n=COMP[kind];packed=struct.pack('<'+'f'*(len(data)*n),*(x for row in data for x in row));binary.extend(packed)
  view=len(doc['bufferViews']);doc['bufferViews'].append(dict(buffer=0,byteOffset=start,byteLength=len(packed)))
  accessor=dict(bufferView=view,componentType=5126,count=len(data),type=kind)
  if kind=='SCALAR':accessor.update(min=[min(r[0] for r in data)],max=[max(r[0] for r in data)])
  index=len(doc['accessors']);doc['accessors'].append(accessor);return index
 times=add([(0.,),(duration,)],'SCALAR')
 for channel in idle['channels']:
  srcnode=original['nodes'][channel['target']['node']];name=srcnode['name'];matches=[i for i,node in enumerate(doc['nodes']) if node.get('name') in [name,name.replace(' ','_')]]
  assert len(matches)==1,(name,matches);node=doc['nodes'][matches[0]]
  for key,default in [('translation',[0,0,0]),('scale',[1,1,1]),('rotation',[0,0,0,1])]:
   a=srcnode.get(key,default);b=node.get(key,default);error=max(abs(x-y) for x,y in zip(a,b))
   if key=='rotation':error=min(error,max(abs(x+y) for x,y in zip(a,b)))
   assert error<.0001,(name,key,'Local skeleton frame changed')
  sampler=idle['samplers'][channel['sampler']];assert sampler.get('interpolation','LINEAR') in ['LINEAR','STEP']
  acc,rows=values(sampler['output']);first=rows[0];assert max(abs(x-y) for row in rows for x,y in zip(first,row))<.0001,'Idle contains motion; preserve it with a different export path'
  output=add([first,first],acc['type']);idx=len(anim['samplers']);anim['samplers'].append(dict(input=times,output=output,interpolation=sampler.get('interpolation','LINEAR')));anim['channels'].append(dict(sampler=idx,target=dict(node=matches[0],path=channel['target']['path'])))
 doc.setdefault('animations',[]).append(anim);doc['buffers']=[dict(byteLength=len(binary))]
 text=json.dumps(doc,separators=(',',':')).encode();text+=b' '*((-len(text))%4);binary.extend(b'\0'*((-len(binary))%4));length=12+8+len(text)+8+len(binary)
 target.write_bytes(struct.pack('<III',0x46546c67,2,length)+struct.pack('<II',len(text),0x4e4f534a)+text+struct.pack('<II',len(binary),0x004e4942)+binary)
 return dict(restored=True,tracks=len(anim['channels']),duration=duration,constant_source_values_preserved=True,local_skeleton_frames_verified=True)
