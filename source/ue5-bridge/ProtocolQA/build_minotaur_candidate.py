"""Convert the original Hibernian modular Minotaur in private output only."""
import argparse
import collections
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

parser=argparse.ArgumentParser(description=__doc__)
for name in ['client','game','workspace','output']:parser.add_argument('--'+name,type=Path,required=True)
args=parser.parse_args()
client,game,workspace,output=(p.resolve() for p in (args.client,args.game,args.workspace,args.output))
assert output.is_relative_to(workspace) and output!=workspace and not output.is_relative_to(game)
os.environ['DAOC_CLIENT']=str(client)
pipeline=Path(__file__).resolve().parents[2]/'new-client/pipeline'
sys.path.insert(0,str(pipeline))
import assets_pipeline
import nif_character
import texture_index
import build_races
assert assets_pipeline.CLIENT.resolve()==client and nif_character.CLIENT.resolve()==client
output.mkdir(parents=True,exist_ok=True)
private=output/'content/characters'
build_races.OUT=private
build_races.TEX=private/'fig3_textures'
texture_index.CACHE=output/'texture_index.json'
# The shared converter reads style definitions relative to its output root.
styles=private.parent/'classes/styles.json';styles.parent.mkdir(parents=True,exist_ok=True)
shutil.copy2(game/'content/classes/styles.json',styles)
sys.argv=[str(Path(__file__)),'--no-upscale']
from minotaur_source_parts import resolve_parts
archive=client/'gamedata.mpk'
before=hashlib.sha256(archive.read_bytes()).hexdigest()
tables=build_races.Tables()
tables.parts, aliases=resolve_parts(tables.rows('fig3parts.csv'))
assert len(aliases)==69, 'Review original fractional part block before conversion'
rows=[row for row in tables.monnifs if row[0].strip()=='868' and row[1].strip()=='Hibernian Player Minotaur' and row[12].strip()=='3' and row[13].strip()=='63']
assert len(rows)==1,'Review original Minotaur table identity before conversion'
monnif=rows[0]
players=[row for row in tables.monsters if len(row)>81 and row[67].strip()==monnif[0].strip()]
assert any(row[0].strip()=='1419' for row in players)
def minotaur_rows(t,fig):
    assert t is tables and fig==63
    pick=lambda column:collections.Counter(row[column].strip() for row in players).most_common(1)[0][0]
    return monnif,players,pick
build_races.figure_rows=minotaur_rows
textures={}
meta=build_races.build_figure(tables,'hib','Minotaur','male',63,textures)
missing=build_races.export_textures(tables,textures)
assert not missing,missing
assert meta['fig3']==63 and meta['monnifs']==868 and meta['gender']=='male' and meta['race']=='Minotaur'
assert meta['faces'] and meta['skin_tones'] and meta['hair_styles']
report={'passed':True,'installed':False,'activated':False,'original_archive_sha256':hashlib.sha256((client/'gamedata.mpk').read_bytes()).hexdigest(),
        'fractional_source_ids':aliases,'source_archive_unchanged':hashlib.sha256(archive.read_bytes()).hexdigest()==before,
        'model_id':1419,'fig3':63,'prefix':meta['prefix'],'monnifs':868,'source_player_rows':[row[0].strip() for row in players],
        'faces':len(meta['faces']),'hair_styles':len(meta['hair_styles']),'skin_tones':len(meta['skin_tones']),
        'sliders':meta['sliders'],'clips':len(meta['clip_seconds']),'missing_textures':missing,'textures':len(textures),
        'geometry':str(private/'races'/meta['prefix']/'figure.gltf'),'metadata':str(private/'races'/meta['prefix']/'figure.json')}
assert report['source_archive_unchanged']
(output/'conversion.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({key:report[key] for key in ['passed','installed','activated','prefix','faces','hair_styles','skin_tones','clips','missing_textures','textures','source_archive_unchanged']}))
