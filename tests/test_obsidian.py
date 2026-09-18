"""Local vault publication tests; no model or Obsidian application calls."""

from pathlib import Path

import pytest

from class_skipper.cli import main
from class_skipper.config import DEFAULTS
from class_skipper.obsidian import export_course


@pytest.fixture
def course(tmp_path):
    output = tmp_path / "output"
    lecture = output / "os" / "l02"
    (lecture / "assets").mkdir(parents=True)
    (lecture / "assets" / "flow.png").write_bytes(b"local image bytes")
    (lecture / "notes.md").write_text("# Lecture\n\nMechanism.\n\n![Flow](assets/flow.png)\n")
    (output / "os" / "index.md").write_text("# 操作系统\n\n- [Lecture](l02/notes.md)\n")
    vault = tmp_path / "vault"
    (vault / ".obsidian").mkdir(parents=True)
    (vault / ".obsidian" / "settings.json").write_text('{"keep":true}')
    return DEFAULTS | {
        "output": str(output),
        "workspace": str(tmp_path / "workspace"),
        "obsidian_vault": str(vault),
    }


def test_export_links_assets_and_idempotence(course):
    result, code = export_course(course, "os")
    assert code == 0 and result["images"] == 1
    target = Path(result["vault_course"])
    assert target.name == "operating-system"
    assert "(l02.md)" in (target / "index.md").read_text()
    assert "(assets/l02/flow.png)" in (target / "l02.md").read_text()
    assert (target / "assets/l02/flow.png").read_bytes() == b"local image bytes"
    modified = (target / "l02.md").stat().st_mtime_ns
    assert export_course(course, "os")[1] == 0
    assert (target / "l02.md").stat().st_mtime_ns == modified
    assert not list(target.rglob("*.json"))
    assert (target.parent / ".obsidian/settings.json").read_text() == '{"keep":true}'


def test_vault_edits_are_preserved_with_reviewable_candidate(course):
    result, _ = export_course(course, "os")
    target = Path(result["vault_course"])
    (target / "l02.md").write_text("My own annotations.")
    (target / "personal.md").write_text("Personal note.")
    result, code = export_course(course, "os")
    assert code == 5 and result["conflicts"] == ["l02.md"]
    assert (target / "l02.md").read_text() == "My own annotations."
    assert (target / "personal.md").read_text() == "Personal note."
    assert (Path(result["candidate"]) / "l02.md").exists()


def test_invalid_course_or_missing_asset_never_publishes(course):
    with pytest.raises(ValueError):
        export_course(course, "os", name="../escape")
    (Path(course["output"]) / "os/l02/assets/flow.png").unlink()
    with pytest.raises(FileNotFoundError):
        export_course(course, "os")
    assert not (Path(course["obsidian_vault"]) / "operating-system").exists()


def test_export_cli_needs_no_model_credentials(course, tmp_path):
    import yaml

    config = tmp_path / "config.yaml"
    config.write_text(yaml.safe_dump(course))
    assert (
        main(["--config", str(config), "--env-file", str(tmp_path / "absent.env"), "export", "os"])
        == 0
    )


def test_generate_cli_auto_exports_after_success(course, tmp_path, monkeypatch):
    import yaml

    import class_skipper.cli as cli

    config = tmp_path / "config.yaml"
    config.write_text(yaml.safe_dump(course))
    note = Path(course["output"]) / "os/l02/notes.md"
    monkeypatch.setattr(cli, "generate", lambda *a, **kw: ({"notes": str(note)}, 0))
    assert (
        main(
            [
                "--config",
                str(config),
                "--env-file",
                str(tmp_path / "absent.env"),
                "generate",
                "os",
                "l02",
                "--slides",
                "unused.pdf",
            ]
        )
        == 0
    )
    assert (Path(course["obsidian_vault"]) / "operating-system/l02.md").exists()


@pytest.mark.parametrize("edited", [False, True])
def test_removing_obsolete_assets_preserves_user_changes(course, edited):
    result, _ = export_course(course, "os")
    target = Path(result["vault_course"])
    asset = target / "assets/l02/flow.png"
    if edited:
        asset.write_bytes(b"personal diagram edit")
    personal = target / "personal.md"
    personal.write_text("Unrelated personal notes.")
    (Path(course["output"]) / "os/l02/notes.md").write_text("# Lecture\n\nText only.\n")
    _, code = export_course(course, "os")
    assert personal.read_text() == "Unrelated personal notes."
    if edited:
        assert code == 5 and asset.read_bytes() == b"personal diagram edit"
        assert "![Flow]" in (target / "l02.md").read_text()
    else:
        assert code == 0 and not asset.exists()
        assert "Text only." in (target / "l02.md").read_text()
