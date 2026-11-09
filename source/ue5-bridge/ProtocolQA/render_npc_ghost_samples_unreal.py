"""Private source/ghost/restored scene captures. No active world or original material writes."""
import json,os,time,traceback,math
from pathlib import Path
import unreal
lab=Path(os.environ['DAOC_NPC_GHOST_LAB']).resolve();out=Path(os.environ.get('DAOC_NPC_GHOST_RENDER_OUTPUT',str(lab/'RenderAcceptance'))).resolve();assert out.is_relative_to(lab);out.mkdir(parents=True,exist_ok=True);samples=json.loads((lab/'samples_imported.json').read_text());prepared=json.loads((lab/'MaterialsCandidate/prepared.json').read_text());assert samples['passed'] and prepared['passed'] and prepared['originals_unchanged']
world=unreal.EditorLevelLibrary.get_editor_world();actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);report=dict(passed=False,installed=False,captures={},errors=[]);owned=[];render_materials=[]
def spawn(cls,pos=unreal.Vector(),rot=unreal.Rotator()):
 a=actors.spawn_actor_from_class(cls,pos,rot,transient=True);owned.append(a);return a
def save_capture(capture,target,path):
 unreal.SystemLibrary.execute_console_command(world,'Editor.AsyncAssetCompilationFinishAll')
 for material in render_materials:unreal.MaterialEditingLibrary.get_statistics(material)
 for _ in range(3):capture.capture_scene();time.sleep(.3)
 unreal.RenderingLibrary.export_render_target(world,target,str(path.parent),path.name)
 assert path.is_file(),str(path)
