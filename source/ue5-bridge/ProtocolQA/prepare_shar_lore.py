"""Append original Shar creation descriptions to a private copy of the installed lore."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

SUMMARY_SHA256='a1312d85b0a9824b6ae63a5a0657da330d1bea30d2230c76245b41f357626af2'


def prepare(client,pipeline,installed_lore,workspace,output):
    client,pipeline,installed_lore,workspace,output=(p.resolve() for p in (client,pipeline,installed_lore,workspace,output))
    assert output.is_relative_to(workspace) and output!=installed_lore
    archive=client/'charman/summary.mpk'
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==SUMMARY_SHA256,'Original character summary archive changed'
    spec=importlib.util.spec_from_file_location('original_mpak_reader',pipeline/'daoc_mpk.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    raw=module.read_mpk(str(archive))['summary.txt'].decode('latin1')
    sections={};current=None
    for line in raw.splitlines():
        line=line.strip()
        if line.startswith('[') and line.endswith(']'):
            current=line[1:-1];sections[current]=[]
        elif current and line:sections[current].append(line)
    additions={}
    for key,lines in sections.items():
        if not key.startswith('SHAR-') or not lines:continue
        title,body=(lines[0],lines[1:]) if len(lines[0])<60 else ('',lines)
        disabled=title.strip(' .').lower() in ['n/a','not available','not supported']
        additions[key]={'title':'' if disabled else title,'text':'\n\n'.join(body),'available':not disabled}
    assert all(additions[key]['available'] and additions[key]['text'] for key in ['SHAR-ARMS','SHAR-MAGI','SHAR-STEA'])
    result=json.loads(installed_lore.read_text(encoding='utf-8-sig'))
    for key,row in additions.items():
        assert key not in result['classes'] or result['classes'][key]==row
        result['classes'][key]=row
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    report={'passed':True,'installed':False,'original_summary_sha256':SUMMARY_SHA256,'added_classes':sorted(additions),'original_lore_sha256':hashlib.sha256(installed_lore.read_bytes()).hexdigest(),'candidate_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'scope':'Original English creation descriptions only. Server choices remain authoritative; no other race or realm text changed.'}
    output.with_suffix('.source.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['client','pipeline','installed-lore','workspace','output']:parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args();print(json.dumps(prepare(args.client,args.pipeline,args.installed_lore,args.workspace,args.output)))
