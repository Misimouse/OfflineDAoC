import unreal,json
from pathlib import Path
R=Path(__file__).resolve().parent;catalog=json.loads((R/'equipment_catalog_v01.json').read_text())['models'];out={}
for ident in ['445','59','19','857']:
 row=catalog[ident];mesh=unreal.load_asset(row['asset']);materials=mesh.get_editor_property('materials') if row.get('type','static')=='skeletal' else mesh.get_editor_property('static_materials');values=[]
 for slot in materials:
  mat=slot.material_interface;names=unreal.MaterialEditingLibrary.get_vector_parameter_names(mat);entry={'asset':mat.get_path_name(),'parameters':[str(n)for n in names]}
  if isinstance(mat,unreal.MaterialInstanceConstant):
   entry['parent']=mat.get_editor_property('parent').get_path_name();entry['values']={}
   for name in names:
    c=unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(mat,name);entry['values'][str(name)]=[c.r,c.g,c.b,c.a]
  values.append(entry)
 out[ident]=values
(R/'Reports/training_staff_fx_pets/equipment_material_probe.json').write_text(json.dumps(out,indent=2))
