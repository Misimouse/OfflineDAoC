"""Reject altered trade delivery manifests without changing any filesystem target."""
import argparse,copy,json
from pathlib import Path
from player_trade_delivery_plan import read,validate
from prepare_combined_expansion_data import digest

def verify(workspace,install):
    path=workspace/'PlayerTradeGatewayLab/delivery-plan.json';plan=read(path);validate(workspace,install,plan)
    mutations={}
    for key in ['database_modified','server_rules_modified','map_modified','normal_installation_modified']:
        mutations[key]=lambda p,key=key:p.update({key:True})
    mutations['phase']=lambda p:p.update(phase='complete')
    mutations['duplicate target']=lambda p:p['files'].append(copy.deepcopy(p['files'][0]))
    mutations['missing target']=lambda p:p['files'].pop()
    mutations['unexpected target']=lambda p:p['files'][0].update(target=str(workspace/'unrelated.dll'))
    mutations['unexpected source']=lambda p:p['files'][0].update(source=str(workspace/'unrelated.dll'))
    mutations['changed installed input']=lambda p:p['files'][0].update(before_sha256='0'*64)
    mutations['changed candidate']=lambda p:p['files'][0].update(after_sha256='0'*64)
    mutations['predecessor']=lambda p:p.update(predecessor_sha256='0'*64)
    mutations['native before']=lambda p:p.update(native_before_sha256='0'*64)
    mutations['native after']=lambda p:p.update(native_after_sha256='0'*64)
    mutations['altered evidence']=lambda p:p['evidence'].update({p['proofs']['real']:'0'*64})
    mutations['missing proof']=lambda p:p['proofs'].pop('controller')
    rejected=[]
    for name,change in mutations.items():
        candidate=copy.deepcopy(plan);change(candidate)
        try:validate(workspace,install,candidate)
        except (AssertionError,KeyError,ValueError):rejected.append(name)
        else:raise AssertionError('Altered manifest accepted: '+name)
    value=dict(passed=True,checks=1+len(rejected),altered_plans_rejected=rejected,plan_sha256=digest(path),normal_installation_modified=False,server_started=False)
    out=workspace/'PlayerTradeGatewayLab/delivery_guards_verified.json';out.write_text(json.dumps(value,indent=2));return value
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ['workspace','install']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.install.resolve())))
