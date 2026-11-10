"""Reject altered trainer delivery plans without touching the normal runtime."""
import argparse,copy,json
from pathlib import Path
from prepare_combined_expansion_data import digest
from trainer_affordability_receipts import read,validate

def verify(workspace):
    root=workspace/'TrainerAffordabilityLab';plan=root/'install_plan.json';data=read(plan);validate(workspace,data,False);checks=1
    mutations=[lambda d:d.update(installed=False),lambda d:d.update(phase='partial')]
    for key in ['database_modified','native_modified','server_rules_modified','map_modified']:
        mutations.append(lambda d,key=key:d.update({key:True}))
    mutations.extend([
        lambda d:d['files'].append(copy.deepcopy(d['files'][0])),
        lambda d:d['files'][0].update(target=str(workspace/'Godot/live_gateway.gd')),
        lambda d:d['files'][0].update(source=str(workspace/'Godot/trainer_state.gd')),
        lambda d:d['files'][0].update(before_sha256='0'*64),
        lambda d:d['files'][0].update(after_sha256='0'*64),
        lambda d:d.update(predecessor_sha256='0'*64),
        lambda d:d.update(native_sha256='0'*64),
        lambda d:d.update(evidence={}),
        lambda d:d['evidence'].update({next(iter(d['evidence'])):'0'*64}),
        lambda d:d['proofs'].update(state=str(workspace/'outside.json')),
        lambda d:d['evidence'].update({str(workspace/'extra.json'):'0'*64})])
    for mutate in mutations:
        changed=copy.deepcopy(data);mutate(changed)
        try:validate(workspace,changed,False)
        except (AssertionError,KeyError,ValueError,OSError):checks+=1
        else:raise AssertionError('Altered delivery was accepted')
    value=dict(passed=True,simulated_only=True,checks=checks,plan_sha256=digest(plan),normal_installation_modified=False,
        guard_sources={name:digest(Path(__file__).with_name(name)) for name in ['trainer_affordability_receipts.py','install_trainer_affordability.py','central_activation_receipts.py']})
    (root/'install_simulation.json').write_text(json.dumps(value,indent=2));return value
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);a=p.parse_args();print(json.dumps(verify(a.workspace.resolve())))
