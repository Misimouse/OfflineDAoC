from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parent
for folder in ['Reports/training_staff_fx_pets','Reports/ui_integration','Reports/isolated-save','Reports/live','SourceModels','Client/Plugins','GMCombatTest/NativeHost/Plugins']:
 (ROOT/folder).mkdir(parents=True,exist_ok=True)
source=ROOT/'UnrealPlugin/DAoCVisualBridge'
for host in ['Client','GMCombatTest/NativeHost']:
 target=ROOT/host/'Plugins/DAoCVisualBridge'
 for part in ['Source']:
  shutil.copytree(source/part,target/part,dirs_exist_ok=True)
 shutil.copy2(source/'DAoCVisualBridge.uplugin',target/'DAoCVisualBridge.uplugin')
print('Source plugin staged. Supply your own local content and generated catalogues before running a game.')
