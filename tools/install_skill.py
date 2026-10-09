"""Link the portable skill into Codex and/or Claude Code so repository edits apply at once."""

import argparse
import os
import subprocess
from pathlib import Path


def is_linked(destination, source):
    return destination.exists() and destination.resolve() == source


def create_link(source, destination):
    if os.name == "nt":
        # Junctions need no administrator rights or developer mode.
        try:
            subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(destination), str(source)],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            raise OSError(f"mklink /J failed: {exc.stdout}{exc.stderr}".strip()) from exc
    else:
        destination.symlink_to(source, target_is_directory=True)


def install(source, destination, *, update=False):
    source = source.resolve(strict=True)
    destination = destination.expanduser().absolute()
    if not (source / "SKILL.md").is_file():
        raise ValueError("Source must contain SKILL.md.")
    if is_linked(destination, source):
        return destination
    parent = destination.parent.resolve()
    if parent == source or source in parent.parents:
        raise ValueError("Installation must be separate from the source folder.")
    if os.path.lexists(destination):
        if not update:
            raise ValueError(
                "Destination exists and does not link to this repository; existing "
                "folder preserved. Use --update to back it up and link the new version, "
                "or choose another folder."
            )
        backup = destination.with_name(destination.name + ".backup")
        number = 1
        while os.path.lexists(backup):
            number += 1
            backup = destination.with_name(f"{destination.name}.backup{number}")
        destination.rename(backup)
    parent.mkdir(parents=True, exist_ok=True)
    create_link(source, destination)
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
        help="Replace a differing destination after renaming it to class-skipper.backup*.",
    )
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1] / "skills" / "class-skipper"
    code = 0
    for destination in [args.destination] if args.destination else targets(args.host):
        try:
            print(f"Linked: {install(source, destination, update=args.update)} -> {source}")
        except (ValueError, OSError) as exc:
            print(f"Skipped {destination}: {exc}")
            code = 2
    parser.exit(code)


if __name__ == "__main__":
    main()
