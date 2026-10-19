"""Atomic JSON session checkpoints with integrity checking; no pickle."""

import hashlib
import json
import os
from pathlib import Path
import platform
import tempfile

import numpy as np

from . import __version__
from .integrated import IntegratedSession

MAX_CHECKPOINT_BYTES = 10 * 1024 * 1024


def _canonical(payload):
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def checkpoint_bytes(session):
    """Create the same portable envelope for a disk file or browser download."""
    if not isinstance(session, IntegratedSession):
        raise ValueError('checkpoint requires an IntegratedSession')
    payload = {'format': 'synapse-session-file-v1', 'engine_version': __version__,
               'python_version': platform.python_version(), 'numpy_version': np.__version__,
               'session': session.state_dict()}
    envelope = {'payload': payload, 'sha256': hashlib.sha256(_canonical(payload)).hexdigest()}
    data = json.dumps(envelope, indent=2, allow_nan=False).encode('utf-8')
    if len(data) > MAX_CHECKPOINT_BYTES:
        raise ValueError('checkpoint exceeds the 10 MiB budget')
    return data


def save_checkpoint(path, session):
    path = Path(path)
    data = checkpoint_bytes(session)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False, suffix='.tmp') as stream:
            temporary = Path(stream.name)
            if stream.write(data) != len(data):
                raise OSError('incomplete checkpoint write')
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
        if path.read_bytes() != data:
            raise OSError('checkpoint write verification failed')
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return path


def load_checkpoint(path):
    path = Path(path)
    if path.stat().st_size > MAX_CHECKPOINT_BYTES:
        raise ValueError('checkpoint exceeds the 10 MiB budget')
    return session_from_checkpoint_bytes(path.read_bytes())


def session_from_checkpoint_bytes(data):
    """Validate an uploaded JSON envelope without executing code or writing files."""
    if not isinstance(data, bytes) or len(data) > MAX_CHECKPOINT_BYTES:
        raise ValueError('checkpoint must be bytes within the 10 MiB budget')
    try:
        envelope = json.loads(data.decode('utf-8'))
        if not isinstance(envelope, dict) or not isinstance(envelope.get('payload'), dict):
            raise ValueError('checkpoint envelope and payload must be objects')
        payload = envelope['payload']
        if payload.get('format') != 'synapse-session-file-v1':
            raise ValueError('unsupported checkpoint file format')
        checksum = hashlib.sha256(_canonical(payload)).hexdigest()
        if checksum != envelope['sha256']:
            raise ValueError('checkpoint integrity check failed')
        return IntegratedSession.from_state_dict(payload['session'])
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, RecursionError) as exc:
        raise ValueError('invalid checkpoint JSON or structure') from exc
