"""Add only the original point bitmap and lossless mesh coordinates for UE."""
import argparse,base64,json,hashlib,shutil,struct
from pathlib import Path
from prepare_combined_expansion_data import digest

def prepare(workspace,install):
    source=install/'new-client/godot/content/ui/gtarget';lab=workspace/'GroundTargetLab';private=lab/'Resources/GroundTarget_v01';private.mkdir(parents=True,exist_ok=True)
    model=source/'model.gltf';data=json.loads(model.read_text());assert len(data['buffers'])==1 and len(data['nodes'])==1 and data['nodes'][0]=={'name':'Editable Mesh','mesh':0}
    raw=base64.b64decode(data['buffers'][0]['uri'].split(',',1)[1]);assert len(raw)==data['buffers'][0]['byteLength']
    def values(i):
        a=data['accessors'][i];b=data['bufferViews'][a['bufferView']];fmt={5126:'f',5125:'I'}[a['componentType']];size={'VEC3':3,'VEC2':2,'SCALAR':1}[a['type']];assert 'byteStride' not in b
        offset=b.get('byteOffset',0)+a.get('byteOffset',0);return [list(struct.unpack_from('<'+fmt*size,raw,offset+n*4*size)) for n in range(a['count'])]
    mesh=dict(vertices=values(0),normals=values(1),uv=values(2),indices=[v[0] for v in values(3)],original_scale=.7,tile_m=2.0,source_sha256=digest(model));assert len(mesh['vertices'])==24 and len(mesh['indices'])==36
    (private/'model.json').write_text(json.dumps(mesh,indent=2));shutil.copy2(source/'target.png',private/'target.png')
    plugin=workspace/'Client/Plugins/DAoCVisualBridge/Content/GroundTarget_v01';plugin.mkdir(parents=True,exist_ok=True);files=[]
    for origin in sorted(private.iterdir()):
        target=plugin/origin.name
        if target.exists():assert digest(target)==digest(origin),'Refuse overwriting existing private content'
        else:shutil.copy2(origin,target)
        files.append(dict(source=str(origin),target=str(target),sha256=digest(target)))
    report=dict(passed=True,original_art_modified=False,world_map_modified=False,source_inputs={str(p):digest(p) for p in [model,source/'target.png']},files=files,original_model_vertices=24,original_model_indices=36,original_tile_m=2.0)
    (lab/'resources.json').write_text(json.dumps(report,indent=2));return dict(passed=True,files=len(files),original_art_modified=False)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--install',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.workspace.resolve(),a.install.resolve())))
