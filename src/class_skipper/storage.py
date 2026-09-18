"""Small atomic files and content identities."""

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path


def digest(value):
    if not isinstance(value, bytes):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True).encode()
    return hashlib.sha256(value).hexdigest()


def atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = value if isinstance(value, bytes) else value.encode()
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_json(path, value):
    atomic(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def read_json(path):
    return json.loads(Path(path).read_text())


def slug(value):
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}", value):
        raise ValueError("Course and lecture IDs must use letters, digits, underscores or hyphens.")
    return value


def managed(root, *parts):
    root = Path(root).absolute()
    target = root.joinpath(*parts)
    if any(p.is_symlink() for p in [target, *target.parents]):
        raise ValueError("Managed output paths cannot contain symlinks.")
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError("Output path escapes the workspace.")
    return target
