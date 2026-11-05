"""Snapshot a stopped, successful disposable test for local owner review only."""
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import xml.etree.ElementTree as ET


def junction(source, target):
    assert source.is_dir() and not target.exists()
    quote = lambda value: "'" + str(value).replace("'", "''") + "'"
    command = 'New-Item -ItemType Junction -Path '+quote(target)+' -Target '+quote(source)+' | Out-Null'
    subprocess.run(['powershell', '-NoProfile', '-Command', command], check=True, capture_output=True)


def export(run, database, server, workspace, output, account, password, classes):
    run, database, server, workspace, output = (Path(p).resolve() for p in (run, database, server, workspace, output))
    lab = workspace/'ExpansionRaceLab'
    assert run.is_relative_to(workspace/'ProtocolQA') and database.is_relative_to(run) and server.is_relative_to(run)
    assert output.is_relative_to(lab) and not output.exists(), 'Never overwrite an existing review session'
    with sqlite3.connect(database) as db:
        assert db.execute('SELECT RunId FROM CodexQaIsolationMarker').fetchone()[0] == run.name
        assert db.execute('SELECT COUNT(*) FROM DOLCharacters WHERE AccountName=? AND Race=21 AND Class IN (43,44,45,46)', (account,)).fetchone()[0] == 4
    output.mkdir(parents=True)
    target_server=output/'runtime/server'
    shutil.copytree(server,target_server)
    target_db=output/'runtime/data/review.sqlite3.db';target_db.parent.mkdir()
    with sqlite3.connect(database) as source, sqlite3.connect(target_db) as destination:
        source.backup(destination)
        destination.execute('UPDATE Account SET PrivLevel=3 WHERE Name=?',(account,))
    config=target_server/'config/serverconfig.xml';tree=ET.parse(config);node=tree.getroot().find('Server')
    for key,value in {'Port':'10361','RegionPort':'10461','UdpPort':'10461',
                      'ServerName':'Isolated Minotaur owner review','ServerNameShort':'MinoReview',
                      'DBConnectionString':'Data Source='+str(target_db)+';Version=3;Pooling=True;Journal Mode=WAL;Synchronous=Normal;Foreign Keys=True;Default Timeout=60'}.items():
        node.find(key).text=value
    tree.write(config,encoding='utf-8',xml_declaration=True)
    project=output/'GodotProject';project.mkdir()
    original=run/'LobbyProject'
    for name in ['game','.godot']:
        shutil.copytree(original/name,project/name)
    shutil.copy2(original/'project.godot',project/'project.godot')
    classes=Path(classes).resolve()
    shutil.copy2(classes,output/'server_classes.json')
    net=project/'game/net/server.gd';text=net.read_text(encoding='utf-8-sig')
    assert text.count(classes.as_posix())==1
    net.write_text(text.replace(classes.as_posix(),(output/'server_classes.json').as_posix()),encoding='utf-8')
    junction((original/'content').resolve(),project/'content')
    shutil.copytree(run/'Godot',output/'Godot')
    (output/'SourceModels').mkdir()
    shutil.copy2(run/'SourceModels/tasks.json',output/'SourceModels/tasks.json')
    lobby=output/'Godot/character_lobby.gd';text=lobby.read_text(encoding='utf-8-sig')
    anchor='    var action:=String(value.get("action",""))\n'
    assert text.count(anchor)==1
    text=text.replace(anchor,anchor+'    if action=="character_create":return fail("Use the four review characters. New character starting areas are not enabled in this review.")\n')
    lobby.write_text(text,encoding='utf-8')
    bridge=output/'Godot/visual_bridge.gd';text=bridge.read_text(encoding='utf-8-sig')
    assert text.count('port: int = 19737')==1
    bridge.write_text(text.replace('port: int = 19737','port: int = 19747'),encoding='utf-8')
    private=lab/'MinotaurModularCandidate/LobbyAcceptance'
    for source,target in [('models.json','models.json'),('equipment.json','equipment_catalog.json'),('appearance.json','appearance_catalog.json')]:
        shutil.copy2(private/source,output/target)
    cfg=json.loads((run/'bridge_config.json').read_text(encoding='utf-8-sig'));cfg['port']=19747
    (output/'bridge_config.json').write_text(json.dumps(cfg,indent=2))
    for name in ['collision_catalog.json','environment_catalog.json']:
        if (workspace/name).exists():shutil.copy2(workspace/name,output/name)
    for folder in ['Reports/live','Reports/movement','AppData','LocalAppData']:(output/folder).mkdir(parents=True,exist_ok=True)
    # These are credentials of the disposable test account, never the owner's account.
    (output/'private_review_config.json').write_text(json.dumps({'run_id':run.name,'account':account,'password':password,'server_port':10361,'bridge_port':19747},indent=2))
    report={'prepared':True,'installed':False,'normal_database_modified':False,'review_characters':4,
            'scope':'Private four level5 Minotaur review characters with GM access; original Horn Size deformation and new-character starting-zone support remain pending.'}
    (output/'prepared.json').write_text(json.dumps(report,indent=2))
    return report
