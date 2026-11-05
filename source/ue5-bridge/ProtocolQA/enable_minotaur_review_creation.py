"""Remove only the private review creation guard after original-start protocol QA."""
import argparse
import hashlib
import json
import socket
from pathlib import Path


def enable(workspace):
    workspace = workspace.resolve()
    root = workspace/'ExpansionRaceLab/MinotaurOwnerReview'
    assert root.is_dir() and root.resolve().is_relative_to(workspace)
    for port in [10361,19747]:
        try:
            with socket.create_connection(('127.0.0.1',port), timeout=.2):
                raise RuntimeError('Close the private review before updating its creation guard')
        except (ConnectionRefusedError, socket.timeout):
            pass
    proof = workspace/'Reports/minotaur_original_start/real_protocol.json'
    report = json.loads(proof.read_text())
    required = ['passed', 'real_protocol', 'disposable_only', 'database_restored',
                'appearance_profile_restored', 'bridge_config_restored',
                'candidate_files_restored', 'normal_shutdown',
                'original_start_without_relocation', 'original_spawn_and_bind_preserved_before_entry']
    assert all(report.get(k) for k in required)
    assert 'qa_connacht_relocation' not in report
    cases = report['cases']
    assert len(cases) == 4 and {c['selected_class'] for c in cases} == {43,44,45,46}
    assert all(c['original_spawn_and_bind_retained'] and c['original_start_zone'] == 207
               and c['existing_character_reentry'] and c['spell_list_complete'] for c in cases)
    # The shared/native source is never touched. Existing saved characters and
    # their database remain untouched; only remove the exporter's private guard.
    lobby = root/'Godot/character_lobby.gd'
    assert lobby.resolve().is_relative_to(root)
    block = '    if action=="character_create":return fail("Use the four review characters. New character starting areas are not enabled in this review.")\n'
    text = lobby.read_text(encoding='utf-8-sig')
    receipt = root/'creation_enabled.json'
    if block not in text:
        assert receipt.exists(), 'Unexpected private lobby contents'
        existing = json.loads(receipt.read_text())
        assert existing['lobby_after_sha256'] == hashlib.sha256(lobby.read_bytes()).hexdigest()
        return existing
    assert text.count(block) == 1
    backup = root/'Godot/character_lobby.before_creation_enable.gd.bak'
    assert not backup.exists(), 'Preserve the existing rollback copy'
    before = lobby.read_bytes()
    backup.write_bytes(before)
    lobby.write_text(text.replace(block, ''), encoding='utf-8')
    result = {'passed': True, 'review_only': True, 'normal_installation_modified': False,
              'review_database_modified': False, 'original_start_zone': 207,
              'careers_verified': 4, 'protocol_proof_sha256': hashlib.sha256(proof.read_bytes()).hexdigest(),
              'lobby_before_sha256': hashlib.sha256(before).hexdigest(),
              'lobby_after_sha256': hashlib.sha256(lobby.read_bytes()).hexdigest(),
              'rollback_copy': str(backup)}
    receipt.write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True, type=Path)
    print(json.dumps(enable(parser.parse_args().workspace)))
