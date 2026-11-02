import json,hashlib
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/equipment'
data=json.loads((D/'import.json').read_text());assert data['complete']and not data['errors']
models={}
for ident,row in data['models'].items():
 assert row['bounds_max_error_cm']<.1 and row['bone_translation_error_cm']<.1
 models[ident]={'asset':row['asset'],'canonical_bone':row['canonical_bone'],'reference':{'translation_cm':row['bone_reference_translation_cm'],'quaternion_xyzw':row['bone_reference_quaternion'],'scale':row['bone_reference_scale']},'info':row['info'],'canonical_bounds_cm':row['bounds_cm']}
output=R/'equipment_catalog_v01.json';output.write_text(json.dumps({'version':1,'source':'original client geometry and bind frames','models':models},indent=2))
(D/'catalog.json').write_text(json.dumps({'prepared':True,'active':False,'models':list(models),'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'source_geometry_verified':True,'bind_frames_verified':True},indent=2));print('Prepared dormant equipment catalog:',list(models))
