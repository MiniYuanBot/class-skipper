"""Offline Markdown parser fixtures; no model, host, or course run."""

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "class-skipper" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from markdown_tools import math_issues, scan_markdown  # noqa: E402


class MarkdownScannerTests(unittest.TestCase):
    def scan(self, body):
        references, issues = scan_markdown(body)
        self.assertEqual(issues, [])
        return references

    def test_nested_and_escaped_caption_brackets_preserve_offsets(self):
        body = (
            r'![imm[0:5], Instr[6-0], \[literal\]](assets/instruction.png "original [title]")'
            "\n[流水线](section:section-2#转发)"
        )
        image, link = self.scan(body)
        self.assertEqual(image.kind, "image")
        self.assertEqual(image.label, r"imm[0:5], Instr[6-0], \[literal\]")
        self.assertEqual(image.target, "assets/instruction.png")
        self.assertEqual(link.target, "section:section-2#转发")
        self.assertEqual(body[image.start : image.end], body.splitlines()[0])
        rewritten = body[: image.target_start] + "../assets/new.png" + body[image.target_end :]
        self.assertEqual(rewritten, body.replace("assets/instruction.png", "../assets/new.png"))

    def test_balanced_escaped_and_angle_destinations_with_titles(self):
        cases = [
            ('![x](assets/plot(v2).png "title (with punctuation)")', "assets/plot(v2).png"),
            (r"![x](assets/plot\(v2\).png 'single title')", "assets/plot(v2).png"),
            ("![x](<assets/plot (v2).png> 'title')", "assets/plot (v2).png"),
            ("[x](https://example.test/a_(b_(c)) (link title))", "https://example.test/a_(b_(c))"),
            ("[x](assets/a%20b.png?a=1&amp;b=2)", "assets/a%20b.png?a=1&b=2"),
        ]
        for body, expected in cases:
            with self.subTest(body=body):
                (reference,) = self.scan(body)
                self.assertEqual(reference.target, expected)
                rewritten = body[: reference.target_start] + "NEW" + body[reference.target_end :]
                self.assertIn("NEW", rewritten)
                if "<" in body:
                    self.assertIn("<NEW>", rewritten)

    def test_wikilinks_keep_aliases_and_fragments(self):
        body = "[[中文章节#小结|自定义 [显示文字]]] [[#本页标题]] [[chapter#^block]]"
        references = self.scan(body)
        self.assertEqual([ref.kind for ref in references], ["wiki"] * 3)
        self.assertEqual(
            [ref.target for ref in references], ["中文章节#小结", "#本页标题", "chapter#^block"]
        )
        self.assertEqual(references[0].label, "自定义 [显示文字]")
        self.assertEqual(references[1].label, "#本页标题")
        self.assertEqual(references[2].label, "chapter#^block")
        (table_reference,) = self.scan(r"| [[chapter\|中文标题]] |")
        self.assertEqual(table_reference.target, "chapter")
        self.assertEqual(table_reference.label, "中文标题")

    def test_code_comments_and_math_are_not_references(self):
        body = "\n".join(
            [
                "```markdown",
                "![fenced](missing.png)",
                "```",
                "    ![indented](missing.png)",
                "`![inline](missing.png)` and `` ` ![also](missing.png) ``",
                "<!-- ![comment](missing.png) -->",
                "$x + [inline](fake.md)$",
                "$$",
                "![display](missing.png)",
                "$$",
                r"\( [paren](fake.md) \)",
                r"\[ ![bracket](missing.png) \]",
                r"\![escaped](missing.png)",
                "![real](assets/real.png)",
            ]
        )
        references = self.scan(body)
        self.assertEqual(
            [(ref.kind, ref.target) for ref in references],
            [("link", "missing.png"), ("image", "assets/real.png")],
        )

    def test_callout_content_and_quoted_fences(self):
        body = "\n".join(
            [
                "> [!info] 来源",
                "> ![imm[0:5]](assets/real.png)",
                "> ```md",
                "> ![fake](missing.png)",
                "> ```",
                ">     ![indented](missing.png)",
                "> [正文](section:next)",
            ]
        )
        self.assertEqual(
            [ref.target for ref in self.scan(body)], ["assets/real.png", "section:next"]
        )

    def test_list_continuations_keep_images_and_math_visible(self):
        for marker in ["1. ", "- ", "+ ", "* "]:
            for quote in ["", "> "]:
                with self.subTest(marker=marker, quote=quote):
                    body = "\n".join(
                        [
                            quote + marker + "步骤",
                            quote,
                            quote + "    ![位域 imm[0:5]](assets/fields.png)",
                            quote + "    功耗 $½CV²$。",
                        ]
                    )
                    self.assertEqual([ref.target for ref in self.scan(body)], ["assets/fields.png"])
                    self.assertEqual([line for line, _ in math_issues(body)], [4])

    def test_lists_preserve_nested_indented_and_fenced_code(self):
        body = "\n".join(
            [
                "1. 步骤",
                "",
                "       ![code](missing.png) ½CV²",
                "",
                "    - 子步骤",
                "",
                "      ![图](assets/real.png)",
                "      ```",
                "      ![fenced](missing.png) ½CV²",
                "      ```",
                "",
                "普通段落",
                "",
                "    ![outside code](missing.png) ½CV²",
            ]
        )
        self.assertEqual([ref.target for ref in self.scan(body)], ["assets/real.png"])
        self.assertEqual(math_issues(body), [])

    def test_alt_code_or_math_does_not_become_an_independent_link(self):
        body = r"![`imm[0:5]`, [[not a link]], $x [not](link)$](assets/figure.png)"
        references = self.scan(body)
        self.assertEqual(len(references), 1)
        self.assertEqual(references[0].target, "assets/figure.png")
        self.assertEqual(len(math_issues(body)), 1)

    def test_math_like_url_characters_do_not_hide_following_images(self):
        body = "[cost](https://example.test/$price) ![figure](assets/figure.png) $x$"
        self.assertEqual(
            [ref.target for ref in self.scan(body)],
            ["https://example.test/$price", "assets/figure.png"],
        )
        code_url = "[url](https://example.test/`path) ![figure](figure.png) `code`"
        self.assertEqual(
            [ref.target for ref in self.scan(code_url)],
            ["https://example.test/`path", "figure.png"],
        )

    def test_unsupported_and_malformed_images_have_source_lines(self):
        cases = [
            "![alt][ref]",
            "![alt][]",
            "![alt]",
            "![[figure.png]]",
            "![alt](broken.png",
            "![alt](a(b.png)",
            "![unclosed alt",
            '![alt](image.png "unclosed title)',
        ]
        for case in cases:
            with self.subTest(case=case):
                references, issues = scan_markdown("Intro\n\n" + case)
                self.assertEqual(references, [])
                self.assertEqual(len(issues), 1)
                self.assertEqual(issues[0][0], 3)

    def test_clickable_images_are_diagnosed_instead_of_silently_omitted(self):
        references, issues = scan_markdown("Intro\n[![图](assets/figure.png)](chapter.md)")
        self.assertEqual([reference.target for reference in references], ["chapter.md"])
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0][0], 2)
        self.assertIn("standalone image", issues[0][1])
        self.scan("[`![literal](example.png)`](chapter.md)")

    def test_plain_brackets_and_footnotes_are_not_issues(self):
        body = "普通 [文字]、imm[0:5]、Instr[6-0] 和脚注[^1]。\n[^1]: explanation"
        self.assertEqual(scan_markdown(body), ([], []))

    def test_legacy_link_targets_with_spaces_and_malformed_links(self):
        references = self.scan("[旧标题](02 动态功耗.md#Power) [歧义](01 重名)")
        self.assertEqual(
            [reference.target for reference in references], ["02 动态功耗.md#Power", "01 重名"]
        )
        for body in ['[x](file.md "broken title)', "[x](unclosed", "![x](spaces here.png)"]:
            with self.subTest(body=body):
                references, issues = scan_markdown(body)
                self.assertEqual(references, [])
                self.assertEqual(len(issues), 1)

    def test_math_unicode_and_alt_issues(self):
        body = "\n".join(
            [
                "Power ≈ ½CV²Af",
                "$V₂ + ⅓$",
                "![Power $P$](assets/power.png)",
                r"图：$P \approx \frac{1}{2} C V^{2} A f$。",
            ]
        )
        issues = math_issues(body)
        self.assertEqual([line for line, _ in issues], [1, 2, 3])
        self.assertIn("caption", issues[2][1])
        self.assertEqual(len(math_issues("ⁱ ⁿ ₓ ⅟ ↉ ᵀ ᶜ")), 1)
        self.assertEqual(len(math_issues("Vᵀ")), 1)

    def test_math_preserves_literal_code_comments_and_urls(self):
        body = "\n".join(
            [
                "```",
                "Power ≈ ½CV²Af",
                "```",
                "`½CV²` <!-- ½CV² -->",
                "    ½CV²",
                "[ordinary label](https://example.test/½CV²)",
                "![plain](assets/½CV².png)",
                r"![cost \$5, `Instr[6-0]`](assets/plain.png)",
                r"![literal `$x$`, cost $5](assets/plain.png)",
                "CPU Power Instruction imm[0:5] footnote[^1]",
            ]
        )
        self.assertEqual(math_issues(body), [])

    def test_alt_math_delimiters_all_reported_but_caption_math_valid(self):
        for formula in ["$P$", "$$P$$", r"\(P\)", r"\[P\]"]:
            with self.subTest(formula=formula):
                self.assertEqual(len(math_issues(f"![{formula}](assets/p.png)")), 1)
                self.assertEqual(math_issues(f"![plain](assets/p.png)\n\n图：{formula}"), [])


if __name__ == "__main__":
    unittest.main()
