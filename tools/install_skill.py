"""Copy the portable skill without overwriting local edits; no model/network calls."""

import argparse
import hashlib
import os
import shutil
import tempfile
from pathlib import Path


def files(folder):
    result = {}
    for path in folder.rglob("*"):
        if path.is_symlink():
            raise ValueError("Skill installation does not copy symlinks.")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            result[path.relative_to(folder).as_posix()] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    return result


def install(source, destination):
    source = source.resolve(strict=True)
    destination = destination.expanduser().absolute()
    if any(path.is_symlink() for path in [destination, *destination.parents]):
        raise ValueError("Installation paths cannot contain symlinks.")
    if source == destination.resolve() or source in destination.resolve().parents:
        raise ValueError("Installation must be separate from the source folder.")
    if not (source / "SKILL.md").is_file():
        raise ValueError("Source must contain SKILL.md.")
    expected = files(source)
    if destination.exists():
        if not destination.is_dir() or files(destination) != expected:
            raise ValueError(
                "Destination differs; existing skill preserved. Choose another folder."
            )
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".class-skipper-", dir=destination.parent))
    try:
        for relative in expected:
            target = temporary / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / relative, target)
        temporary.rename(destination)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--destination",
        type=Path,
        help="Exact installed skill folder (default: CODEX_HOME/skills or ~/.agents/skills).",
    )
    args = parser.parse_args()
    codex_home = os.environ.get("CODEX_HOME")
    base = Path(codex_home) / "skills" if codex_home else Path.home() / ".agents" / "skills"
    source = Path(__file__).resolve().parents[1] / "skills" / "class-skipper"
    try:
        result = install(source, args.destination or base / "class-skipper")
    except (ValueError, OSError) as exc:
        parser.exit(2, f"{exc}\n")
    print(f"Installed: {result}")


if __name__ == "__main__":
    main()
