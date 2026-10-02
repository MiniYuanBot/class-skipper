"""Offline skill helper checks with real tiny parsers; no model or course/API run."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "class-skipper" / "scripts"


def small_pdf(path):
    """Write a real one-page PDF with a valid xref, using only the standard library."""
    stream = b"BT /F1 12 Tf 20 150 Td (Local PDF fixture tail condition) Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    data, offsets = b"%PDF-1.4\n", [0]
    for number, body in enumerate(objects, 1):
        offsets.append(len(data))
        data += str(number).encode() + b" 0 obj\n" + body + b"\nendobj\n"
    xref = len(data)
    data += b"xref\n0 6\n0000000000 65535 f \n"
    data += b"".join(f"{offset:010} 00000 n \n".encode() for offset in offsets[1:])
    data += b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n" + str(xref).encode() + b"\n%%EOF\n"
    path.write_bytes(data)


class OfflineSkillTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "notes workspace"
        self.text = self.base / "lecture.txt"
        self.text.write_text(
            "完整文本\n" + "长段落\n" * 1200 + "TAIL 必要条件", encoding="utf-8-sig"
        )

    def cli(self, *args, expected=0):
        result = subprocess.run(
            [sys.executable, "-X", "utf8", str(SCRIPTS / "local.py"), *map(str, args)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def prepare(self, *extra, lecture="01"):
        return self.cli(
            "prepare",
            "--root",
            self.root,
            "--course",
            "demo",
            "--lecture",
            lecture,
            "--title",
            "课程标题",
            "--slides",
            self.text,
            *extra,
        )

    def write_json(self, filename, value):
        path = self.base / filename
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path

    def document(self, sections=None):
        return self.write_json(
            "document.json",
            {
                "schema_version": 1,
                "title": "完整讲义",
                "introduction": "先看完整材料。",
                "synthesis": "必要条件不能省略。",
                "uncertainties": [],
                "sections": sections
                or [
                    {
                        "id": "concept",
                        "title": "概念",
                        "markdown": (
                            "### 定义\r\n\r\n#### 细节\r\n\r\n```python\r\n"
                            "### literal comment\r\n```\r\n\r\n$$\r\n"
                            "### literal math\r\n$$\r\n\r\n![原图](assets/figure.png)"
                        ),
                        "source_ids": ["s1b1"],
                    },
                    {
                        "id": "condition",
                        "title": "条件",
                        "markdown": "### 必要条件\n\n保留原材料最后一段。",
                        "source_ids": ["s1b2"],
                    },
                ],
            },
        )

    def publish_document(self):
        prepared = self.prepare("--options", '{"course_name":"演示课程"}')
        asset = self.base / "figure.png"
        asset.write_bytes(b"referenced visual")
        document = self.document()
        command = ("publish", "--run", prepared["run"], "--document", document, "--asset", asset)
        return prepared, self.cli(*command), command

    def assert_local_links(self, root):
        import re

        for page in root.rglob("*.md"):
            for reference in re.findall(r"\]\(([^()]+)\)", page.read_text(encoding="utf-8")):
                self.assertTrue(
                    (page.parent / reference).is_file(), f"Broken link in {page}: {reference}"
                )

    def test_structured_publication_navigation_sources_and_intermediate_layout(self):
        prepared, result, _ = self.publish_document()
        run = Path(prepared["run"])
        for directory in (
            "requests",
            "chapters",
            "visuals/pages",
            "visuals/crops",
            "draft",
            "revision",
            "final",
            "cache",
        ):
            self.assertTrue((run / directory).is_dir())
        self.assertTrue((self.root / "input").is_dir())
        for filename in ("run.json", "materials.json", "status.json"):
            self.assertEqual(
                json.loads((run / filename).read_text(encoding="utf-8"))["schema_version"], 1
            )
        status = run / "status.json"
        status.write_text('{"schema_version":1,"manual":"keep"}', encoding="utf-8")
        self.prepare("--options", '{"course_name":"演示课程"}')
        self.assertIn("manual", status.read_text(encoding="utf-8"))
        output = self.root / "output"
        self.assert_local_links(output)
        self.assertEqual(result["chapters"], 2)
        chapter = output / "demo" / "01" / "chapters" / "concept.md"
        body = chapter.read_text(encoding="utf-8")
        self.assertIn('type: "course-note"', body)
        self.assertIn('section: "concept"', body)
        self.assertIn("lecture.txt — Text segment 1", body)
        self.assertIn("../assets/figure.png", body)
        self.assertIn("\n## 定义\n", body)
        self.assertIn("\n### 细节\n", body)
        self.assertIn("\n### literal comment\n", body)
        self.assertIn("\n### literal math\n", body)
        self.assertNotIn(b"\r", chapter.read_bytes())
        self.assertFalse(list(output.rglob("*.json")))
        self.assertIn("演示课程", Path(result["index"]).read_text(encoding="utf-8"))

    def test_structured_root_and_chapter_manual_changes_block_whole_publication(self):
        _, result, command = self.publish_document()
        root_index = Path(result["index"])
        root_index.write_text("manual library navigation", encoding="utf-8")
        conflict = self.cli(*command, expected=5)
        self.assertIn("index.md", conflict["conflicts"])
        self.assertEqual(root_index.read_text(encoding="utf-8"), "manual library navigation")
        root_index.write_bytes((Path(conflict["candidate"]) / "index.md").read_bytes())
        chapter = self.root / "output" / "demo" / "01" / "chapters" / "concept.md"
        chapter.write_text("manual chapter correction", encoding="utf-8")
        conflict = self.cli(*command, expected=5)
        self.assertIn("demo/01/chapters/concept.md", conflict["conflicts"])
        self.assertEqual(chapter.read_text(encoding="utf-8"), "manual chapter correction")

    def test_structured_export_preserves_full_navigation_and_manual_edits(self):
        self.publish_document()
        command = (
            "export",
            "--root",
            self.root,
            "--course",
            "demo",
            "--vault",
            self.base / "vault",
            "--course-name",
            "课程",
        )
        result = self.cli(*command)
        target = Path(result["target"])
        self.assert_local_links(target)
        chapter = target / "demo" / "01" / "chapters" / "concept.md"
        self.assertTrue(chapter.is_file())
        chapter.write_text("edited in Obsidian", encoding="utf-8")
        self.cli(*command, expected=5)
        self.assertEqual(chapter.read_text(encoding="utf-8"), "edited in Obsidian")

    def test_structured_invalid_ids_and_removes_only_unchanged_stale_chapters(self):
        prepared, _, command = self.publish_document()
        document = self.base / "document.json"
        body = json.loads(document.read_text(encoding="utf-8"))
        body["sections"][0]["source_ids"] = ["unknown"]
        document.write_text(json.dumps(body), encoding="utf-8")
        self.cli(*command, expected=2)
        body["sections"][0]["source_ids"] = ["s1b1"]
        body["schema_version"] = 2
        document.write_text(json.dumps(body), encoding="utf-8")
        self.cli(*command, expected=2)
        body["schema_version"] = 1
        body["sections"][1]["id"] = body["sections"][0]["id"]
        document.write_text(json.dumps(body), encoding="utf-8")
        self.cli(*command, expected=2)
        body["sections"][1]["id"] = "condition"
        body["sections"] = [body["sections"][1]]
        document.write_text(json.dumps(body), encoding="utf-8")
        lecture = self.root / "output" / "demo" / "01"
        stale = lecture / "chapters" / "concept.md"
        original = stale.read_bytes()
        stale.write_text("manual correction in retired chapter", encoding="utf-8")
        self.cli(*command, expected=5)
        self.assertEqual(stale.read_text(encoding="utf-8"), "manual correction in retired chapter")
        self.assertTrue((lecture / "assets" / "figure.png").is_file())
        stale.write_bytes(original)
        self.cli(*command)
        self.assertFalse((lecture / "chapters" / "concept.md").exists())
        self.assertFalse((lecture / "assets" / "figure.png").exists())
        self.assertTrue((lecture / "chapters" / "condition.md").is_file())
        self.assertTrue(Path(prepared["run"]).is_dir())

    def test_structured_course_navigation_uses_publication_order(self):
        _, result, _ = self.publish_document()
        asset = self.base / "figure.png"
        for lecture in ("l2", "l10"):
            prepared = self.prepare(lecture=lecture)
            self.cli(
                "publish",
                "--run",
                prepared["run"],
                "--document",
                self.base / "document.json",
                "--asset",
                asset,
            )
        index = Path(result["course_index"]).read_text(encoding="utf-8")
        self.assertLess(index.index("](l2/index.md)"), index.index("](l10/index.md)"))

    def test_complete_utf8_materials_identity_and_no_repository_dependency(self):
        first = self.prepare()
        materials = json.loads(Path(first["materials"]).read_text(encoding="utf-8"))
        self.assertEqual(len(materials["sources"]), 1)
        self.assertIn("TAIL 必要条件", materials["units"][-1]["text"])
        self.assertGreater(len(materials["units"]), 1)
        self.assertEqual(first["run"], self.prepare()["run"])
        self.assertNotEqual(first["run"], self.prepare("--options", '{"language":"en"}')["run"])
        self.assertNotEqual(first["run"], self.prepare("--transcript", self.text)["run"])
        self.text.write_text("updated full source", encoding="utf-8")
        self.assertNotEqual(first["run"], self.prepare()["run"])

    def test_cache_invalidates_prompt_options_source_and_upstream_and_archives_refresh(
        self,
    ):
        run = self.prepare()["run"]
        request = self.write_json(
            "request.json",
            {
                "stage": "write:01",
                "instructions": "full prompt",
                "options": {"language": "zh"},
            },
        )
        response = self.write_json("response.json", {"markdown": "labeled model double response"})
        upstream = self.write_json("plan.json", {"sections": ["01"]})
        command = ("--run", run, "--request", request, "--upstream", upstream)
        self.assertEqual(self.cli("cache", "lookup", *command)["status"], "miss")
        stored = self.cli("cache", "store", *command, "--response", response)
        self.assertEqual(
            self.cli("cache", "lookup", *command)["response"]["markdown"],
            "labeled model double response",
        )
        response.write_text('{"markdown":"new complete response"}', encoding="utf-8")
        self.cli("cache", "store", *command, "--response", response, expected=2)
        self.cli("cache", "store", *command, "--response", response, "--refresh")
        history = list((Path(run) / "cache" / "history").glob("*.json"))
        self.assertEqual(len(history), 1)
        self.assertIn("labeled model double", history[0].read_text(encoding="utf-8"))
        original = json.loads(request.read_text(encoding="utf-8"))
        for key, value in (
            ("instructions", "changed full prompt"),
            ("options", {"language": "en"}),
        ):
            request.write_text(json.dumps(original | {key: value}), encoding="utf-8")
            self.assertEqual(self.cli("cache", "lookup", *command)["status"], "miss")
        request.write_text(json.dumps(original), encoding="utf-8")
        upstream.write_text('{"sections":["02"]}', encoding="utf-8")
        self.assertEqual(self.cli("cache", "lookup", *command)["status"], "miss")
        self.text.write_text("new material", encoding="utf-8")
        self.assertEqual(
            self.cli("cache", "lookup", "--run", self.prepare()["run"], "--request", request)[
                "status"
            ],
            "miss",
        )
        self.assertTrue(Path(stored["cache"]).exists())

    def test_publish_assets_note_and_index_manual_protection(self):
        run = self.prepare()["run"]
        note = self.base / "final.md"
        note.write_text("# 内容\n\n![原图](assets/figure.png)\n", encoding="utf-8")
        asset = self.base / "figure.png"
        unused = self.base / "unused.png"
        asset.write_bytes(b"local image bytes")
        unused.write_bytes(b"not referenced")
        command = (
            "publish",
            "--run",
            run,
            "--note",
            note,
            "--asset",
            asset,
            "--asset",
            unused,
        )
        result = self.cli(*command)
        published = Path(result["notes"])
        index = Path(result["index"])
        self.assertFalse((published.parent / "assets" / unused.name).exists())
        published.write_text("manual note", encoding="utf-8")
        result = self.cli(*command, expected=5)
        self.assertEqual(published.read_text(encoding="utf-8"), "manual note")
        self.assertIn("01/notes.md", result["conflicts"])
        self.assertTrue((Path(result["candidate"]) / "01" / "notes.md").is_file())
        published.write_text(note.read_text(encoding="utf-8"), encoding="utf-8")
        index.write_text("manual index", encoding="utf-8")
        self.cli(*command, expected=5)
        self.assertEqual(index.read_text(encoding="utf-8"), "manual index")

    def test_export_preserves_manual_edits_and_rewrites_images(self):
        run = self.prepare()["run"]
        note = self.base / "final.md"
        note.write_text("# Notes\n\n![Figure](assets/figure.png)", encoding="utf-8")
        asset = self.base / "figure.png"
        asset.write_bytes(b"local image")
        self.cli("publish", "--run", run, "--note", note, "--asset", asset)
        vault = self.base / "vault"
        command = (
            "export",
            "--root",
            self.root,
            "--course",
            "demo",
            "--vault",
            vault,
            "--course-name",
            "测试课程",
        )
        result = self.cli(*command)
        exported = Path(result["target"]) / "01.md"
        self.assertIn("assets/01/figure.png", exported.read_text(encoding="utf-8"))
        self.assertIn("](01.md)", Path(result["index"]).read_text(encoding="utf-8"))
        exported.write_text("manual vault note", encoding="utf-8")
        self.cli(*command, expected=5)
        self.assertEqual(exported.read_text(encoding="utf-8"), "manual vault note")

    def test_portable_names_reject_case_collisions(self):
        self.prepare(lecture="Lesson")
        self.cli(
            "prepare",
            "--root",
            self.root,
            "--course",
            "demo",
            "--lecture",
            "lesson",
            "--title",
            "Collision",
            "--slides",
            self.text,
            expected=2,
        )
        self.cli(
            "prepare",
            "--root",
            self.root,
            "--course",
            "CON",
            "--lecture",
            "01",
            "--title",
            "Reserved",
            "--slides",
            self.text,
            expected=2,
        )

    def test_real_docx_and_pptx_parser_fixtures(self):
        from docx import Document
        from pptx import Presentation
        from pptx.util import Inches

        doc = Document()
        doc.add_paragraph("DOCX first body")
        doc.add_table(rows=1, cols=1).cell(0, 0).text = "DOCX table condition"
        doc.add_paragraph("DOCX final tail")
        docx = self.base / "fixture.docx"
        doc.save(docx)
        deck = Presentation()
        slide = deck.slides.add_slide(deck.slide_layouts[6])
        slide.shapes.add_textbox(
            Inches(1), Inches(1), Inches(3), Inches(1)
        ).text = "PPTX slide concept"
        slide.notes_slide.notes_text_frame.text = "PPTX speaker final condition"
        pptx = self.base / "fixture.pptx"
        deck.save(pptx)
        result = self.prepare("--slides", pptx, "--transcript", docx)
        materials = json.loads(Path(result["materials"]).read_text(encoding="utf-8"))
        text = "\n".join(unit["text"] for unit in materials["units"])
        for expected in (
            "DOCX table condition",
            "DOCX final tail",
            "PPTX speaker final condition",
        ):
            self.assertIn(expected, text)
        self.assertIn("Slide 1", [u["location"] for u in materials["units"]])
        self.assertTrue(any(u["location"].startswith("DOCX body") for u in materials["units"]))

    def test_real_pdf_parser_render_crop_and_changed_source(self):
        from PIL import Image

        pdf = self.base / "fixture.pdf"
        small_pdf(pdf)
        result = self.prepare("--slides", pdf)
        materials = json.loads(Path(result["materials"]).read_text(encoding="utf-8"))
        unit = next(u for u in materials["units"] if u["source"] == "s2")
        self.assertIn("tail condition", unit["text"])
        self.assertEqual(unit["location"], "PDF p.1")
        output = self.base / "figure.png"
        self.cli(
            "render",
            "--run",
            result["run"],
            "--source",
            "s2",
            "--page",
            "1",
            "--crop",
            "0,0,50,60",
            "--output",
            output,
        )
        with Image.open(output) as image:
            self.assertEqual(image.size, (50, 60))
        previous = output.read_bytes()
        self.cli(
            "render",
            "--run",
            result["run"],
            "--source",
            "s2",
            "--page",
            "1",
            "--crop",
            "0,0,9999,9999",
            "--output",
            output,
            expected=2,
        )
        self.assertEqual(output.read_bytes(), previous)
        pdf.write_bytes(pdf.read_bytes() + b"\n% changed source\n")
        self.cli(
            "render",
            "--run",
            result["run"],
            "--source",
            "s2",
            "--page",
            "1",
            "--output",
            output,
            expected=2,
        )


if __name__ == "__main__":
    unittest.main()
