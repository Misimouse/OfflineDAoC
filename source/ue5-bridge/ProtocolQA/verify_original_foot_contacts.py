"""Independently sample the original Godot foot-contact implementation."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
from prepare_combined_expansion_data import digest

parser=argparse.ArgumentParser(description=__doc__)
for key in ['workspace','install','engine']:parser.add_argument('--'+key,type=Path,required=True)
args=parser.parse_args();w=args.workspace.resolve();repo=Path(__file__).resolve().parents[3];root=w/'FootstepAudioLab/OriginalContacts'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');root.mkdir(parents=True)
assert not (w/'FootstepAudioLab/installed.json').exists(),'Footstep delivery is sealed; do not rewrite its original timing proof'
models=json.loads((w/'Reports/footstep_audio/coverage.json').read_text())['models']
tasks={str(row['id']):row for path in [w/'SourceModels/tasks.json',w/'ExpansionRaceLab/OriginalTasks/tasks.json'] for row in json.loads(path.read_text())}
inputs={mid:{'race':row['race'],'gltf':tasks[mid]['info'].get('gltf','')} for mid,row in models.items()}
(root/'tasks.json').write_text(json.dumps(inputs),encoding='utf-8')
project=json.loads((w/'Reports/protocol_qa/prepared.json').read_text());qa=Path(project['root']);assert qa.is_relative_to(w/'ProtocolQA')
sdk=args.engine/'Binaries/ThirdParty/DotNet/10.0/win-x64';env=dict(os.environ,DOTNET_ROOT=str(sdk),DOTNET_ROOT_X64=str(sdk),PATH=str(sdk)+os.pathsep+os.environ['PATH'],APPDATA=str(root/'AppData'),LOCALAPPDATA=str(root/'LocalAppData'))
for key in ['APPDATA','LOCALAPPDATA']:Path(env[key]).mkdir()
script=repo/'source/ue5-bridge/Godot/export_original_foot_contacts.gd';helper=repo/'source/new-client/godot/game/character_sounds.gd'
assert digest(helper)==digest(qa/'LobbyProject/game/character_sounds.gd')
bind={str(path):digest(path) for path in [script,helper,qa/'LobbyProject/game/fig3_figure.gd',root/'tasks.json']}
command=[str(args.install/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'),'--headless','--path',str(qa/'LobbyProject'),'--script',str(script),'--','--footstep-tasks='+str(root/'tasks.json'),'--footstep-output='+str(root/'contacts.json'),'--footstep-original-helper=res://game/character_sounds.gd']
with (root/'godot.log').open('w',encoding='utf-8') as log:result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,env=env,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
assert result.returncode==0,'Inspect '+str(root/'godot.log')
report=json.loads((root/'contacts.json').read_text());assert report['passed'] and set(report['models'])==set(models)
for mid,row in report['models'].items():
    for clip,data in row.items():
        assert data['length']>0 and data['contacts'],(mid,clip)
        assert data['contacts']==sorted(set(data['contacts'])) and all(0<=t<data['length'] for t in data['contacts'])
assert all(digest(Path(path))==sha for path,sha in bind.items())
report['source_inputs']=bind;report['server_started']=False;report['normal_installation_modified']=False
(root/'verified.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
resources_path=w/'FootstepAudioLab/resources.json';resources=json.loads(resources_path.read_text());assert not resources['installed']
catalog=Path(resources['catalog']);assert digest(catalog)==resources['catalog_sha256']
index=json.loads(catalog.read_text());assert set(index['local_player_models'])==set(report['models'])
for mid,data in report['models'].items():index['local_player_models'][mid]['contacts']=data
catalog.write_text(json.dumps(index,indent=1),encoding='utf-8');resources['catalog_sha256']=digest(catalog)
resources['original_contacts_receipt']=str(root/'verified.json');resources['original_contacts_receipt_sha256']=digest(root/'verified.json')
resources_path.write_text(json.dumps(resources,indent=2),encoding='utf-8')
print(json.dumps({'passed':True,'models':len(models),'report_directory':str(root)}))
