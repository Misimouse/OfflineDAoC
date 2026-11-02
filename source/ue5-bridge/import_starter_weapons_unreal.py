"""Import dormant weapon samples and measure coordinates against the body skeleton."""
import json,traceback,re
from pathlib import Path
import unreal
R=Path(__file__).resolve().parent;D=R/'Reports/equipment';O=D/'import.json'
assets=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem);tools=unreal.AssetToolsHelpers.get_asset_tools()
report={'complete':False,'active':False,'models':{},'errors':[]}
def xyz(v):return [v.x,v.y,v.z]
def save():O.write_text(json.dumps(report,indent=2))
try:
 data=json.loads((R/'SourceWeapons_v01/exported.json').read_text());assert data['complete']
 registry=unreal.AssetRegistryHelpers.get_asset_registry();registry.scan_paths_synchronous(['/DAoCVisualBridge/Equipment_v01'],True)
 body_catalog=json.loads((R/'models_animations_v02.json').read_text());body=unreal.load_asset(body_catalog['1984']['asset'])
 modifier=unreal.SkeletonModifier();assert modifier.set_skeletal_mesh(body)
 names=[str(n)for n in modifier.get_all_bone_names()];report['attachment_bones']=[n for n in names if any(k in n.lower()for k in ['held','shield','belt','back'])]
 for row in data['models']:
  ident=str(row['model']);destination='/DAoCVisualBridge/Equipment_v01/Model_'+ident
  existing=assets.list_assets(destination,recursive=True,include_folder=False)
  if not existing:
   task=unreal.AssetImportTask();task.filename=row['file'];task.destination_path=destination;task.automated=True;task.save=True;task.replace_existing=False;tools.import_asset_tasks([task]);existing=assets.list_assets(destination,recursive=True,include_folder=False)
  meshes=[unreal.load_asset(p)for p in existing];meshes=[m for m in meshes if isinstance(m,unreal.StaticMesh)];assert len(meshes)==1
  mesh=meshes[0];bounds=mesh.get_bounds();actual=[xyz(bounds.origin-bounds.box_extent),xyz(bounds.origin+bounds.box_extent)]
  # GLTFCore/Private/GLTF/ConversionUtilities.h ConvertVec3 is (X,Z,Y).
  expected=[[p[0]*100,p[2]*100,p[1]*100]for p in row['bounds_m']]
  max_error=max(abs(actual[a][b]-expected[a][b])for a in range(2)for b in range(3));assert max_error<.1,('weapon geometry coordinate conversion',ident,actual,expected)
  normalize=lambda name:re.sub(r'[-_ ]','',name).casefold()
  wanted=normalize(row['canonical_bone']);matches=[n for n in names if normalize(n)==wanted];assert len(matches)==1,(row['canonical_bone'],matches)
  bone=matches[0];transform=modifier.get_bone_transform(bone,True)
  frame=row['canonical_godot_frame'];expected_origin=[frame[9]*100,frame[11]*100,frame[10]*100];origin=xyz(transform.translation);bone_error=max(abs(a-b)for a,b in zip(origin,expected_origin))
  report['models'][ident]={'asset':mesh.get_path_name(),'bounds_cm':actual,'expected_bounds_cm':expected,'bounds_max_error_cm':max_error,'canonical_bone':bone,'bone_reference_translation_cm':origin,'expected_bone_translation_cm':expected_origin,'bone_translation_error_cm':bone_error,'bone_reference_quaternion':[transform.rotation.x,transform.rotation.y,transform.rotation.z,transform.rotation.w],'bone_reference_scale':xyz(transform.scale3d),'vertices':row['vertices'],'info':row['info']};save()
  assert bone_error<.1,('body/weapon reference-frame mismatch',ident,bone_error)
 report['complete']=True;save()
except Exception:
 report['errors'].append(traceback.format_exc());save();raise
