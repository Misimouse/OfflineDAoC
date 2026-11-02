"""Compile an independent instancing-capable copy of the approved bark graph.
Runtime copies uniform parameters from the current original instance, so UV,
colour/normal/roughness textures and artistic values stay source-controlled.
"""
import unreal,json,hashlib,traceback
from pathlib import Path
R=Path(__file__).resolve().parent;A=R.parent/'DAoC-Enhanced-Unreal';O=R/'Reports/compatibility';O.mkdir(exist_ok=True)
SRC='/Game/DAoC/Connacht_v01/Ardee_Giant_Grove_v01/Approved_Dark_Bark_v01/Materials';DST='/DAoCVisualBridge/Compatibility/GroveBark_v01';report={'complete':False,'originals_unchanged':False,'errors':[]}
def write():(O/'bark_assets.json').write_text(json.dumps(report,indent=2))
try:
 E=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
 if E is None:E=unreal.EditorAssetSubsystem()
 T=unreal.AssetToolsHelpers.get_asset_tools();M=unreal.MaterialEditingLibrary
 protected={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (A/'Content/DAoC/Connacht_v01/Ardee_Giant_Grove_v01/Approved_Dark_Bark_v01/Materials').glob('*.uasset')}
 original=E.load_asset(SRC+'/M_GiantOak_Dark_Approved');assert original
 assert not E.does_asset_exist(DST+'/M_GroveBark_Instanced')
 copy=T.duplicate_asset('M_GroveBark_Instanced',DST,original);assert copy
 M.set_material_usage(copy,unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
 M.recompile_material(copy);E.save_loaded_asset(copy,only_if_is_dirty=False)
 assert M.has_material_usage(copy,unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
 for path,h in protected.items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==h,path
 report.update(complete=True,originals_unchanged=True,private_master=copy.get_path_name(),original_assets_sha256=protected,original_master=original.get_path_name(),usage='InstancedStaticMeshes',uniform_parameters_copied_at_runtime=True,scope='only the three approved giant oak bark instances; no leaf/birch changes')
except Exception:report['errors'].append(traceback.format_exc());raise
finally:write()
