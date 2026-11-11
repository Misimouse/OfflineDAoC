"""Exercise the candidate reward decoder/requests on original disposable DOL."""
import argparse,json,os,runpy,shutil,sys
from datetime import datetime
from pathlib import Path
from prepare_combined_expansion_data import digest

def verify(workspace,install,engine,backend_proof,gateway=False,installed=False,backpack=False,markers=False):
    from central_activation_receipts import verify_files
    active=verify_files(workspace)
    assert active['player_trade_installed'] and active['quest_rewards_installed']==installed
    assert not installed or gateway
    assert not (backpack or markers) or installed
    assert not (backpack and markers)
    backend=json.loads(backend_proof.read_text());assert backend['passed'] and backend['candidate_dispatch_enabled'] and backend['checks']>=265
    if installed:
        plan=json.loads((workspace/'QuestRewardsLab/delivery-plan.json').read_text())
        assert plan['proofs']['codec']==str(backend_proof)
        candidate=install/'new-client/godot/.godot/mono/temp/bin/Debug'
    else:
        assert all(digest(Path(p))==h for p,h in backend['source_inputs'].items())
        candidate=Path(backend['candidate_backend']).parent
    assert digest(candidate/'MMOEngine.dll')==backend['candidate_backend_sha256']
    qa=Path(__file__).resolve().parent;out=workspace/'QuestRewardsLab/Runners'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True)
    text=(qa/'verify_journal_lifecycle_real.py').read_text();line=next(l for l in text.splitlines() if l.startswith('D=ROOT/'))
    text=text.replace(line,"D=ROOT/'QuestRewardsLab/RealProtocol'/time.strftime('%Y%m%d-%H%M%S');D.mkdir(parents=True)",1)
    line=next(l for l in text.splitlines() if "result['checks']['ordinary_accounts_only']=" in l)
    text=text.replace(line,line+'\n  from quest_reward_wire_case import prepare\n  prepare(db,leader,world,result)',1)
    start=text.index(' def journal(peer=a):');end=text.index(" result['passed']=all(result['checks'].values())",start)
    text=text[:start]+' from quest_reward_wire_case import run\n run(a,b,wait,settle,result,checked,D,world,leader)\n'+text[end:]
    hook='''
  q=root/'Godot/live_gateway.gd';staged=q.read_text(encoding='utf-8-sig')
  staged=staged.replace('var inventory:RefCounted','var qa_reward_dialog:Dictionary={}\\nvar qa_reward_request:Dictionary={}\\nvar qa_reward_serial:=0\\nvar inventory:RefCounted',1)
  staged=staged.replace('func world_event(kind:String,data:Dictionary)->void:','func world_event(kind:String,data:Dictionary)->void:\\n    if kind=="quest_dialog":\\n        var revision:int=int(qa_reward_dialog.get("revision",0))+1\\n        qa_reward_dialog=data.duplicate(true);qa_reward_dialog["revision"]=revision',1)
  raw_hook='        server.client.connect("Packet",Callable(player_models,"consume_raw"))'
  assert staged.count(raw_hook)==1
  staged=staged.replace(raw_hook,raw_hook+'\\n        server.client.connect("Packet",func(code,data):\\n            if int(code)==129 and data.size()>1 and int(data[1]) in [33,34]:print("QA_QUEST_RAW "+data.hex_encode()))',1)
  staged=staged.replace('        transport.snapshot_metadata["classic_ui"]=classic_ui.snapshot()','        transport.snapshot_metadata["qa_quest_dialog"]=qa_reward_dialog.duplicate(true)\\n        transport.snapshot_metadata["qa_quest_request"]=qa_reward_request.duplicate(true)\\n        transport.snapshot_metadata["classic_ui"]=classic_ui.snapshot()',1)
  command_hook='func command(value:Dictionary)->void:\\n    if String(value.get("action",""))=="chat" and String(value.get("text","" )).begins_with("/qa-quest-reward "):\\n        var request:Dictionary=JSON.parse_string(String(value.text).trim_prefix("/qa-quest-reward "))\\n        var encoded:bool=false\\n        if request.mode=="offer":encoded=server.client.QuestOffer(int(request.quest_id),int(request.giver_id),bool(request.accept))\\n        else:encoded=server.client.QuestReward(int(request.quest_id),int(request.giver_id),int(request.required_choices),int(request.option_count),PackedInt32Array(request.choices))\\n        qa_reward_serial+=1;qa_reward_request={"serial":qa_reward_serial,"encoded":encoded};return'
  staged=staged.replace('func command(value:Dictionary)->void:',command_hook,1)
  assert 'var qa_reward_dialog:' in staged and 'qa_quest_dialog' in staged and 'server.client.QuestOffer' in staged
  q.write_text(staged,encoding='utf-8')
  q=root/'Godot/visual_bridge.gd';staged=q.read_text(encoding='utf-8-sig');assert '["character",' in staged;q.write_text(staged.replace('["character",','["qa_quest_dialog","qa_quest_request","character",',1))
'''
    if gateway:
        lab='IndicatorProtocol' if markers else 'BackpackProtocol' if backpack else 'InstalledProtocol' if installed else 'GatewayProtocol'
        case='quest_indicator_real_case' if markers else 'quest_reward_backpack_case' if backpack else 'quest_reward_gateway_case'
        text=text.replace('QuestRewardsLab/RealProtocol','QuestRewardsLab/'+lab).replace('from quest_reward_wire_case import','from '+case+' import')
        hook='''
  from stage_quest_reward_gateway import stage_gateway
  stage_gateway(root/'Godot', Path(os.environ['DAOC_BRIDGE_SOURCE_QA']).parent/'Godot/quest_reward_state.gd')
'''
        if installed:hook=''
        if markers:hook='''
  from stage_quest_indicators import stage_markers
  stage_markers(root/'Godot',telemetry=True)
'''
    needle=" candidate_root=ROOT/'GuildWindowLab/ServerCandidate'";at=text.index(needle);text=text[:at]+hook+text[at:]
    runner=out/'verify_candidate.py';runner.write_text(text)
    os.environ.update(DAOC_INSTALL=str(install),DAOC_BRIDGE_SOURCE_QA=str(qa),DAOC_QUEST_REWARD_BACKEND_PROOF=str(backend_proof))
    sys.path.insert(0,str(workspace/'ProtocolQA'))
    import qa_runtime as runtime
    assert runtime.INSTALL==install and runtime.ROOT==workspace
    sdk=engine/'Binaries/ThirdParty/DotNet/10.0/win-x64';runtime.dotnet=sdk/'dotnet.exe';runtime.env.update(DOTNET_ROOT=str(sdk),DOTNET_ROOT_X64=str(sdk),PATH=str(sdk)+os.pathsep+runtime.env['PATH'])
    backups=[];recovery=out/'recovery.json'
    try:
        for name in ['MMOEngine.dll','MMOEngine.pdb']:
            target=runtime.RUN/'LobbyProject/.godot/mono/temp/bin/Debug'/name;assert target.resolve().is_relative_to(runtime.RUN.resolve())
            saved=out/('before_'+name);shutil.copy2(target,saved);backups.append((target,saved))
            recovery.write_text(json.dumps(dict(phase='running',files=[dict(target=str(t),backup=str(s)) for t,s in backups]),indent=2));shutil.copy2(candidate/name,target)
        value=runpy.run_path(str(runner),run_name='__main__');proof=value['D']/'verified.json';report=json.loads(proof.read_text());assert report['passed']
    finally:
        for target,saved in reversed(backups):shutil.copy2(saved,target);assert digest(target)==digest(saved)
        recovery.write_text(json.dumps(dict(phase='restored',files=[dict(target=str(t),backup=str(s)) for t,s in backups]),indent=2))
        assert verify_files(workspace)['player_trade_installed']
    result=dict(passed=True,checks=len(report['checks']),proof=str(proof),candidate_backend_proof=str(backend_proof),private_backend_restored=True,normal_runtime_modified=False,installed=installed)
    name='indicators_verified.json' if markers else 'backpack_verified.json' if backpack else 'installed_protocol_verified.json' if installed else 'gateway_verified.json' if gateway else 'wire_verified.json'
    (workspace/'QuestRewardsLab'/name).write_text(json.dumps(result,indent=2));return result

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ['workspace','install','engine','backend_proof']:p.add_argument('--'+key.replace('_','-'),type=Path,required=True)
    p.add_argument('--gateway',action='store_true')
    p.add_argument('--installed',action='store_true')
    p.add_argument('--backpack',action='store_true')
    p.add_argument('--markers',action='store_true')
    a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.install.resolve(),a.engine.resolve(),a.backend_proof.resolve(),a.gateway,a.installed,a.backpack,a.markers)))
