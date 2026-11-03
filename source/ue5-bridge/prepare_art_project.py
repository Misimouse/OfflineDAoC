"""Preview/apply a shared Unreal project binding without changing art or maps."""
import argparse,datetime,hashlib,json,os,re,shutil,subprocess
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--bridge-root',required=True,type=Path)
parser.add_argument('--art-project',required=True,type=Path)
parser.add_argument('--map',required=True)
parser.add_argument('--apply',action='store_true')
args=parser.parse_args()
bridge=args.bridge_root.resolve(strict=True);project=args.art_project.resolve(strict=True)
assert project.suffix.lower()=='.uproject'
assert re.fullmatch(r'/Game/[A-Za-z0-9_]+(?:/[A-Za-z0-9_]+)*',args.map)
map_file=project.parent/'Content'/(args.map[6:]+'.umap');assert map_file.is_file()
plugin=(bridge/'Client/Plugins/DAoCVisualBridge').resolve(strict=True)
assert plugin.is_relative_to(bridge) and (plugin/'DAoCVisualBridge.uplugin').is_file()
assert (plugin/'Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll').is_file()
link=project.parent/'Plugins/DAoCVisualBridge'
if link.exists():assert link.resolve()==plugin,'Preserve the different plugin already in this project.'
if link.parent.exists():assert link.parent.resolve().is_relative_to(project.parent)
original=project.read_bytes();descriptor=json.loads(original.decode('utf-8-sig'))
assert str(descriptor.get('EngineAssociation',''))=='5.8','Review plugin compatibility for another engine.'
references=descriptor.setdefault('Plugins',[])
entry=next((x for x in references if x.get('Name')=='DAoCVisualBridge'),None)
if entry is None:references.append({'Name':'DAoCVisualBridge','Enabled':False})
else:entry['Enabled']=False
config=bridge/'playable_project.json'
target={'managed_by':'DAoCVisualBridge','version':1,'project':os.path.relpath(project,bridge).replace('\\','/'),'map':args.map,'enable_plugins':['DAoCVisualBridge']}
if config.exists():assert json.loads(config.read_text()).get('managed_by')=='DAoCVisualBridge','Preserve the existing launcher configuration.'
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report={'managed_by':'DAoCVisualBridge','version':1,'applied':False,'plugin_link_created':not link.exists(),'previous_project_sha256':hashlib.sha256(original).hexdigest(),'project':str(project),'map':args.map,'map_sha256':digest(map_file),'plugin_link':str(link),'plugin_source':str(plugin),'editor_plugin_enabled':False,'runtime_plugin_enabled':True,'art_content_modified':False,'profiles':[]}
if args.apply:
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup=bridge/'Backups'/('SharedArtProject_'+stamp);backup.mkdir(parents=True)
    shutil.copy2(project,backup/project.name)
    if config.exists():shutil.copy2(config,backup/config.name)
    assert project.read_bytes()==original,'The project descriptor changed during preparation.'
    if not link.exists():
        link.parent.mkdir(exist_ok=True)
        environment=dict(os.environ,DAOC_PLUGIN_LINK=str(link),DAOC_PLUGIN_TARGET=str(plugin))
        subprocess.run(['powershell','-NoProfile','-Command','New-Item -ItemType Junction -Path $env:DAOC_PLUGIN_LINK -Target $env:DAOC_PLUGIN_TARGET | Out-Null'],env=environment,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
    assert link.resolve()==plugin
    project.write_bytes((json.dumps(descriptor,indent='\t',ensure_ascii=False)+'\n').encode('utf-8'))
    config.write_bytes((json.dumps(target,indent=2)+'\n').encode('utf-8'))
    source=bridge/'Client/Saved';saved=project.parent/'Saved';saved.mkdir(exist_ok=True)
    for item in source.glob('*.json'):
        if item.name!='DAoCControls.json' and not re.fullmatch(r'DAoCClassicUI_[0-9a-fA-F]{8}\.json',item.name):continue
        destination=saved/item.name
        if destination.exists():
            report['profiles'].append({'name':item.name,'action':'preserved_existing'});continue
        shutil.copy2(item,destination);report['profiles'].append({'name':item.name,'action':'copied','sha256':digest(destination)})
    assert digest(map_file)==report['map_sha256'],'An art map changed during project configuration.'
    report.update(applied=True,backup=str(backup),project_sha256=digest(project),configuration=str(config),configuration_sha256=digest(config))
folder=bridge/'Reports/shared_project';folder.mkdir(parents=True,exist_ok=True)
(folder/('installation.json' if args.apply else 'preview.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
