"""Small append-only JSON store for independently dated research artifacts."""
import json
import os
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Timezone is required')
    return parsed


def research_day(value):
    return timestamp(value).astimezone(timezone(timedelta(hours=9))).date().isoformat()


def atomic_json(path, doc):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(doc, ensure_ascii=False, indent=2, allow_nan=False)+'\n'
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.research-')
    try:
        with os.fdopen(fd, 'w') as out:
            out.write(encoded)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def immutable_json(path, doc):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(doc, ensure_ascii=False, indent=2, allow_nan=False)+'\n'
    try:
        with path.open('x') as out:
            out.write(encoded)
    except FileExistsError:
        if json.loads(path.read_text()) != doc:
            raise ValueError(f'Immutable research collision: {path}')


def safe_path(root, relative):
    path = (Path(root)/relative).resolve()
    if not path.is_relative_to(Path(root).resolve()):
        raise ValueError('Path escapes research store')
    return path
