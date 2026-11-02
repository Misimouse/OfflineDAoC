import unreal,json,traceback
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/training_staff_fx_pets';assets=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem);tools=unreal.AssetToolsHelpers.get_asset_tools();lib=unreal.MaterialEditingLibrary
report={'passed':False,'textures':0,'materials':[],'errors':[]}
try:
 unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(['/DAoCVisualBridge/SpellVisuals_v01'],True)
 textures=json.loads((R/'SourceSpellVisuals_v01/textures.json').read_text())
 tasks=[]
 for key,path in textures.items():
  dest='/DAoCVisualBridge/SpellVisuals_v01/Textures/T_'+key
  if assets.does_asset_exist(dest):continue
  t=unreal.AssetImportTask();t.filename=path;t.destination_path='/DAoCVisualBridge/SpellVisuals_v01/Textures';t.destination_name='T_'+key;t.automated=True;t.save=True;tasks.append(t)
 for i in range(0,len(tasks),20):tools.import_asset_tasks(tasks[i:i+20])
 report['textures']=len(textures)
 for mode,blend in [('Add',unreal.BlendMode.BLEND_ADDITIVE),('Alpha',unreal.BlendMode.BLEND_TRANSLUCENT)]:
  name='M_Spell'+mode;path='/DAoCVisualBridge/SpellVisuals_v01/'+name
  if assets.does_asset_exist(path):report['materials'].append(path);continue
  m=tools.create_asset(name,'/DAoCVisualBridge/SpellVisuals_v01',unreal.Material,unreal.MaterialFactoryNew());m.set_editor_property('blend_mode',blend);m.set_editor_property('two_sided',True);m.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
  t=lib.create_material_expression(m,unreal.MaterialExpressionTextureSampleParameter2D,-650,0);t.set_editor_property('parameter_name','Sprite');t.set_editor_property('texture',unreal.load_asset('/Engine/EngineResources/WhiteSquareTexture'))
  v=lib.create_material_expression(m,unreal.MaterialExpressionVertexColor,-650,220)
  tint=lib.create_material_expression(m,unreal.MaterialExpressionVectorParameter,-650,-200);tint.set_editor_property('parameter_name','Tint');tint.set_editor_property('default_value',unreal.LinearColor(1,1,1,1))
  op=lib.create_material_expression(m,unreal.MaterialExpressionScalarParameter,-650,400);op.set_editor_property('parameter_name','Opacity');op.set_editor_property('default_value',1)
  def mul(a,ao,b,bo,x,y):
   n=lib.create_material_expression(m,unreal.MaterialExpressionMultiply,x,y);lib.connect_material_expressions(a,ao,n,'A');lib.connect_material_expressions(b,bo,n,'B');return n
  col=mul(t,'RGB',v,'RGB',-400,0);col=mul(col,'',tint,'',-200,0);alpha=mul(t,'A',v,'A',-400,250);alpha=mul(alpha,'',op,'',-200,250)
  lib.connect_material_property(col,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR);lib.connect_material_property(alpha,'',unreal.MaterialProperty.MP_OPACITY);lib.recompile_material(m);assets.save_loaded_asset(m);report['materials'].append(path)
 report['passed']=True
except Exception:report['errors'].append(traceback.format_exc())
(D/'fx_import.json').write_text(json.dumps(report,indent=2));assert report['passed'],report['errors']
