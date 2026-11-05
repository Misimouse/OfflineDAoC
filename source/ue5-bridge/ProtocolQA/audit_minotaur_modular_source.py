"""Audit original modular Minotaur tables before attempting conversion."""
import argparse
import csv
import hashlib
import io
import json
import sys
from pathlib import Path
from minotaur_source_parts import resolve_parts


def audit(client, workspace, output):
    client, workspace, output = (p.resolve() for p in (client, workspace, output))
    assert output.is_relative_to(workspace) and not output.is_relative_to(client)
    pipeline=Path(__file__).resolve().parents[2]/'new-client/pipeline'
    sys.path.insert(0,str(pipeline))
    from daoc_mpk import read_mpk
    archive=client/'gamedata.mpk'
    before=hashlib.sha256(archive.read_bytes()).hexdigest()
    tables=read_mpk(str(archive))
    def rows(name):return list(csv.reader(io.StringIO(tables[name].decode('latin1'))))
    monnifs=[row for row in rows('monnifs.csv') if row and row[0].strip()=='868']
    assert len(monnifs)==1
    source=monnifs[0]
    assert source[1].strip()=='Hibernian Player Minotaur' and source[12].strip()=='3' and source[13].strip()=='63'
    raw_parts=rows('fig3parts.csv')
    parts={row[0].strip():row for row in raw_parts if row and row[0].strip().isdigit()}
    resolved, aliases=resolve_parts(raw_parts)
    maps=[row for row in rows('fig3map.csv') if row and row[0].strip()=='63']
    assert maps and any(row[1].strip()=='0' for row in maps)
    references=sorted({value.strip() for row in maps for value in row[3:] if value.strip()},key=int)
    missing=[key for key in references if key not in parts]
    unresolved=[key for key in references if key not in resolved]
    archives={}
    absent=[]
    for key in references:
        if key not in resolved:
            continue
        row=resolved[key]
        part_archive=client/'figures/fig3'/('fig'+row[5].strip().zfill(3)+'.mpk')
        if part_archive not in archives:
            archives[part_archive]={name.lower() for name in read_mpk(str(part_archive))} if part_archive.exists() else set()
        if (row[2]+'.nif').lower() not in archives[part_archive]:
            absent.append({'part':key,'mesh':row[2],'archive':str(part_archive)})
    options={}
    for table in ['fig3facemap.csv','fig3eyecolormap.csv','fig3skincolormap.csv','fig3descriptions.csv','fig3haircolormap.csv']:
        options[table]=[row for row in rows(table) if row and row[0].strip()=='63']
    result={'audited':True,'ready_for_modular_conversion':not unresolved and not absent,'activated':False,'original_archive_sha256':before,
            'fig3':63,'monnifs':868,'source_name':source[1],'skeleton_archive':source[15],
            'part_references':references,'missing_part_definitions':missing,'option_table_rows':options,
            'fractional_source_ids':{key:aliases[key] for key in references if key in aliases},
            'unresolved_part_definitions':unresolved,'absent_meshes':absent,
            'no_substitute_parts_created':True,'note':'Stock decimal IDs are resolved only in memory for the private Minotaur candidate. Original archives remain unchanged. Conversion readiness is not runtime acceptance.'}
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==before
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['client','workspace','output']:parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();result=audit(args.client,args.workspace,args.output)
    print(json.dumps({key:result[key] for key in ['audited','ready_for_modular_conversion','fig3','missing_part_definitions','activated']}))
