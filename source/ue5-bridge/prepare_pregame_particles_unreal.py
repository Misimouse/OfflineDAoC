"""Import the original ambient sprite into separate assets; never save a map."""
import json,os,sys
from pathlib import Path
import unreal
sys.path.insert(0,str(Path(__file__).parent))
from pregame_material_unreal import build
workspace=Path(os.environ['DAOC_BRIDGE_WORKSPACE'])
source=workspace/'SourcePregameParticles/lobby_particles.json'
data=json.loads(source.read_text())
assert data['version']==1 and len(data['emitters'])==1
emitter=data['emitters'][0]
assert emitter['blend']=='add' and emitter['texture']=='grnglow'
definition={'spec':{'alpha':'add','double_sided':True,'vertex_colors':True},
            'layers':{'base':{'file':emitter['image'],'uv':0}}}
material=build('/DAoCVisualBridge/PregameParticles_v01','M_OriginalAmbient',definition,source.parent,source_uniforms=True)
assert material
print('PREGAME_PARTICLES_IMPORTED map_saved=False')
