"""Create a private moderate Celt physique; retain UVs, topology, rig and animation."""
import argparse,copy,hashlib,json,shutil,struct
from pathlib import Path
import numpy as np
from densify_appearance_morphs import read_glb,accessor_bytes

def arrays(document,binary,index):
    a=document['accessors'][index]
    components={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']]
    dtype={5121:'u1',5123:'<u2',5125:'<u4',5126:'<f4'}[a['componentType']]
    return np.frombuffer(accessor_bytes(document,binary,index),dtype).reshape(-1,components).astype(float)

def make_field(document,binary):
    skin=document['skins'][0]
    inverse=arrays(document,binary,skin['inverseBindMatrices']).reshape(-1,4,4).transpose(0,2,1)
    bind=np.linalg.inv(inverse)
    bones={document['nodes'][node]['name']:bind[i,:3,3] for i,node in enumerate(skin['joints'])}
    segments=[]
    for side in ['R','L']:
        for start,end,strength in [('UpperArm','Forearm',.15),('Forearm','Hand',.06),('Thigh','Calf',.10),('Calf','Foot',.10)]:
            segments.append((bones['Bip01 '+side+' '+start],bones['Bip01 '+side+' '+end],strength,start,side))
    def field(points):
        result=points.copy()
        for sign in [-1,1]:
            for limb in ['arm','leg']:
                chosen=[s for s in segments if (s[4]=='R')==(sign<0) and (s[3] in ['UpperArm','Forearm'])==(limb=='arm')]
                for a,b,strength,name,side in chosen:
                    axis=b-a;t=((points-a)@axis)/(axis@axis)
                    radial=points-(a+t[:,None]*axis)
                    radius=np.linalg.norm(radial,axis=1)
                    # Longitudinal taper leaves wrists, elbows, knees, ankles
                    # and the original attachment positions unchanged.
                    profile=np.sin(np.clip(t,0,1)*np.pi)**2
                    if name=='UpperArm':
                        # Round the deltoid over the upper quarter as well as
                        # the biceps, without moving the shoulder joint.
                        s=np.clip(t,0,1)
                        profile+=.4*s**2*(1-s)**6/(.25**2*.75**6)
                    fade=np.clip((10-radius)/4,0,1);falloff=fade*fade*(3-2*fade)
                    gate=(points[:,0]*sign>0)&(t>0)&(t<1)
                    lateral=np.clip((np.abs(points[:,0])-(5 if limb=='arm' else .5))/(4 if limb=='arm' else 1.5),0,1)
                    lateral=lateral*lateral*(3-2*lateral)
                    vertical=1 if limb=='arm' else np.clip((39-points[:,2])/2,0,1)
                    result+=radial*(strength*profile*falloff*gate*lateral*vertical)[:,None]
        # Small pectoral and upper-torso volume. The lower hem, neck, head,
        # hands and pelvis retain their original shape and attachment points.
        x,y,z=points.T
        upper=np.exp(-((z-51.5)/5.8)**2)*np.clip((61-z)/4,0,1)*np.clip((z-39)/4,0,1)
        side=np.clip((11-np.abs(x))/2.5,0,1)
        result[:,0]+=x*.035*upper*side
        front=np.clip((y-.5)/2,0,1)
        pec=np.exp(-((np.abs(x)-4.1)/3.8)**2)*np.exp(-((z-53)/3.5)**2)
        result[:,1]+=.38*pec*front*side
        return result
    return field

def prepare(source,destination,report_path):
    source=source.resolve();destination=destination.resolve()
    assert source!=destination
    original,blob=read_glb(source);document=copy.deepcopy(original);binary=bytearray(blob)
    assert original['nodes'][0].get('name')=='Cloaked_cel_m','This anatomical profile is only for the original male Celt'
    deform=make_field(document,blob);modified=set();changes=[];jacobian_min=1.
    def replace(index,values):
        assert np.isfinite(values).all()
        while len(binary)%4:binary.append(0)
        data=np.asarray(values,dtype='<f4').tobytes();a=document['accessors'][index]
        a['bufferView']=len(document['bufferViews']);a['byteOffset']=0;a.pop('sparse',None)
        document['bufferViews'].append({'buffer':0,'byteOffset':len(binary),'byteLength':len(data)})
        binary.extend(data);a['min']=np.min(values,axis=0).tolist();a['max']=np.max(values,axis=0).tolist();modified.add(index)
    for primitive in document['meshes'][0]['primitives']:
        material=document['materials'][primitive['material']]['name']
        if '_head_' in material or '_cloak_' in material:continue
        attrs=primitive['attributes'];positions=arrays(original,blob,attrs['POSITION']);new=deform(positions)
        delta=np.linalg.norm(new-positions,axis=1)
        if delta.max()<1e-6:continue
        triangles=arrays(original,blob,primitive['indices']).astype(int).reshape(-1,3)
        a=positions[triangles];b=new[triangles]
        old_cross=np.cross(a[:,1]-a[:,0],a[:,2]-a[:,0]);new_cross=np.cross(b[:,1]-b[:,0],b[:,2]-b[:,0])
        old_area=np.linalg.norm(old_cross,axis=1);new_area=np.linalg.norm(new_cross,axis=1);valid=old_area>1e-8
        angle=np.sum(old_cross[valid]*new_cross[valid],axis=1)/(old_area[valid]*new_area[valid])
        assert angle.min()>.5 and (new_area[valid]/old_area[valid]).min()>.5,(material,'triangle distortion')
        eps=.001
        jacobian=np.stack([(deform(positions+np.eye(3)[k]*eps)-deform(positions-np.eye(3)[k]*eps))/(2*eps) for k in range(3)],axis=-1)
        jacobian_min=min(jacobian_min,float(np.linalg.det(jacobian).min()))
        assert np.linalg.det(jacobian).min()>.5,(material,'unsafe deformation',float(np.linalg.det(jacobian).min()))
        replace(attrs['POSITION'],new)
        if 'NORMAL' in attrs:
            normals=arrays(original,blob,attrs['NORMAL']);normals=np.linalg.solve(jacobian.transpose(0,2,1),normals[...,None])[...,0];normals/=np.linalg.norm(normals,axis=1)[:,None];replace(attrs['NORMAL'],normals)
        if 'TANGENT' in attrs:
            tangents=arrays(original,blob,attrs['TANGENT']);tangent=np.einsum('nij,nj->ni',jacobian,tangents[:,:3]);tangent-=normals*np.sum(tangent*normals,axis=1)[:,None];tangent/=np.linalg.norm(tangent,axis=1)[:,None];replace(attrs['TANGENT'],np.column_stack([tangent,tangents[:,3]]))
        changes.append({'material':material,'vertices':len(positions),'moved':int((delta>1e-6).sum()),'max_displacement_source_units':float(delta.max()),'minimum_face_normal_agreement':float(angle.min()),'minimum_triangle_area_ratio':float((new_area[valid]/old_area[valid]).min())})
    document['buffers'][0]['byteLength']=len(binary)
    data=json.dumps(document,separators=(',',':')).encode();data+=b' '*((-len(data))%4);binary.extend(b'\0'*((-len(binary))%4))
    raw=struct.pack('<4sII',b'glTF',2,28+len(data)+len(binary))+struct.pack('<II',len(data),0x4e4f534a)+data+struct.pack('<II',len(binary),0x004e4942)+binary
    destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(raw)
    external=[]
    for image in original.get('images',[]):
        uri=image.get('uri','')
        if uri and not uri.startswith('data:'):
            p=(source.parent/uri).resolve();assert p.is_relative_to(source.parent)
            q=destination.parent/uri;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q);external.append(uri)
    check,check_blob=read_glb(destination)
    unchanged=0
    for i in range(len(original['accessors'])):
        if i not in modified:
            assert accessor_bytes(original,blob,i)==accessor_bytes(check,check_blob,i),i
            unchanged+=1
    for key in ['nodes','skins','animations','materials','images','meshes']:
        assert original[key]==check[key],key
    report={'passed':True,'installed':False,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'candidate_sha256':hashlib.sha256(raw).hexdigest(),'changes':changes,'unchanged_accessors':unchanged,'changed_accessors':len(modified),'uv_indices_skin_weights_rig_animation_unchanged':True,'minimum_jacobian_determinant':jacobian_min,'external_images':external}
    report_path.write_text(json.dumps(report,indent=2));return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source',type=Path);parser.add_argument('destination',type=Path);parser.add_argument('--report',required=True,type=Path);args=parser.parse_args();result=prepare(args.source,args.destination,args.report);print('PHYSIQUE_SOURCE_PASS',len(result['changes']),'sections;',result['unchanged_accessors'],'unchanged accessors')