try:
 unreal.SystemLibrary.execute_console_command(world,'r.CustomDepth 3')
 for ident in ['110','307']:
  entry=samples['models'][ident];mesh=unreal.load_asset(entry['asset']);assert isinstance(mesh,unreal.SkeletalMesh)
  avatar=spawn(unreal.SkeletalMeshActor);body=avatar.skeletal_mesh_component;body.set_skeletal_mesh_asset(mesh);body.set_editor_property('cast_shadow',False)
  clip=unreal.load_asset(entry['idle']);body.play_animation(clip,False);body.set_position(.25,False);body.set_editor_property('pause_anims',True)
  original=[body.get_material(i) for i in range(body.get_num_materials())];render_materials[:]=original
  proxy=spawn(unreal.SkeletalMeshActor);depth=proxy.skeletal_mesh_component;depth.set_skeletal_mesh_asset(mesh);depth.play_animation(clip,False);depth.set_position(.25,False);depth.set_editor_property('pause_anims',True);depth.set_editor_property('render_in_main_pass',False);depth.set_editor_property('render_in_depth_pass',False);depth.set_editor_property('cast_shadow',False);depth.set_render_custom_depth(False)
  center,extent=avatar.get_actor_bounds(False);panel=spawn(unreal.StaticMeshActor,unreal.Vector(center.x,center.y-100,center.z));panel.static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE);panel.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube.Cube'));panel.set_actor_scale3d(unreal.Vector(6,.05,5));panel.static_mesh_component.set_material(0,unreal.load_asset('/Engine/EngineMaterials/WorldGridMaterial.WorldGridMaterial'));render_materials.append(panel.static_mesh_component.get_material(0))
  light=spawn(unreal.DirectionalLight,rot=unreal.Rotator(-20,-90,0));light.light_component.set_mobility(unreal.ComponentMobility.MOVABLE);light.light_component.set_intensity(0.0)
  fill=spawn(unreal.DirectionalLight,rot=unreal.Rotator(-20,30,0));fill.light_component.set_mobility(unreal.ComponentMobility.MOVABLE);fill.light_component.set_intensity(0.0)
  lamp=spawn(unreal.PointLight,unreal.Vector(center.x,center.y+150,center.z+100));lamp.light_component.set_mobility(unreal.ComponentMobility.MOVABLE);lamp.light_component.set_editor_property('intensity_units',unreal.LightUnits.LUMENS);lamp.light_component.set_intensity(800.0);lamp.light_component.set_attenuation_radius(3000.0);lamp.light_component.set_editor_property('cast_shadows',False)
  owner=spawn(unreal.SceneCapture2D);capture=owner.get_component_by_class(unreal.SceneCaptureComponent2D);capture.set_editor_property('capture_every_frame',False);capture.set_editor_property('capture_on_movement',False);capture.set_editor_property('capture_source',unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR);capture.set_editor_property('primitive_render_mode',unreal.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST);capture.set_editor_property('show_only_actors',[avatar,proxy,panel]);capture.set_editor_property('fov_angle',40)
  pp=capture.get_editor_property('post_process_settings');pp.set_editor_property('override_auto_exposure_method',True);pp.set_editor_property('auto_exposure_method',unreal.AutoExposureMethod.AEM_MANUAL);pp.set_editor_property('override_auto_exposure_apply_physical_camera_exposure',True);pp.set_editor_property('auto_exposure_apply_physical_camera_exposure',False);pp.set_editor_property('override_bloom_intensity',True);pp.set_editor_property('bloom_intensity',0);capture.set_editor_property('post_process_settings',pp)
  target=unreal.RenderingLibrary.create_render_target2d(world,512,768,unreal.TextureRenderTargetFormat.RTF_RGBA8,unreal.LinearColor(.08,.08,.08,1));capture.set_editor_property('texture_target',target)
  distance=max(extent.x/.364,extent.z/(.364*1.5))*1.35+extent.y;eye=unreal.Vector(center.x,center.y+distance,center.z);owner.set_actor_location(eye,False,False);owner.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(eye,center),False)
  capture.set_editor_property('show_only_actors',[panel]);save_capture(capture,target,out/(ident+'_background.png'))
  capture.set_editor_property('show_only_actors',[avatar,proxy,panel]);time.sleep(2);save_capture(capture,target,out/(ident+'_ordinary.png'))
  for i,material in enumerate(original):
   replacement=unreal.load_asset(prepared['materials'][material.get_path_name()]);assert replacement
   if isinstance(replacement,unreal.MaterialInstanceConstant):unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(replacement,'BridgeGhostDepthKnown',0.0);unreal.MaterialEditingLibrary.update_material_instance(replacement)
   body.set_material(i,replacement);render_materials.append(replacement)
  depth.set_render_custom_depth(True);time.sleep(2);save_capture(capture,target,out/(ident+'_ghost_unfiltered.png'))
  for i in range(body.get_num_materials()):
   material=body.get_material(i)
   if isinstance(material,unreal.MaterialInstanceConstant):unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(material,'BridgeGhostDepthKnown',1.0);unreal.MaterialEditingLibrary.update_material_instance(material)
  save_capture(capture,target,out/(ident+'_ghost.png'))
  for i,material in enumerate(original):body.set_material(i,material)
  depth.set_render_custom_depth(False);save_capture(capture,target,out/(ident+'_restored.png'))
  for angle in [90,180,270]:
   radians=math.radians(angle);dx=-math.sin(radians);dy=math.cos(radians)
   eye=unreal.Vector(center.x+dx*distance,center.y+dy*distance,center.z);owner.set_actor_location(eye,False,False);owner.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(eye,center),False)
   owned.remove(panel);actors.destroy_actor(panel);owned.remove(lamp);actors.destroy_actor(lamp)
   panel=spawn(unreal.StaticMeshActor,unreal.Vector(center.x-dx*100,center.y-dy*100,center.z),unreal.Rotator(pitch=0,yaw=angle,roll=0));panel.static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE);panel.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube.Cube'));panel.set_actor_scale3d(unreal.Vector(6,.05,5));panel.static_mesh_component.set_material(0,unreal.load_asset('/Engine/EngineMaterials/WorldGridMaterial.WorldGridMaterial'))
   lamp=spawn(unreal.PointLight,unreal.Vector(center.x+dx*150,center.y+dy*150,center.z+100));lamp.light_component.set_mobility(unreal.ComponentMobility.MOVABLE);lamp.light_component.set_editor_property('intensity_units',unreal.LightUnits.LUMENS);lamp.light_component.set_intensity(800.0);lamp.light_component.set_attenuation_radius(3000.0);lamp.light_component.set_editor_property('cast_shadows',False)
   capture.set_editor_property('show_only_actors',[avatar,proxy,panel])
   capture.set_editor_property('show_only_actors',[panel]);save_capture(capture,target,out/(ident+'_'+str(angle)+'_background.png'))
   capture.set_editor_property('show_only_actors',[avatar,proxy,panel]);save_capture(capture,target,out/(ident+'_'+str(angle)+'_ordinary.png'))
   for i,material in enumerate(original):body.set_material(i,unreal.load_asset(prepared['materials'][material.get_path_name()]))
   depth.set_render_custom_depth(True);save_capture(capture,target,out/(ident+'_'+str(angle)+'_ghost.png'))
   for i,material in enumerate(original):body.set_material(i,material)
   depth.set_render_custom_depth(False);save_capture(capture,target,out/(ident+'_'+str(angle)+'_restored.png'))
  report['captures'][ident]=[str(out/(ident+'_'+name+'.png')) for name in ['ordinary','ghost','restored']]
  for actor in list(owned):actors.destroy_actor(actor)
  owned.clear()
 report['passed']=True
except Exception:report['errors'].append(traceback.format_exc())
finally:
 for actor in owned:actors.destroy_actor(actor)
(out/'capture_result.json').write_text(json.dumps(report,indent=2));assert report['passed'],report['errors']
