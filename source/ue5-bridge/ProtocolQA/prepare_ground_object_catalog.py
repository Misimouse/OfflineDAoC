"""Prepare measured rigid world-item descriptors while reusing installed canonical assets."""
import argparse,json,math,re
from pathlib import Path
from prepare_combined_expansion_data import digest


def quaternion(columns):
    matrix=[[columns[c][r] for c in range(3)] for r in range(3)]
    m=matrix;trace=sum(m[i][i] for i in range(3))
    if trace>0:
        s=math.sqrt(trace+1.0)*2;q=[(m[2][1]-m[1][2])/s,(m[0][2]-m[2][0])/s,(m[1][0]-m[0][1])/s,.25*s]
    else:
        k=max(range(3),key=lambda i:m[i][i]);j=(k+1)%3;l=(k+2)%3;s=math.sqrt(1+m[k][k]-m[j][j]-m[l][l])*2;q=[0.,0.,0.,0.];q[k]=.25*s;q[j]=(m[j][k]+m[k][j])/s;q[l]=(m[l][k]+m[k][l])/s;q[3]=(m[l][j]-m[j][l])/s
    length=math.sqrt(sum(x*x for x in q));return [x/length for x in q]


def verify_rotation(columns,q):
    x,y,z,w=q
    rotated=[[1-2*(y*y+z*z),2*(x*y+w*z),2*(x*z-w*y)],
             [2*(x*y-w*z),1-2*(x*x+z*z),2*(y*z+w*x)],
             [2*(x*z+w*y),2*(y*z-w*x),1-2*(x*x+y*y)]]
    assert max(abs(columns[c][r]-rotated[c][r]) for c in range(3) for r in range(3))<.00002
    return rotated


def prepare(workspace,install):
    lab=workspace/'GroundObjectsLab';proof=json.loads((lab/'geometry_verified.json').read_text());assert proof['passed']
    assert all(digest(Path(p))==h for p,h in proof['source_inputs'].items())
    frames=json.loads((lab/'geometry_frames.json').read_text());assert digest(lab/'geometry_frames.json')==proof['frames_sha256'] and frames['passed']
    native=json.loads((workspace/'equipment_catalog_v01.json').read_text());original_path=install/'new-client/godot/content/weapons/weapons.json';original=json.loads(original_path.read_text())['models'];exports={str(r['export_id']):r for r in json.loads((workspace/'SourceWeapons_All_v01/exported.json').read_text())['models']}
    catalogue=dict(version=1,coordinate_frame='Unreal centimetres, original ground-holder origin',fallback_model=488,models={},unsupported_animated=[],source_empty=[],missing_native=[])
    unique={}
    for model,entry in native['models'].items():
        kind=entry.get('type','static')
        if kind=='hidden':catalogue['source_empty'].append(int(model));continue
        if kind=='skeletal':catalogue['unsupported_animated'].append(int(model));continue
        key=re.search(r'/Equipment_All_v01/Model_(\d+)/',entry['asset']).group(1);row=frames['models'][key];assert original[model]['file']==exports[key]['info']['file']
        if key not in unique:
            f=row['canonical_to_world_godot'];basis=[[f[0],f[2],f[1]],[f[6],f[8],f[7]],[f[3],f[5],f[4]]];scale=[math.sqrt(sum(v*v for v in c)) for c in basis];unit=[[v/scale[k] for v in c] for k,c in enumerate(basis)]
            assert all(.0001<v<10000 for v in scale)
            assert max(abs(sum(unit[a][i]*unit[b][i] for i in range(3))) for a in range(3) for b in range(a+1,3))<.00002
            rotation=quaternion(unit);rotated=verify_rotation(unit,rotation)
            # One original float bone frame has minute nonorthogonality. Bound
            # its actual vertex error before expressing it as Unreal TRS.
            coordinates=[max(abs(p[k]) for p in entry['canonical_bounds_cm']) for k in range(3)]
            errors=[sum(abs(basis[c][r]-rotated[c][r]*scale[c])*coordinates[c] for c in range(3)) for r in range(3)]
            bound=math.sqrt(sum(e*e for e in errors));assert bound<.01,(model,bound)
            unique[key]=dict(asset=entry['asset'],type='static',world_transform=dict(translation_cm=[f[9]*100,f[11]*100,f[10]*100],quaternion_xyzw=rotation,scale=scale),original_world_bounds_cm=[[p[0]*100,p[2]*100,p[1]*100] for p in row['world_bounds_m']],source_vertices=row['vertices'],representation_error_bound_cm=bound)
        catalogue['models'][model]=dict(unique[key],original_name=original[model].get('name',''))
    catalogue['missing_native']=[int(k) for k in original if k not in native['models']]
    assert len(catalogue['models'])==1021 and len(unique)==918 and all(str(k) in catalogue['models'] for k in [145,488,636,637])
    output=lab/'world_catalog_candidate.json';output.write_text(json.dumps(catalogue,indent=2))
    result=dict(passed=True,installed=False,normal_runtime_modified=False,models=1021,unique_assets=918,max_representation_error_bound_cm=max(r['representation_error_bound_cm'] for r in unique.values()),new_meshes=0,new_textures=0,unsupported_animated=len(catalogue['unsupported_animated']),source_empty=len(catalogue['source_empty']),missing_native=len(catalogue['missing_native']),candidate=str(output),sha256=digest(output),source_inputs={str(p):digest(p) for p in [lab/'geometry_verified.json',lab/'geometry_frames.json',workspace/'equipment_catalog_v01.json',original_path]})
    (lab/'catalogue_verified.json').write_text(json.dumps(result,indent=2));return {k:v for k,v in result.items() if k!='source_inputs'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['workspace','install']:p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();print(json.dumps(prepare(a.workspace.resolve(),a.install.resolve())))
