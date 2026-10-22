"""Bake two water detail levels offline, using exactly the stock quad footprint."""
from pathlib import Path
import argparse, collections, hashlib, json, math
import numpy as np

PROJECT=Path(__file__).resolve().parents[2]
STATE=PROJECT/'.enhanced-session/water_trial'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def ground(points,heights,size):
    coords=np.clip(points[:,[0,2]]/size*(len(heights)-1),0,len(heights)-1.001)
    ix=np.floor(coords).astype(int);f=coords-ix;x,z=ix.T;fx,fz=f.T
    return (heights[z,x]*(1-fx)+heights[z,x+1]*fx)*(1-fz)+(heights[z+1,x]*(1-fx)+heights[z+1,x+1]*fx)*fz

def build(quads,spacing,level,heights,size):
    vertices=[];faces=[];lookup={}
    for quad in quads:
        lo=quad.min(0);hi=quad.max(0)
        nx=max(1,round((hi[0]-lo[0])/spacing));nz=max(1,round((hi[2]-lo[2])/spacing))
        grid=[]
        for j in range(nz+1):
            row=[]
            for i in range(nx+1):
                x=round(float(lo[0]+(hi[0]-lo[0])*i/nx),4);z=round(float(lo[2]+(hi[2]-lo[2])*j/nz),4)
                key=(round(x*1000),round(z*1000))
                if key not in lookup:lookup[key]=len(vertices);vertices.append([x,level,z])
                row.append(lookup[key])
            grid.append(row)
        for j in range(nz):
            for i in range(nx):
                a,b,c,d=grid[j][i],grid[j][i+1],grid[j+1][i],grid[j+1][i+1]
                faces.extend([[a,b,c],[b,d,c]])
    p=np.asarray(vertices,dtype=np.float32)
    depth=np.clip((level-ground(p,heights,size))/4,0,1)
    raw=np.column_stack([p,depth]).astype('<f4');indices=np.asarray(faces,dtype='<u4')
    assert np.isfinite(raw).all() and len(indices)>0
    return raw,indices

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=STATE);parser.add_argument('--near-spacing',type=float,default=0.8);args=parser.parse_args()
    target=args.out.resolve();assert target.is_relative_to(STATE.resolve());assert args.near_spacing in [0.4,0.8]
    target.mkdir(exist_ok=True,parents=True)
    export=json.loads((STATE/'export.json').read_text(encoding='utf-8'));zone=PROJECT/'content/zones/zone207';info=json.loads((zone/'zone.json').read_text(encoding='utf-8'))
    for rel,h in export['source_hashes'].items():assert sha(PROJECT/rel)==h
    h=np.fromfile(zone/info['heights_2x'],dtype='<f4').reshape(info['heights_2x_size'],info['heights_2x_size'])
    entries=[];total=collections.Counter()
    for body in export['bodies']:
        raw=Path(body['file']);assert sha(raw)==body['sha256'];quads=np.fromfile(raw,dtype='<f4').reshape(-1,6,3)
        chunks=collections.defaultdict(list)
        for quad in quads:
            lo=quad.min(0);key=tuple(np.floor((lo[[0,2]]+0.01)/51.2).astype(int));chunks[key].append(quad)
        for key,quadlist in sorted(chunks.items()):
            name=f"{body['name']}_{key[0]}_{key[1]}";entry={'name':name,'body':body['name'],'height':body['height'],'quads':len(quadlist)}
            for kind,spacing in [('near',args.near_spacing),('far',6.4)]:
                v,f=build(quadlist,spacing,body['height'],h,info['size_m'])
                vp=target/(name+'_'+kind+'.vtx');fp=vp.with_suffix('.idx');vp.write_bytes(v.tobytes());fp.write_bytes(f.tobytes())
                entry[kind]={'vertex_file':vp.name,'index_file':fp.name,'vertices':len(v),'triangles':len(f),'vertex_sha256':sha(vp),'index_sha256':sha(fp)}
                total[kind+'_triangles']+=len(f)
            entries.append(entry)
        print('WATER_BAKED',body['name'],'quads',len(quads),'chunks',len(chunks),flush=True)
    result={'zone':207,'source_hashes':export['source_hashes'],'bodies':export['bodies'],'chunks':entries,'totals':dict(total),'near_spacing_m':args.near_spacing,'chunk_size_m':51.2,'maximum_wave_amplitude_m':0.04,'detail_switch_m':140,'wave_fade_start_m':45,'wave_fade_end_m':85,'note':'Exact original quad footprint and nominal level; offline geometry only, original swimming and collisions unchanged.'}
    (target/'geometry.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('WATER_GEOMETRY_OK',len(entries),dict(total))

if __name__=='__main__':main()
