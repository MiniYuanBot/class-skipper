"""Real local copy checks; no model calls or acceptance claims."""

import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "tools" / "install_skill.py"
spec = importlib.util.spec_from_file_location("install_skill", MODULE)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallSkillTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_install_is_portable_and_preserves_modified_destination(self):
        source = self.root / "source"
        source.mkdir()
        (source / "SKILL.md").write_text("skill", encoding="utf-8")
        (source / "scripts").mkdir()
        (source / "scripts" / "local.py").write_text("pass", encoding="utf-8")
        destination = self.root / "space 中文" / "class-skipper"
        self.assertEqual(installer.install(source, destination), destination)
        self.assertEqual(installer.install(source, destination), destination)
        (destination / "SKILL.md").write_text("manual edit", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "preserved"):
            installer.install(source, destination)
        self.assertEqual((destination / "SKILL.md").read_text(encoding="utf-8"), "manual edit")

    def test_installer_rejects_nested_destination(self):
        (self.root / "SKILL.md").write_text("skill", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "separate"):
            installer.install(self.root, self.root / "nested")


if __name__ == "__main__":
    unittest.main()
