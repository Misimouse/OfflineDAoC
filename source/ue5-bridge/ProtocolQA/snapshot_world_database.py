"""Read a consistent local world snapshot without opening or changing the source DB."""
from contextlib import contextmanager
import hashlib
from pathlib import Path
import sqlite3
import tempfile


@contextmanager
def snapshot(source, temporary_root):
    source, temporary_root = source.resolve(), temporary_root.resolve()
    assert source.name == 'opendaoc.sqlite3.db' and source.is_file()
    temporary_root.mkdir(parents=True, exist_ok=True)
    assert not source.is_relative_to(temporary_root)
    with tempfile.TemporaryDirectory(prefix='world_audit_', dir=temporary_root) as temporary:
        temporary = Path(temporary).resolve()
        assert temporary.is_relative_to(temporary_root)
        for attempt in range(3):
            paths = [source]
            wal = source.with_name(source.name+'-wal')
            if wal.exists():
                paths.append(wal)
            raw = {path: path.read_bytes() for path in paths}
            hashes = {path: hashlib.sha256(value).hexdigest() for path, value in raw.items()}
            if all(path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == value for path, value in hashes.items()) and wal.exists() == (wal in raw):
                break
        else:
            raise RuntimeError('World files changed during each bounded snapshot attempt')
        target = temporary/'snapshot.sqlite3.db'
        for path, value in raw.items():
            suffix = '-wal' if path == wal else ''
            target.with_name(target.name+suffix).write_bytes(value)
        del raw
        db = sqlite3.connect(target.as_uri()+'?mode=ro', uri=True)
        try:
            db.row_factory = sqlite3.Row
            db.execute('PRAGMA query_only=ON')
            assert db.execute('PRAGMA quick_check').fetchone()[0] == 'ok'
            yield db, {'source_read_only': True, 'wal_included': wal in hashes,
                       'source_files_sha256': {path.name: value for path, value in hashes.items()},
                       'private_snapshot_removed_after_audit': True}
        finally:
            db.close()
