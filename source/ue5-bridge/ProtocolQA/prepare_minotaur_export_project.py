"""Prepare a physical private Godot project for the recovered modular Minotaur.

No assets are linked to the normal project. The normal gameplay factory stays
untouched; its metadata-cache read and helmet transform constant are resolved
locally so this export does not require loading the gameplay session.
"""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path


def prepare_palette_adapter(source, project, hashes):
    """Reuse the original menu's sampling without its gameplay dependencies."""
    path = source / 'game/pregame.gd'
    original = path.read_text(encoding='utf-8-sig')
    start = 'func _eye_colours()'
    end = '# ---------------------------------------------------------------- frame + widgets'
    assert original.count(start) == original.count(end) == 1
    methods = original[original.index(start):original.index(end)]
    assert methods.count('func ') == 4 and 'func _swatch(' in methods
    methods = methods.replace('Fig3Figure.skin_tint', 'load("res://game/fig3_figure.gd").skin_tint')
    header = 'extends Node\nvar _figure\nvar draft:Dictionary={}\nvar _swatch_cache:Dictionary={}\n'
    (project / 'tools/palette_original.gd').write_text(header + methods, encoding='utf-8')
    hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(candidate, workspace):
    candidate, workspace = candidate.resolve(), workspace.resolve()
    assert candidate != workspace and candidate.is_relative_to(workspace)
    source = Path(__file__).resolve().parents[2] / 'new-client/godot'
    bridge = Path(__file__).resolve().parents[1] / 'Godot'
    receipt = json.loads((candidate/'conversion.json').read_text())
    assert receipt['passed'] and receipt['source_archive_unchanged']
    assert receipt['fig3'] == 63 and receipt['model_id'] == 1419
    project = candidate/'Godot'
    assert not project.is_symlink()
    for folder in ['game', 'tools']:
        (project/folder).mkdir(parents=True, exist_ok=True)
    (project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Private Minotaur Conversion QA"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n')
    hashes = {}
    for name in ['fig3_figure.gd', 'nif_materials.gd', 'emblems.gd']:
        path = source/'game'/name
        hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        shutil.copy2(path, project/'game'/name)
    factory = project/'game/fig3_figure.gd'
    text = factory.read_text(encoding='utf-8-sig').replace('class_name Fig3Figure\n', '', 1)
    text, count = re.subn(r'^\tmeta = NpcManager\._metas\[prefix\].*$', '\tmeta = JSON.parse_string(FileAccess.get_file_as_string(dir + "/figure.json"))', text, flags=re.M)
    assert count == 1, 'Review factory metadata loading before private export'
    weapons = source/'game/weapon_models.gd'
    transform = re.search(r'^const TO_NIF\s*:?=\s*(.+)$', weapons.read_text(), re.M)
    assert transform and text.count('WeaponModels.TO_NIF') == 1
    text = text.replace('WeaponModels.TO_NIF', '('+transform.group(1)+')')
    factory.write_text(text, encoding='utf-8')
    hashes[str(weapons)] = hashlib.sha256(weapons.read_bytes()).hexdigest()
    shutil.copytree(candidate/'content', project/'content', dirs_exist_ok=True)
    for name in ['export_models.gd', 'export_all_animations.gd', 'export_appearance_parts.gd',
                 'export_cloaked_figures.gd', 'export_appearance_swatches.gd']:
        path = bridge/name
        hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        shutil.copy2(path, project/'tools'/name)
    prepare_palette_adapter(source, project, hashes)
    meta = json.loads((candidate/'content/characters/races/mino/figure.json').read_text())
    tasks = [{'id': '1419', 'name': 'Hibernian modular Minotaur candidate',
              'info': {'race': 'mino', **{key: meta[key] for key in ['clip_seconds', 'cast_clips'] if key in meta}}, 'equipment': []}]
    (candidate/'SourceFigures').mkdir(exist_ok=True)
    (candidate/'SourceFigures/tasks.json').write_text(json.dumps(tasks, indent=2))
    report = {'prepared': True, 'installed': False, 'gameplay_session_loaded': False,
              'project': str(project), 'source_scripts': hashes,
              'private_factory_sha256': hashlib.sha256(factory.read_bytes()).hexdigest(),
              'conversion_sha256': hashlib.sha256((candidate/'conversion.json').read_bytes()).hexdigest()}
    (candidate/'export_project.json').write_text(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--workspace', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.candidate, args.workspace)))
