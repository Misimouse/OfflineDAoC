"""Trim a verified private material library into the lazy runtime lookup catalogue."""
import argparse,json
from pathlib import Path
from prepare_combined_expansion_data import digest

def prepare(materials,output):
    data=json.loads(materials.read_text(encoding='utf-8-sig'))
    assert data['passed'] and data['originals_unchanged'] and not data['installed'] and not data.get('diagnostic_only')
    assert 0<len(data['materials'])<=20000 and data['library'].startswith('/DAoCVisualBridge/Stealth_v01/')
    for source,target in data['materials'].items():
        assert source.startswith('/') and target.startswith(data['library']+'/') and '..' not in target
    result={key:data[key] for key in ['passed','installed','originals_unchanged','library','materials']}
    result.update(version=1,source_manifest_sha256=digest(materials))
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,separators=(',',':')),encoding='utf-8')
    return dict(passed=True,materials=len(result['materials']),bytes=output.stat().st_size,normal_runtime_modified=False)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--materials',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(json.dumps(prepare(a.materials.resolve(),a.output.resolve())))
