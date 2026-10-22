"""Offline sculpting of copies of stock menhirs, plus mask-guided solid ivy geometry.

Only writes the supplied private output directory. Input glTFs/PNGs are read-only.
Requires numpy and Pillow; no downloaded/user-provided executable is run.
"""
from pathlib import Path
import argparse, base64, collections, hashlib, json, math, struct
import numpy as np
from PIL import Image


def unit(v):
    a=np.asarray(v,dtype=float)
    return a/np.maximum(np.linalg.norm(a,axis=-1,keepdims=True),1e-12)


class Source:
    def __init__(self,path):
        self.path=path;self.g=json.loads(path.read_text())
        self.buffers=[base64.b64decode(b['uri'].split(',')[1]) if b['uri'].startswith('data:') else (path.parent/b['uri']).read_bytes() for b in self.g['buffers']]

    def array(self,index):
        a=self.g['accessors'][index];v=self.g['bufferViews'][a['bufferView']]
        dtype=np.dtype({5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[a['componentType']])
        n={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
        return np.ndarray((a['count'],n),dtype=dtype,buffer=self.buffers[v.get('buffer',0)],offset=v.get('byteOffset',0)+a.get('byteOffset',0),strides=(v.get('byteStride',dtype.itemsize*n),dtype.itemsize)).copy()

    def parts(self):
        # Converted exterior models currently have baked coordinates; explicitly reject unexpected transforms.
        for node in self.g['nodes']:
            if 'mesh' not in node or node.get('name','').startswith(('collision_','climb_')):continue
            if any(k in node for k in ['matrix','translation','rotation','scale']):raise ValueError('Uninspected node transform: '+str(self.path))
            mesh=self.g['meshes'][node['mesh']]
            for prim in mesh['primitives']:
                if 'material' not in prim:continue
                a=prim['attributes'];spec=self.g.get('extras',{}).get('nif_materials',[])[prim['material']]
                yield {'name':mesh.get('name',node['name']),'p':self.array(a['POSITION']),'n':self.array(a['NORMAL']),'uv':self.array(a['TEXCOORD_1']) if 'TEXCOORD_1' in a else None,'f':self.array(prim['indices']).reshape(-1,3),'spec':spec}


def stock_mesh(src):
    positions=[];faces=[];uvs=[];masks=[];lookup={}
    for part in src.parts():
        vine=part['spec'].get('slots',{}).get('dark',{}).get('tex')=='hclimbvine'
        for triangle in part['f']:
            ids=[]
            for point in part['p'][triangle]:
                key=tuple(np.round(point,4))
                if key not in lookup:lookup[key]=len(positions);positions.append(point)
                ids.append(lookup[key])
            faces.append(ids);uvs.append(part['uv'][triangle] if vine else np.zeros((3,2)));masks.append(float(vine))
    return np.asarray(positions,dtype=float),np.asarray(faces,dtype=int),np.asarray(uvs),np.asarray(masks)


def subdivide(v,f,uv,mask):
    edges={};neighbours=[set() for _ in v]
    for a,b,c in f:
        for x,y,opposite in [(a,b,c),(b,c,a),(c,a,b)]:
            key=tuple(sorted((x,y)));edges.setdefault(key,[]).append(opposite);neighbours[x].add(y);neighbours[y].add(x)
    assert all(len(x)==2 for x in edges.values()),'Menhir must remain closed/manifold'
    out=[]
    for i,p in enumerate(v):
        n=len(neighbours[i]);beta=(0.625-(0.375+0.25*math.cos(2*math.pi/n))**2)/n
        out.append(p+0.30*(beta*v[list(neighbours[i])].sum(0)-n*beta*p))
    edge_index={}
    for (a,b),op in edges.items():
        edge_index[(a,b)]=len(out);out.append(0.5*(v[a]+v[b])+0.30*0.125*(v[op[0]]+v[op[1]]-v[a]-v[b]))
    fs=[];us=[];ms=[]
    for tri,u,m in zip(f,uv,mask):
        a,b,c=tri;ab=edge_index[tuple(sorted((a,b)))];bc=edge_index[tuple(sorted((b,c)))];ca=edge_index[tuple(sorted((c,a)))];ua,ub,uc=u;uab=(ua+ub)/2;ubc=(ub+uc)/2;uca=(uc+ua)/2
        fs.extend([[a,ab,ca],[b,bc,ab],[c,ca,bc],[ab,bc,ca]])
        us.extend([[ua,uab,uca],[ub,ubc,uab],[uc,uca,ubc],[uab,ubc,uca]]);ms.extend([m]*4)
    return np.asarray(out),np.asarray(fs),np.asarray(us),np.asarray(ms)


def normals(v,f):
    n=np.zeros_like(v);tri=v[f];cross=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
    for i in range(3):np.add.at(n,f[:,i],cross)
    return unit(n)


def sculpt(src,seed):
    v,f,uv,mask=stock_mesh(src);lo=v.min(0);hi=v.max(0);initial=len(f)
    for _ in range(4):v,f,uv,mask=subdivide(v,f,uv,mask)
    # Recover the original envelope after rounding, including the original buried base.
    v=(v-v.min(0))/(v.max(0)-v.min(0))*(hi-lo)+lo
    n=normals(v,f);height=hi[1]-lo[1];y=(v[:,1]-lo[1])/height;phase=(seed%19)*0.31
    # Large, shallow worn hollows and a bent fracture cut, all baked into actual vertices.
    front=np.clip(n[:,2],0,1)**2
    line=0.12+0.19*(y-0.5)+0.035*np.sin(y*14+phase)
    cut=0.065*np.exp(-((v[:,0]-line)/0.065)**2)*front*np.exp(-((y-0.63)/0.34)**8)
    dent=0.10*np.exp(-((v[:,0]+0.36)/0.24)**2-((y-0.59)/0.12)**2)*front
    side=0.065*np.exp(-((v[:,2]+0.05)/0.22)**2-((y-0.38)/0.15)**2)*np.clip(n[:,0],0,1)**2
    # Quiet broad weathering, not uniformly spiky noise. Keep ground contact and the top envelope.
    wear=0.012*np.sin(v[:,0]*5.1+phase)*np.sin(v[:,1]*3.7+0.2)*np.cos(v[:,2]*4.3-phase)
    envelope=np.clip((y-0.15)*5,0,1)*np.clip((1-y)*12,0,1)
    depth=(cut+dent+side-wear)*envelope
    v=v-n*depth[:,None];n=normals(v,f);cavity=np.clip(1-(cut+dent+side)*2.0,0.73,1)
    edges=collections.Counter(tuple(sorted((t[i],t[(i+1)%3]))) for t in f for i in range(3))
    assert all(count==2 for count in edges.values())
    assert np.isfinite(v).all() and np.isfinite(n).all()
    return v,f,n,uv,mask,cavity,{'original_triangles':initial,'triangles':len(f),'vertices':len(v),'original_bounds':[lo.tolist(),hi.tolist()],'improved_bounds':[v.min(0).tolist(),v.max(0).tolist()],'closed_manifold':True,'buried_base_preserved':True,'maximum_sculpt_depth_m':float(depth.max())}


class Mesh:
    def __init__(self):self.v=[];self.f=[]
    def vertex(self,p,n,uv=(0,0),uv2=(0,0),colour=(1,1,1,1)):
        self.v.append([*p,*n,*uv,*uv2,*colour]);return len(self.v)-1
    def triangle(self,a,b,c):self.f.append([a,b,c])
    def tube(self,a,b,r,colour,sides=5):
        direction=np.asarray(b)-a
        if np.linalg.norm(direction)<0.002:return
        d=unit(direction);t=unit(np.cross(d,[1,0,0] if abs(d[0])<0.8 else [0,1,0]));bit=np.cross(d,t);rings=[]
        for point in [a,b]:
            ring=[]
            for j in range(sides):
                normal=math.cos(j*2*math.pi/sides)*t+math.sin(j*2*math.pi/sides)*bit
                ring.append(self.vertex(point+normal*r,normal,colour=colour))
            rings.append(ring)
        for i in range(sides):
            j=(i+1)%sides;self.triangle(rings[0][i],rings[0][j],rings[1][i]);self.triangle(rings[0][j],rings[1][j],rings[1][i])
    def leaf(self,p,n,rng):
        # Solid five-lobed ivy leaf with a raised midrib and folded/cupped edges; no alpha billboard.
        n=unit(n+np.asarray([rng.uniform(-.22,.22),rng.uniform(-.22,.22),rng.uniform(-.22,.22)]));up=unit(np.asarray([0,1,0])-n*n[1])
        if np.linalg.norm(up)<0.01:up=unit(np.cross(n,[1,0,0]))
        side=unit(np.cross(up,n));angle=rng.uniform(-0.9,0.9);s=side*math.cos(angle)+up*math.sin(angle);u=up*math.cos(angle)-side*math.sin(angle)
        length=rng.uniform(0.075,0.135);width=length*rng.uniform(0.78,1.12)
        outline=[(0,-0.48),(-.22,-.25),(-.5,-.26),(-.34,.03),(-.58,.24),(-.23,.25),(0,.63),(.23,.25),(.58,.24),(.34,.03),(.5,-.26),(.22,-.25)]
        tint=rng.uniform(.82,1.18);colour=(.07*tint,.19*tint,.025*tint,1)
        points=[np.asarray(p)+n*0.015]+[np.asarray(p)+s*x*width+u*y*length+n*(.004+(.63-y)*.008+abs(x)*.006) for x,y in outline]
        coords=[(0,.05)]+outline;ns=np.zeros((len(points),3));fs=[]
        for j in range(len(outline)):
            a=0;b=j+1;c=(j+1)%len(outline)+1;cross=np.cross(points[b]-points[a],points[c]-points[a])
            if np.dot(cross,n)<0:b,c=c,b;cross=-cross
            fs.append((a,b,c));ns[a]+=cross;ns[b]+=cross;ns[c]+=cross
        ids=[self.vertex(point,normal,uv=uv,colour=colour) for point,normal,uv in zip(points,unit(ns),coords)]
        for a,b,c in fs:self.triangle(ids[a],ids[b],ids[c])
        petiole=np.asarray(p)-u*length*.48
        return petiole
    def save(self,out,name):
        v=np.asarray(self.v,dtype='<f4').reshape(-1,14);f=np.asarray(self.f,dtype='<u4').reshape(-1,3)
        assert np.isfinite(v).all()
        (out/(name+'.vtx')).write_bytes(v.tobytes());(out/(name+'.idx')).write_bytes(f.tobytes())
        return {'name':name,'vertices':len(v),'triangles':len(f),'vertex_file':name+'.vtx','index_file':name+'.idx'}


def body_mesh(v,f,n,uv,mask,cavity):
    mesh=Mesh();lookup={}
    for face,uvs,has_mask in zip(f,uv,mask):
        ids=[]
        for i,uv2 in zip(face,uvs):
            key=(int(i),*np.round(uv2,5),int(has_mask))
            if key not in lookup:lookup[key]=mesh.vertex(v[i],n[i],uv=(v[i,0],v[i,1]),uv2=uv2,colour=(cavity[i],1,1,has_mask))
            ids.append(lookup[key])
        mesh.triangle(*ids)
    return mesh


def skeleton(mask):
    a=(np.asarray(Image.fromarray(mask).resize((64,64),Image.Resampling.BOX))>85).astype(np.uint8)
    for _ in range(100):
        changed=False
        for step in [0,1]:
            p=np.pad(a,1);neighbours=[p[:-2,1:-1],p[:-2,2:],p[1:-1,2:],p[2:,2:],p[2:,1:-1],p[2:,:-2],p[1:-1,:-2],p[:-2,:-2]];count=sum(neighbours);trans=sum((neighbours[i]==0)&(neighbours[(i+1)%8]==1) for i in range(8))
            cond=(neighbours[0]*neighbours[2]*neighbours[4]==0)&(neighbours[2]*neighbours[4]*neighbours[6]==0) if step==0 else (neighbours[0]*neighbours[2]*neighbours[6]==0)&(neighbours[0]*neighbours[4]*neighbours[6]==0)
            remove=(a==1)&(count>=2)&(count<=6)&(trans==1)&cond
            if remove.any():a[remove]=0;changed=True
        if not changed:break
    result=[]
    for y,x in zip(*np.where(a)):
        for dy,dx in [(0,1),(1,-1),(1,0),(1,1)]:
            yy,xx=y+dy,x+dx
            if yy<0 or xx<0 or yy>=64 or xx>=64 or not a[yy,xx]:continue
            if dy and dx and (a[y,xx] or a[yy,x]):continue
            result.append([[(x+.5)/64,(y+.5)/64],[(xx+.5)/64,(yy+.5)/64]])
    return np.asarray(result,dtype=float).reshape(-1,2,2)


def projector(v,f):
    tri=v[f];e1=tri[:,1]-tri[:,0];e2=tri[:,2]-tri[:,0];ns=unit(np.cross(e1,e2))
    def project(p,n):
        origin=p+n*.7;d=-n;h=np.cross(d,e2);det=np.einsum('ij,ij->i',e1,h);inv=1/np.where(abs(det)>1e-9,det,1);s=origin-tri[:,0];u=inv*np.einsum('ij,ij->i',s,h);q=np.cross(s,e1);w=inv*(q@d);t=inv*np.einsum('ij,ij->i',e2,q)
        valid=(abs(det)>1e-9)&(u>=-1e-6)&(w>=-1e-6)&(u+w<=1.000001)&(t>0)&(t<1.3)
        if not valid.any():return p,n
        i=int(np.argmin(np.where(valid,abs(t-.7),np.inf)));return origin+d*t[i],ns[i]
    return project


def ivy(src,zone_dir,seed,project=None):
    leaves=Mesh();stems=Mesh();rng=np.random.default_rng(seed);cells=set();leaf_count=0;segment_count=0;parts=[]
    for part in src.parts():
        slot=part['spec'].get('slots',{}).get('dark',{});name=slot.get('tex','')
        if name not in ['hclimbvine','hbasevine'] or slot.get('uv')!=1 or part['uv'] is None:continue
        parts.append({'mesh_name':part['name'],'texture':name})
        img=np.asarray(Image.open(zone_dir/'textures/x4plus'/(name+'.png')).convert('RGBA'));alpha=img[:,:,3]
        if name=='hbasevine':
            # This multiplicative overlay is opaque white outside the plant, not an alpha cutout.
            rgb=img[:,:,:3].astype(float);green=rgb[:,:,1]-(rgb[:,:,0]+rgb[:,:,2])*0.5
            alpha=(alpha*np.clip((green-4)/15,0,1)).astype(np.uint8)
        skel=skeleton(alpha)
        for face in part['f']:
            tri=part['p'][face];uv=part['uv'][face];norm=unit(np.cross(tri[1]-tri[0],tri[2]-tri[0]));area=np.linalg.norm(np.cross(tri[1]-tri[0],tri[2]-tri[0]))/2
            if area<1e-6:continue
            # Surface points selected by the source alpha mask, in the source's own second UV set.
            for _ in range(min(15000,int(area*240)+1)):
                if leaf_count>=1800:break
                r,s=rng.random(2)
                if r+s>1:r,s=1-r,1-s
                coords=uv[0]+r*(uv[1]-uv[0])+s*(uv[2]-uv[0]);pix=(coords%1*np.array([img.shape[1],img.shape[0]])).astype(int)
                if alpha[pix[1],pix[0]]<115:continue
                point=tri[0]+r*(tri[1]-tri[0])+s*(tri[2]-tri[0])
                if point[1]<.02:continue
                pn,nn=project(point,norm) if project else (point,norm)
                key=tuple(np.floor(pn/.06).astype(int))
                if key in cells:continue
                cells.add(key);pos=pn+nn*rng.uniform(.018,.042);petiole=leaves.leaf(pos,nn,rng);stems.tube(pn+nn*.011,petiole,.0035,(.13,.19,.055,1));leaf_count+=1
            matrix=np.column_stack([uv[1]-uv[0],uv[2]-uv[0]])
            if abs(np.linalg.det(matrix))<1e-8:continue
            inv=np.linalg.inv(matrix)
            for u0 in range(math.floor(uv[:,0].min()),math.floor(uv[:,0].max())+1):
                for v0 in range(math.floor(uv[:,1].min()),math.floor(uv[:,1].max())+1):
                    coords=skel+np.array([u0,v0]);bary=(coords-uv[0])@inv.T;valid=(bary[:,:,0]>=-1e-5)&(bary[:,:,1]>=-1e-5)&(bary.sum(2)<=1.00001)
                    for pair in bary[valid.all(1)]:
                        if segment_count>=2500:break
                        ps=[tri[0]+b[0]*(tri[1]-tri[0])+b[1]*(tri[2]-tri[0]) for b in pair]
                        if min(p[1] for p in ps)<.015:continue
                        ps=[(project(p,norm)[0]+project(p,norm)[1]*.012) if project else p+norm*.012 for p in ps]
                        stems.tube(ps[0],ps[1],.0055,(.115,.17,.047,1));segment_count+=1
    return leaves,stems,{'leaves':leaf_count,'stem_segments':segment_count,'clean_parts':parts,'source_mask_guided':True,'solid_leaf_geometry':True}


def main():
    a=argparse.ArgumentParser();a.add_argument('--zone',required=True);a.add_argument('--out',required=True);a.add_argument('--only',nargs='*',type=int);args=a.parse_args();zone=Path(args.zone);out=Path(args.out);out.mkdir(parents=True,exist_ok=True);z=json.loads((zone/'zone.json').read_text());results=[]
    previous=json.loads((out/'geometry.json').read_text()) if args.only and (out/'geometry.json').exists() else {}
    for fid in [1429,1431,1430,935,334,335,336,1107]:
        if args.only and fid not in args.only:
            results.append(next(e for e in previous['targets'] if e['fixture']['id']==fid));continue
        fixture=next(f for f in z['fixtures'] if f['id']==fid);model=z['models'][fixture['m']];src=Source(zone/model['file']);entry={'fixture':fixture,'model':model,'source_sha256':hashlib.sha256(src.path.read_bytes()).hexdigest()};meshes={}
        if fid in [1429,1431,1430,935]:
            v,f,n,uv,mask,cavity,stats=sculpt(src,fid);meshes['body']=body_mesh(v,f,n,uv,mask,cavity).save(out,f'{fid}_body');entry['sculpt']=stats
            l,s,info=ivy(src,zone,fid,projector(v,f));meshes['new_leaves']=l.save(out,f'{fid}_new_leaves');meshes['new_stems']=s.save(out,f'{fid}_new_stems');entry['new_ivy']=info
        l,s,info=ivy(src,zone,fid);meshes['old_leaves']=l.save(out,f'{fid}_old_leaves');meshes['old_stems']=s.save(out,f'{fid}_old_stems');entry['old_ivy']=info;entry['meshes']=meshes;results.append(entry)
        print(fid,model['name'],'sculpt',entry.get('sculpt',{}).get('triangles',0),'ivy leaves',info['leaves'],'stem segments',info['stem_segments'],flush=True)
    data={'schema':1,'zone':207,'zone_sha256':hashlib.sha256((zone/'zone.json').read_bytes()).hexdigest(),'targets':results,'maps':json.loads((out/'downloads.json').read_text()),'mask_hashes':{name:hashlib.sha256((zone/'textures/x4plus'/name).read_bytes()).hexdigest() for name in ['hclimbvine.png','hbasevine.png']},'notes':['Original menhir meshes subdivided and sculpted offline; no in-game generation.','Ivy follows separate dark-overlay alpha/UV2 only; baked-in ivy in base textures is intentionally retained.','Original placement, buried base and physics are retained for this visual trial.']}
    for entry in results:
        for mesh in entry['meshes'].values():
            mesh['vertex_sha256']=hashlib.sha256((out/mesh['vertex_file']).read_bytes()).hexdigest();mesh['index_sha256']=hashlib.sha256((out/mesh['index_file']).read_bytes()).hexdigest()
    (out/'geometry.json').write_text(json.dumps(data,indent=2),encoding='utf-8')


if __name__=='__main__':main()
