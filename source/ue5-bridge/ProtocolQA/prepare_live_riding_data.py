"""Recover original saddle rest point and verify the glTF-to-Unreal axis conversion against imported bones."""
import argparse,json,math,re,struct
from pathlib import Path
from prepare_combined_expansion_data import digest

def multiply(a,b):return [[sum(a[i][k]*b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]
def local(node):
    if 'matrix' in node:return [[node['matrix'][j*4+i] for j in range(4)] for i in range(4)]
    x,y,z,w=node.get('rotation',[0,0,0,1]);sx,sy,sz=node.get('scale',[1,1,1]);tx,ty,tz=node.get('translation',[0,0,0])
    return [[(1-2*(y*y+z*z))*sx,2*(x*y-z*w)*sy,2*(x*z+y*w)*sz,tx],[2*(x*y+z*w)*sx,(1-2*(x*x+z*z))*sy,2*(y*z-x*w)*sz,ty],[2*(x*z-y*w)*sx,2*(y*z+x*w)*sy,(1-2*(x*x+y*y))*sz,tz],[0,0,0,1]]
def prepare(workspace):
    root=workspace/'LiveRidingLab';asset_path=sorted((root/'AssetAcceptance').glob('*/verified.json'))[-1];asset=json.loads(asset_path.read_text(encoding='utf-8-sig'))
    assert asset['passed'] and asset['checks']>=31 and not asset['failures'] and asset['build_receipt_sha256']==digest(root/'native_build.json')
    source=workspace/'SourceAnimations_v02/model_2174.glb';data=source.read_bytes();assert data[:4]==b'glTF';size,kind=struct.unpack_from('<II',data,12);assert kind==0x4e4f534a
    doc=json.loads(data[20:20+size]);nodes=doc['nodes'];parents={child:i for i,node in enumerate(nodes) for child in node.get('children',[])}
    def world(index,seen=None):
        seen=set() if seen is None else seen;assert index not in seen;seen.add(index)
        return multiply(world(parents[index],seen),local(nodes[index])) if index in parents else local(nodes[index])
    def point(index):
        matrix=world(index);x,y,z=[matrix[i][3] for i in range(3)];return [x*100,z*100,y*100]
    clean=lambda name:re.sub('[^a-z0-9]','',name.lower())
    imported={clean(b['name']):b for b in asset['horse_bones']};errors=[]
    for i,node in enumerate(nodes):
        key=clean(node.get('name',''))
        if key in imported:errors.append(math.dist(point(i),imported[key]['component_cm']))
    assert len(errors)>=40 and max(errors)<.01,(len(errors),max(errors))
    saddles=[i for i,node in enumerate(nodes) if node.get('name')=='saddle'];assert len(saddles)==1
    anchor=imported['bip01spine1'];saddle=point(saddles[0]);assert all(math.isfinite(v) for v in saddle) and 100<saddle[2]<200
    catalog={'version':1,'models':{'2174':{'anchor_bone':anchor['name'],'saddle_reference_component_cm':saddle,'anchor_reference_component_cm':anchor['component_cm'],'fallback_height_cm':130}},'rider_clip':'ride_horse'}
    target=root/'riding.json';target.write_text(json.dumps(catalog,indent=2),encoding='utf-8')
    paths=[source,asset_path,root/'native_build.json',root/'reference_audit.json',workspace/'models.json']
    proof={'passed':True,'catalog':str(target),'catalog_sha256':digest(target),'imported_bones_matched':len(errors),'max_axis_conversion_error_cm':max(errors),'input_hashes':{str(p):digest(p) for p in paths},'normal_installation_modified':False,'scale_policy':'Apply catalog 1.1 and actual steed size in native component transform, never bake the instance size into this rest point'}
    (root/'resources.json').write_text(json.dumps(proof,indent=2),encoding='utf-8');return dict(passed=True,bones_matched=len(errors),max_error_cm=max(errors),catalog=str(target))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workspace',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.workspace.resolve())))
