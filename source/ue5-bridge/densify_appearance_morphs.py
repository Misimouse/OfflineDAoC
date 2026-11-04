"""Represent existing glTF morph values densely; preserve every numeric value and base mesh."""
import argparse,json,struct
from pathlib import Path

def read_glb(path):
    raw=Path(path).read_bytes();assert raw[:4]==b'glTF' and struct.unpack_from('<I',raw,4)[0]==2
    pos=12;doc=None;binary=None
    while pos<len(raw):
        size,kind=struct.unpack_from('<II',raw,pos);data=raw[pos+8:pos+8+size];pos+=8+size
        if kind==0x4e4f534a:doc=json.loads(data)
        if kind==0x004e4942:binary=data
    assert doc is not None and binary is not None and len(doc['buffers'])==1
    return doc,binary

def accessor_bytes(doc,binary,index):
    a=doc['accessors'][index];width={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']]*{5120:1,5121:1,5122:2,5123:2,5125:4,5126:4}[a['componentType']];out=bytearray(a['count']*width)
    if 'bufferView' in a:
        view=doc['bufferViews'][a['bufferView']];offset=view.get('byteOffset',0)+a.get('byteOffset',0);stride=view.get('byteStride',width)
        for i in range(a['count']):out[i*width:(i+1)*width]=binary[offset+i*stride:offset+i*stride+width]
    sparse=a.get('sparse')
    if sparse:
        indices=sparse['indices'];values=sparse['values'];iv=doc['bufferViews'][indices['bufferView']];vv=doc['bufferViews'][values['bufferView']];fmt={5121:'B',5123:'H',5125:'I'}[indices['componentType']];step=struct.calcsize('<'+fmt);io=iv.get('byteOffset',0)+indices.get('byteOffset',0);vo=vv.get('byteOffset',0)+values.get('byteOffset',0)
        for i in range(sparse['count']):
            vertex=struct.unpack_from('<'+fmt,binary,io+i*step)[0];assert vertex<a['count'];out[vertex*width:(vertex+1)*width]=binary[vo+i*width:vo+(i+1)*width]
    return bytes(out)

def densify(source,destination):
    doc,original=read_glb(source);binary=bytearray(original);targets={index for mesh in doc.get('meshes',[]) for prim in mesh.get('primitives',[]) for target in prim.get('targets',[]) for index in target.values()};before={i:accessor_bytes(doc,original,i) for i in targets};changed=0
    for i in sorted(targets):
        a=doc['accessors'][i]
        if 'sparse' not in a and 'bufferView' in a:continue
        data=before[i]
        while len(binary)%4:binary.append(0)
        view=len(doc['bufferViews']);doc['bufferViews'].append({'buffer':0,'byteOffset':len(binary),'byteLength':len(data)});binary.extend(data);a.pop('sparse',None);a['bufferView']=view;a['byteOffset']=0;changed+=1
    doc['buffers'][0]['byteLength']=len(binary);encoded=json.dumps(doc,separators=(',',':')).encode();encoded+=b' '*((-len(encoded))%4);binary.extend(b'\0'*((-len(binary))%4));raw=struct.pack('<4sII',b'glTF',2,12+8+len(encoded)+8+len(binary))+struct.pack('<II',len(encoded),0x4e4f534a)+encoded+struct.pack('<II',len(binary),0x004e4942)+binary
    Path(destination).parent.mkdir(parents=True,exist_ok=True);Path(destination).write_bytes(raw);check,blob=read_glb(destination);assert all(accessor_bytes(check,blob,i)==value for i,value in before.items());return {'changed_accessors':changed,'verified_morph_accessors':len(targets),'numeric_values_changed':False}

def moving_morph_names(path):
    doc,binary=read_glb(path);names=set();moving=set()
    for mesh in doc.get('meshes',[]):
        for prim in mesh.get('primitives',[]):
            for name,target in zip(mesh.get('extras',{}).get('targetNames',[]),prim.get('targets',[])):
                names.add(name)
                for index in target.values():
                    assert doc['accessors'][index]['componentType']==5126
                    if any(value[0]!=0 for value in struct.iter_unpack('<f',accessor_bytes(doc,binary,index))):moving.add(name)
    return moving,names-moving

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('destination',type=Path);a=p.parse_args();assert a.source.resolve()!=a.destination.resolve();print(densify(a.source,a.destination))
