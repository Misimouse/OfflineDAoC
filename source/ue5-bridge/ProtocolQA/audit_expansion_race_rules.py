"""Read-only comparison of pinned DOL defaults and this fork's expansion race rules."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import re

COMMIT = '154e150993e078408f87c3e681a62576737d2892'
SOURCES = {
    'GameServer/GlobalConstants.cs': '0b6dd200652e7f08ecf24668c8ccf761580f5c16',
    'GameServer/gameobjects/CharacterClasses/CharacterClassDB.cs': '3edbd1c6872f0e8aa12108e32e40868067cd49f1',
}


def verified_source(path, expected):
    """Accept transport-normalized text only if its original Git blob is recoverable."""
    text = path.read_text(encoding='utf-8-sig').replace('\r\n', '\n')
    base = text.rstrip('\n')
    for newline, bom, tail in itertools.product(['\n', '\r\n'], ['', '\ufeff'], ['', '\n', '\n\n']):
        raw = (bom + (base + tail).replace('\n', newline)).encode('utf-8')
        digest = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        if digest == expected:
            return text
    raise AssertionError(('Pinned upstream Git blob mismatch', str(path)))


def stats(text, race):
    rows = [line for line in text.splitlines() if re.search(r'\{\s*eRace\.' + race + r'\s*,\s*new Dictionary<eStat', line)]
    assert len(rows) == 1, (race, 'base stat row count', len(rows))
    return {'active': not rows[0].lstrip().startswith('//'),
            'values': {k: int(v) for k, v in re.findall(r'\{eStat\.(\w+),\s*(\d+)\}', rows[0])}}


def audit(reference, server):
    sources = {name: verified_source(reference / name, sha) for name, sha in SOURCES.items()}
    constants = (server / 'GlobalConstants.cs').read_text(encoding='utf-8-sig')
    races = {}
    for race in ['Shar', 'HiberniaMinotaur']:
        upstream = stats(sources['GameServer/GlobalConstants.cs'], race)
        local = stats(constants, race)
        assert len(upstream['values']) == len(local['values']) == 8
        races[race] = {'dol': upstream, 'fork': local, 'values_match': upstream['values'] == local['values']}
    classes = {}
    for block in sources['GameServer/gameobjects/CharacterClasses/CharacterClassDB.cs'].split('new DBCharacterClass()')[1:]:
        name = re.search(r'\bID\s*=\s*\(byte\)eCharacterClass\.(\w+)', block)
        eligible = re.search(r'EligibleRaces\s*=\s*\$"([^"\n]*)"', block)
        if not name or not eligible:
            continue
        allowed = re.findall(r'PlayerRace\.(\w+)\.ID', eligible[1])
        if not set(allowed) & {'Shar', 'Graoch'}:
            continue
        paths = list((server / 'playerclasses').rglob('Class' + name[1] + '.cs'))
        assert len(paths) == 1, (name[1], 'fork source count', len(paths))
        text = paths[0].read_text(encoding='utf-8-sig')
        match = re.search(r'EligibleRaces\s*=>\s*new List<PlayerRace>\(\)\s*\{(.*?)\}', text, re.S)
        assert match, (name[1], 'explicit race rule missing')
        active = re.sub(r'//[^\n]*', '', match[1])
        local = re.findall(r'PlayerRace\.(\w+)', active)
        classes[name[1]] = {'dol_defaults': allowed, 'fork_active': local,
            'reference_only': sorted(set(allowed) - set(local)),
            'fork_only': sorted(set(local) - set(allowed)),
            'source': str(paths[0]), 'source_sha256': hashlib.sha256(paths[0].read_bytes()).hexdigest()}
    shar = sorted(k for k, v in classes.items() if 'Shar' in v['dol_defaults'])
    assert shar and 'Warden' not in shar and 'Druid' not in shar
    return {'passed': True, 'read_only': True, 'played_database_accessed': False,
        'race_activation': False, 'reference': {'repository': 'Dawn-of-Light/DOLSharp',
            'commit': COMMIT, 'verified_git_blobs': SOURCES},
        'races': races, 'classes_with_expansion_races': classes,
        'shar_advanced_defaults': [name for name in shar if name not in ['Magician', 'Guardian', 'Stalker']],
        'limitations': ['These are pinned upstream fallback defaults, not an installed DOL CharacterClass table.',
            'Reference-only races and later eligibility changes must not replace this fork wholesale.',
            'Art, transport, disabled switches and real creation/progression remain separate acceptance gates.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['reference', 'server', 'output']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.reference.resolve(), args.server.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'passed': report['passed'], 'shar_advanced_defaults': report['shar_advanced_defaults'],
                      'base_stat_values_match': all(r['values_match'] for r in report['races'].values()), 'race_activation': False}))
