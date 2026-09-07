"""Serialized local file transactions with durable rollback journals (macOS/Linux)."""
from __future__ import annotations

import base64
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import tempfile
import threading

_lock = threading.RLock()
_state = threading.local()


def atomic_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        sync_dir(path.parent)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def sync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def track(path: Path) -> None:
    txn = getattr(_state, 'txn', None)
    if txn is None:
        return
    root, journal, originals = txn
    relative = str(path.resolve().relative_to(root))
    if relative not in originals:
        originals[relative] = base64.b64encode(path.read_bytes()).decode('ascii') if path.exists() else None
        atomic_bytes(journal, json.dumps(originals).encode('utf-8'))


def _rollback(root: Path, journal: Path) -> None:
    originals = json.loads(journal.read_text(encoding='utf-8'))
    for relative, original in originals.items():
        path = (root / relative).resolve()
        path.relative_to(root)
        if original is None:
            path.unlink(missing_ok=True)
            if path.parent.exists():
                sync_dir(path.parent)
        else:
            atomic_bytes(path, base64.b64decode(original))
    journal.unlink()
    sync_dir(root)


@contextmanager
def transaction(root: Path):
    root = root.resolve()
    with _lock:
        if getattr(_state, 'txn', None) is not None:
            if _state.txn[0] != root:
                raise RuntimeError('Cannot switch GTD directories during a transaction')
            yield
            return
        root.mkdir(parents=True, exist_ok=True)
        with (root / '.gtd.lock').open('a+b') as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            journal = root / '.gtd-transaction.json'
            try:
                if journal.exists():
                    _rollback(root, journal)
                _state.txn = (root, journal, {})
                try:
                    yield
                except BaseException:
                    if journal.exists():
                        _rollback(root, journal)
                    raise
                else:
                    if journal.exists():
                        journal.unlink()
                        sync_dir(root)
            finally:
                _state.txn = None
                fcntl.flock(lock_file, fcntl.LOCK_UN)
