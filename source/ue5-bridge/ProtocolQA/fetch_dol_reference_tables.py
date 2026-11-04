"""Fetch pinned public DOL JSON references; never open a game database."""
import argparse
import hashlib
import json
import re
import urllib.request
from pathlib import Path


def fetch(manifest, workspace, output):
    workspace, output = workspace.resolve(), output.resolve()
    assert output.is_relative_to(workspace) and output != workspace
    plan=json.loads(manifest.read_text(encoding='utf-8-sig'))
    assert plan['repository']=='Dawn-of-Light/db-public' and re.fullmatch('[0-9a-f]{40}',plan['commit'])
    output.mkdir(parents=True,exist_ok=True)
    report={'passed':False,'repository':plan['repository'],'commit':plan['commit'],'tables':[],'database_opened':False}
    for row in plan['tables']:
        name=row['name'];size=int(row['bytes'])
        assert re.fullmatch(r'[A-Za-z][A-Za-z0-9_.]*\.json',name) and Path(name).name==name and 0<size<100_000_000
        assert re.fullmatch('[0-9a-f]{40}',row['git_blob'])
        destination=output/name
        def identity(path):
            blob=hashlib.sha1(('blob '+str(size)+'\0').encode());sha=hashlib.sha256();count=0
            with path.open('rb') as stream:
                for chunk in iter(lambda:stream.read(1024*1024),b''):blob.update(chunk);sha.update(chunk);count+=len(chunk)
            return count,blob.hexdigest(),sha.hexdigest()
        if destination.exists():
            count,blob,sha=identity(destination)
            assert count==size and blob==row['git_blob'],('Existing reference differs; preserve it for review',name)
        else:
            temporary=output/(name+'.part')
            request=urllib.request.Request('https://raw.githubusercontent.com/'+plan['repository']+'/'+plan['commit']+'/src/data/'+name,headers={'User-Agent':'DAoC-reference-audit'})
            with urllib.request.urlopen(request,timeout=45) as response,temporary.open('wb') as stream:
                assert response.status==200
                for chunk in iter(lambda:response.read(1024*1024),b''):stream.write(chunk)
            count,blob,sha=identity(temporary)
            assert count==size and blob==row['git_blob'],('Pinned source identity mismatch',name,count,blob)
            temporary.replace(destination)
        report['tables'].append(dict(row,sha256=sha,file=str(destination)))
        (output/'downloaded_tables.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(name,'verified',count,flush=True)
    report['passed']=True
    (output/'downloaded_tables.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['manifest','workspace','output']:parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();result=fetch(args.manifest,args.workspace,args.output)
    print(json.dumps({'passed':result['passed'],'tables':len(result['tables']),'database_opened':False}))
