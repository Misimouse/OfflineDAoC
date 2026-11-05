"""Prepare source-authorized Hibernian Minotaur rules only in a private build.

The four existing advanced careers use the original DOL eligibility defaults.
Mauler is a separate package: this tool does not enable it or change its slot.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from audit_expansion_race_rules import audit

CLASSES = {'Blademaster', 'Hero', 'Champion', 'Warden'}


def variants(reference, server_source, output):
    reference, server_source, output = (p.resolve() for p in (reference, server_source, output))
    assert not output.is_relative_to(server_source)
    rules = audit(reference, server_source/'GameServer')
    assert rules['races']['HiberniaMinotaur']['values_match']
    expected = rules['races']['HiberniaMinotaur']['dol']['values']
    assert expected == {'STR':80,'CON':70,'DEX':50,'QUI':40,'INT':60,'PIE':60,'EMP':60,'CHR':60}
    changes = {}
    name = 'GameServer/GlobalConstants.cs'
    raw = (server_source/name).read_bytes()
    lines = raw.splitlines(keepends=True)
    matches = [i for i, line in enumerate(lines) if b'{ eRace.HiberniaMinotaur, new Dictionary<eStat' in line]
    assert len(matches) == 1 and lines[matches[0]].lstrip().startswith(b'//')
    lines[matches[0]] = lines[matches[0]].replace(b'// ', b'', 1)
    assert b'{eRace.HiberniaMinotaur, eGender.Male}' in raw
    changes[name] = b''.join(lines)
    for cls in sorted(CLASSES):
        authority = rules['classes_with_expansion_races'][cls]
        assert 'Graoch' in authority['dol_defaults'] and 'Graoch' not in authority['fork_active']
        source = Path(authority['source'])
        raw = source.read_bytes()
        match = re.search(rb'EligibleRaces\s*=>\s*new List<PlayerRace>\(\)\s*\{(.*?)\}', raw, re.S)
        assert match
        newline = b'\r\n' if b'\r\n' in raw else b'\n'
        body = match[1].rstrip()+newline+b'            PlayerRace.Graoch,'+newline+b'        '
        changes[source.relative_to(server_source).as_posix()] = raw[:match.start(1)]+body+raw[match.end(1):]
    output.mkdir(parents=True, exist_ok=True)
    report = {'passed': True, 'installed': False, 'normal_sources_changed': False,
              'reference': rules['reference'], 'classes': sorted(CLASSES),
              'race_id': 21, 'gender': 'male', 'mauler_enabled': False, 'files': {}}
    for name, data in changes.items():
        original = server_source/name
        before = hashlib.sha256(original.read_bytes()).hexdigest()
        target = output/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        report['files'][name] = {'path': str(target), 'original_sha256': before,
                               'candidate_sha256': hashlib.sha256(data).hexdigest()}
        assert hashlib.sha256(original.read_bytes()).hexdigest() == before
    (output/'rules_manifest.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ['reference', 'server-source', 'output']:
        parser.add_argument('--'+key, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(variants(args.reference, args.server_source, args.output)))
