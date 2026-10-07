"""Copy the portable skill for Codex and/or Claude Code without overwriting local edits."""

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


def install(source, destination, *, update=False):
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
        if not destination.is_dir():
            raise ValueError("Destination is not a folder; existing file preserved.")
        current = files(destination)
        if current == expected:
            return destination
        if not update:
            raise ValueError(
                "Destination differs; existing skill preserved. "
                "Use --update to back it up and replace it, or choose another folder."
            )
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".class-skipper-", dir=destination.parent))
    try:
        for relative in expected:
            target = temporary / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / relative, target)
        if destination.exists():
            backup = destination.with_name(destination.name + ".backup")
            number = 1
            while backup.exists():
                number += 1
                backup = destination.with_name(f"{destination.name}.backup{number}")
            destination.rename(backup)
        temporary.rename(destination)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return destination


def targets(host):
    codex_home = os.environ.get("CODEX_HOME")
    codex = Path(codex_home) / "skills" if codex_home else Path.home() / ".agents" / "skills"
    claude_home = os.environ.get("CLAUDE_CONFIG_DIR")
    claude = Path(claude_home) if claude_home else Path.home() / ".claude"
    choices = {"codex": [codex], "claude": [claude / "skills"]}
    choices["all"] = choices["codex"] + choices["claude"]
    return [base / "class-skipper" for base in choices[host]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--host",
        choices=("codex", "claude", "all"),
        default="all",
        help="codex: CODEX_HOME/skills or ~/.agents/skills; "
        "claude: CLAUDE_CONFIG_DIR/skills or ~/.claude/skills (default: all)",
    )
    parser.add_argument(
        "--destination",
        type=Path,
        help="Exact installed skill folder, for example <project>/.claude/skills/class-skipper.",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Replace a differing installed copy after renaming it to class-skipper.backup*.",
    )
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1] / "skills" / "class-skipper"
    code = 0
    for destination in [args.destination] if args.destination else targets(args.host):
        try:
            print(f"Installed: {install(source, destination, update=args.update)}")
        except (ValueError, OSError) as exc:
            print(f"Skipped {destination}: {exc}")
            code = 2
    parser.exit(code)


if __name__ == "__main__":
    main()
