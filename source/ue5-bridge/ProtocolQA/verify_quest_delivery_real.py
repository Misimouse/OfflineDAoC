"""Stage an original delivery quest in the marked lab using installed client files."""
import argparse,json,os,runpy,shutil,sqlite3,sys
from datetime import datetime
from pathlib import Path
from prepare_combined_expansion_data import digest

def verify(workspace,install,engine,map_markers=False,lifecycle=False):
    from central_activation_receipts import verify_files
    active=verify_files(workspace)
    assert active['player_trade_installed']
    qa=Path(__file__).resolve().parent
    if lifecycle:
        assert active.get('quest_map_installed')
    lab='QuestMapLifecycleLab' if lifecycle else 'QuestMapLab' if map_markers else 'QuestDeliveryLab'
    out=workspace/lab/'Runners'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True)
    # Export only the world NPC row from a read-only original database connection.
    with sqlite3.connect((install/'runtime/data/opendaoc.sqlite3.db').as_uri()+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row;row=db.execute("SELECT * FROM Mob WHERE Name='Meara' AND Region=200 ORDER BY Mob_ID LIMIT 1").fetchone();assert row
        reference=out/'original_target.json';reference.write_text(json.dumps(dict(source_read_only=True,npc=dict(row)),indent=2))
    text=(qa/'verify_journal_lifecycle_real.py').read_text()
    line=next(l for l in text.splitlines() if l.startswith('D=ROOT/'));text=text.replace(line,"D=ROOT/'QuestDeliveryLab/RealProtocol'/time.strftime('%Y%m%d-%H%M%S');D.mkdir(parents=True)",1)
    line=next(l for l in text.splitlines() if "result['checks']['ordinary_accounts_only']=" in l)
    text=text.replace(line,line+"\n  from quest_delivery_case import prepare\n  prepare(db,leader,world,result,Path(os.environ['DAOC_QUEST_TARGET_REFERENCE']))",1)
    start=text.index(' def journal(peer=a):');end=text.index(" result['passed']=all(result['checks'].values())",start)
    text=text[:start]+" from quest_delivery_case import run\n run(a,b,wait,settle,result,checked,D,world,leader)\n"+text[end:]
    if map_markers:
        text=text.replace("D=ROOT/'QuestDeliveryLab/RealProtocol'","D=ROOT/'QuestMapLab/RealProtocol'",1)
        before=" run(a,b,wait,settle,result,checked,D,world,leader)"
        assert text.count(before)==1
        text=text.replace(before,before[:-1]+",map_checks=True)",1)
        anchor=" candidate_root=ROOT/'GuildWindowLab/ServerCandidate'"
        assert text.count(anchor)==1
        if not active.get('quest_map_installed'):
            text=text.replace(anchor,"  from stage_quest_map import stage_gateway\n  stage_gateway(root/'Godot')\n"+anchor,1)
    if lifecycle:
        text=text.replace("D=ROOT/'QuestDeliveryLab/RealProtocol'","D=ROOT/'QuestMapLifecycleLab/RealProtocol'",1)
        text=text.replace("from quest_delivery_case import", "from quest_map_lifecycle_case import")
    runner=out/'verify_installed.py';runner.write_text(text)
    original_config=install/'runtime/server/classic-quests.json';assert original_config.is_file()
    original_config_hash=digest(original_config)
    os.environ.update(DAOC_INSTALL=str(install),DAOC_BRIDGE_SOURCE_QA=str(qa),DAOC_QUEST_TARGET_REFERENCE=str(reference),DAOC_QUEST_ORIGINAL_CONFIG=str(original_config))
    sys.path.insert(0,str(workspace/'ProtocolQA'))
    import qa_runtime as runtime
    assert runtime.INSTALL==install and runtime.ROOT==workspace
    sdk=engine/'Binaries/ThirdParty/DotNet/10.0/win-x64';runtime.dotnet=sdk/'dotnet.exe'
    runtime.env.update(DOTNET_ROOT=str(sdk),DOTNET_ROOT_X64=str(sdk),PATH=str(sdk)+os.pathsep+runtime.env['PATH'])
    backups=[];recovery=out/'recovery.json'
    def stage(origin,target,name):
        assert target.resolve().is_relative_to(runtime.RUN.resolve())
        saved=out/('before_'+name) if target.exists() else None
        if saved:shutil.copy2(target,saved)
        backups.append((target,saved))
        recovery.write_text(json.dumps(dict(phase='running',files=[dict(target=str(t),backup=str(s) if s else None) for t,s in backups]),indent=2))
        shutil.copy2(origin,target)
    try:
        for name in ['MMOEngine.dll','MMOEngine.pdb']:
            target=runtime.RUN/'LobbyProject/.godot/mono/temp/bin/Debug'/name
            stage(install/'new-client/godot/.godot/mono/temp/bin/Debug'/name,target,name)
        stage(original_config,runtime.SERVER/'classic-quests.json','classic-quests.json')
        value=runpy.run_path(str(runner),run_name='__main__');proof=value['D']/'verified.json';report=json.loads(proof.read_text());assert report['passed']
    finally:
        for target,saved in reversed(backups):
            if saved:shutil.copy2(saved,target);assert digest(target)==digest(saved)
            elif target.exists():target.unlink()
        recovery.write_text(json.dumps(dict(phase='restored',files=[dict(target=str(t),backup=str(s) if s else None) for t,s in backups]),indent=2))
        assert digest(original_config)==original_config_hash
        assert verify_files(workspace)['player_trade_installed']
    installed_files=not map_markers or active.get('quest_map_installed',False)
    result=dict(passed=True,installed_files=installed_files,candidate_gateway=not installed_files,checks=len(report['checks']),proof=str(proof),private_backend_restored=True,normal_runtime_modified=False)
    (workspace/lab/'verified.json').write_text(json.dumps(result,indent=2));return result

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ['workspace','install','engine']:p.add_argument('--'+key,type=Path,required=True)
    mode=p.add_mutually_exclusive_group()
    mode.add_argument('--map-markers',action='store_true')
    mode.add_argument('--map-lifecycle',action='store_true')
    a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.install.resolve(),a.engine.resolve(),a.map_markers,a.map_lifecycle)))
