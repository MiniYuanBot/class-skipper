"""Real local link checks; no model calls or acceptance claims."""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "tools" / "install_skill.py"
spec = importlib.util.spec_from_file_location("install_skill", MODULE)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


@unittest.skipIf(os.name == "nt", "POSIX symlink checks; Windows uses junctions")
class InstallSkillTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        (self.source / "SKILL.md").write_text("skill", encoding="utf-8")

    def test_install_links_to_source_and_is_idempotent(self):
        destination = self.root / "space 中文" / "class-skipper"
        self.assertEqual(installer.install(self.source, destination), destination)
        self.assertTrue(destination.is_symlink())
        self.assertEqual(destination.resolve(), self.source.resolve())
        self.assertEqual(installer.install(self.source, destination), destination)
        (self.source / "SKILL.md").write_text("edited", encoding="utf-8")
        self.assertEqual((destination / "SKILL.md").read_text(encoding="utf-8"), "edited")

    def test_existing_folder_is_preserved_until_update(self):
        destination = self.root / "class-skipper"
        destination.mkdir()
        (destination / "SKILL.md").write_text("manual edit", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "preserved"):
            installer.install(self.source, destination)
        self.assertFalse(destination.is_symlink())
        self.assertEqual((destination / "SKILL.md").read_text(encoding="utf-8"), "manual edit")
        installer.install(self.source, destination, update=True)
        self.assertTrue(destination.is_symlink())
        backup = destination.with_name("class-skipper.backup")
        self.assertEqual((backup / "SKILL.md").read_text(encoding="utf-8"), "manual edit")

    def test_link_to_another_folder_is_preserved_until_update(self):
        other = self.root / "other"
        other.mkdir()
        destination = self.root / "class-skipper"
        destination.symlink_to(other, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "preserved"):
            installer.install(self.source, destination)
        installer.install(self.source, destination, update=True)
        self.assertEqual(destination.resolve(), self.source.resolve())
        self.assertEqual(destination.with_name("class-skipper.backup").resolve(), other.resolve())

    def test_targets_cover_codex_and_claude_code(self):
        names = [path.parent.parent.name for path in installer.targets("all")]
        self.assertEqual(len(names), 2)
        self.assertTrue(all(path.name == "class-skipper" for path in installer.targets("all")))
        self.assertEqual(installer.targets("claude")[0].parent.name, "skills")

    def test_installer_rejects_nested_destination(self):
        with self.assertRaisesRegex(ValueError, "separate"):
            installer.install(self.source, self.source / "nested" / "class-skipper")


if __name__ == "__main__":
    unittest.main()
