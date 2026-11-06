"""Recover original saddle rest point and verify the glTF-to-Unreal axis conversion against imported bones."""
import argparse,json,math,re,struct
from pathlib import Path
from prepare_combined_expansion_data import digest

def multiply(a,b):return [[sum(a[i][k]*b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]
def local(node):
    if 'matrix' in node:return [[node['matrix'][j*4+i] for j in range(4)] for i in range(4)]
    x,y,z,w=node.get('rotation',[0,0,0,1]);sx,sy,sz=node.get('scale',[1,1,1]);tx,ty,tz=node.get('translation',[0,0,0])
    return [[(1-2*(y*y+z*z))*sx,2*(x*y-z*w)*sy,2*(x*z+y*w)*sz,tx],[2*(x*y+z*w)*sx,(1-2*(x*x+z*z))*sy,2*(y*z-x*w)*sz,ty],[2*(x*z-y*w)*sx,2*(y*z+x*w)*sy,(1-2*(x*x+y*y))*sz,tz],[0,0,0,1]]
def extracted(source):
    data=source.read_bytes();assert data[:4]==b'glTF';size,kind=struct.unpack_from('<II',data,12);assert kind==0x4e4f534a
    doc=json.loads(data[20:20+size]);nodes=doc['nodes'];parents={child:i for i,node in enumerate(nodes) for child in node.get('children',[])}
    def world(index,seen=None):
        seen=set() if seen is None else seen;assert index not in seen;seen.add(index)
        return multiply(world(parents[index],seen),local(nodes[index])) if index in parents else local(nodes[index])
    def point(index):
        matrix=world(index);x,y,z=[matrix[i][3] for i in range(3)];return [x*100,z*100,y*100]
    saddles=[i for i,node in enumerate(nodes) if node.get('name')=='saddle'];assert len(saddles)==1
    anchors=[i for i,node in enumerate(nodes) if node.get('name')=='Bip01 Spine1'];assert len(anchors)==1
    saddle=point(saddles[0]);assert all(math.isfinite(v) for v in saddle) and 60<saddle[2]<250
    row={'anchor_bone':'Bip01-Spine1','saddle_reference_component_cm':saddle,'anchor_reference_component_cm':point(anchors[0]),'fallback_height_cm':130}
    return row,nodes,point

def prepare(workspace,source_only=False):
    root=workspace/'LiveRidingLab';root.mkdir(exist_ok=True)
    sources={'2174':workspace/'SourceAnimations_v02/model_2174.glb'}
    if (root/'SourceModels/model_448.glb').exists():sources['448']=root/'SourceModels/model_448.glb'
    catalog={'version':1,'models':{},'rider_clip':'ride_horse'};geometry={}
    for ident,source in sources.items():
        row,nodes,point=extracted(source)
        task_path=workspace/'SourceAnimations_v02/tasks.json' if ident=='2174' else root/'SourceModels/tasks.json'
        tasks=json.loads(task_path.read_text(encoding='utf-8-sig'))
        task=next(t for t in tasks if str(t.get('model_id',t.get('id','')))==ident)
        strides=task['info']['strides_units'];row['stride_m']={key:float(strides[key])*.025 for key in ['walk','run']}
        assert all(math.isfinite(v) and .1<v<30 for v in row['stride_m'].values())
        catalog['models'][ident]=row;geometry[ident]=(nodes,point)
    target=root/'riding.json';target.write_text(json.dumps(catalog,indent=2),encoding='utf-8')
    if source_only:return dict(passed=True,source_only=True,models=list(sources),catalog=str(target),source_hashes={str(p):digest(p) for p in sources.values()})
    asset_path=sorted((root/'AssetAcceptance').glob('*/verified.json'))[-1];asset=json.loads(asset_path.read_text(encoding='utf-8-sig'))
    assert asset['passed'] and asset['checks']>=64 and not asset['failures'] and asset['build_receipt_sha256']==digest(root/'native_build.json')
    assert asset['riding_catalog_sha256']==digest(target)
    clean=lambda name:re.sub('[^a-z0-9]','',name.lower());errors=[];matched={};rest_differences={}
    for ident,(nodes,point) in geometry.items():
        imported={clean(b['name']):b for b in asset['horse_bones' if ident=='2174' else 'taxi_bones']};count=0;model_errors=[]
        for i,node in enumerate(nodes):
            key=clean(node.get('name',''))
            if key in imported:model_errors.append(math.dist(point(i),imported[key]['component_cm']));count+=1
        assert count>=20 and imported['bip01spine1']['name']==catalog['models'][ident]['anchor_bone'];matched[ident]=count
        anchor_error=math.dist(catalog['models'][ident]['anchor_reference_component_cm'],imported['bip01spine1']['component_cm'])
        # The taxi source node-rest and imported skin bind-rest differ slightly.
        # Record that separately; the native seat test uses the source saddle
        # point and the ACTUAL imported/posed reference bone, never a guessed Y.
        rest_differences[ident]=dict(maximum_cm=max(model_errors),anchor_cm=anchor_error,comparison='source node rest versus UE imported skin reference')
        if ident=='2174':
            assert max(model_errors)<.01;errors.extend(model_errors)
        else:assert max(model_errors)<1.1 and anchor_error<.2,rest_differences[ident]
    assert max(errors)<.01,(matched,max(errors))
    models=root/'models.json' if (root/'models.json').exists() else workspace/'models.json'
    paths=list(sources.values())+[asset_path,root/'native_build.json',root/'reference_audit.json',models]
    proof={'passed':True,'catalog':str(target),'catalog_sha256':digest(target),'imported_bones_matched':sum(matched.values()),'models_matched':matched,'source_rest_comparisons':rest_differences,'max_axis_conversion_error_cm':max(errors),'input_hashes':{str(p):digest(p) for p in paths},'normal_installation_modified':False,'scale_policy':'Actual instance transform supplies catalog scale and race-specific steed size; rest points never bake instance size'}
    (root/'resources.json').write_text(json.dumps(proof,indent=2),encoding='utf-8');return dict(passed=True,bones_matched=matched,reference_axis_error_cm=max(errors),source_rest_differences_cm=rest_differences,catalog=str(target))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--source-only',action='store_true');a=p.parse_args();print(json.dumps(prepare(a.workspace.resolve(),a.source_only)))
