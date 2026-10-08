"""Small source-preserving scanner for the Markdown emitted by this skill.

This is intentionally not a Markdown renderer. Unsupported image forms are
reported instead of being silently omitted from asset collection.
"""

from __future__ import annotations

import html
import re
import string
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class Reference:
    kind: str
    start: int
    end: int
    target_start: int
    target_end: int
    label: str
    target: str


_ESCAPE = re.compile(r"\\([" + re.escape(string.punctuation) + r"])")


def _escaped(body: str, index: int) -> bool:
    preceding = index - 1
    while preceding >= 0 and body[preceding] == "\\":
        preceding -= 1
    return (index - preceding - 1) % 2 == 1


def _mark(mask: bytearray, start: int, end: int) -> None:
    mask[start:end] = b"\1" * (end - start)


def _literal_mask(body: str) -> bytearray:
    """Protect fenced/indented/inline code and comments, including blockquotes."""
    mask = bytearray(len(body))
    fence = None
    list_indents = []
    quote_depth = 0
    offset = 0
    for line in body.splitlines(keepends=True):
        quote = re.match(r"^(?: {0,3}>[ \t]?)*", line)[0]
        depth = quote.count(">")
        if depth != quote_depth:
            list_indents.clear()
            quote_depth = depth
        content = line[len(quote) :].expandtabs(4)
        indent = len(content) - len(content.lstrip(" "))
        if not fence and content.strip():
            while list_indents and indent < list_indents[-1]:
                list_indents.pop()
            base = list_indents[-1] if list_indents else 0
            item = re.match(r" {0,3}(?:[-+*]|\d{1,9}[.)])([ ]+)", content[base:])
            if item:
                # Five spaces after a marker starts code, using one for list padding.
                padding = len(item[1]) if len(item[1]) <= 4 else 1
                base += item.start(1) + padding
                list_indents.append(base)
            content = content[base:]
        elif list_indents and indent >= list_indents[-1]:
            content = content[list_indents[-1] :]
        if fence:
            _mark(mask, offset, offset + len(line))
            if re.fullmatch(
                r" {0,3}" + re.escape(fence[0]) + "{" + str(fence[1]) + r",}[ \t\r\n]*", content
            ):
                fence = None
        else:
            match = re.match(r" {0,3}(`{3,}|~{3,})(.*)", content)
            if match and not (match[1][0] == "`" and "`" in match[2]):
                fence = (match[1][0], len(match[1]))
                _mark(mask, offset, offset + len(line))
            elif content.startswith(("    ", "\t")):
                _mark(mask, offset, offset + len(line))
        offset += len(line)
    index = 0
    while index < len(body):
        if mask[index]:
            index += 1
        elif body[index] == "[" or body.startswith("![", index):
            # Literal-looking punctuation in a URL must not start code/comments.
            opening = index + 1 if body[index] == "!" else index
            if body.startswith("[[", opening):
                end = _wiki_end(body, opening)
                index = end + 2 if end is not None else index + 1
                continue
            close = _bracket_end(body, opening)
            parsed = None
            if close is not None and body[close + 1 : close + 2] == "(":
                parsed = _inline_target(body, close + 1)
                if not parsed and opening == index:
                    parsed = _legacy_link_target(body, close + 1)
            if parsed:
                label_start = opening + 1
                label_mask = _literal_mask(body[label_start:close])
                for position, protected in enumerate(label_mask, label_start):
                    if protected:
                        mask[position] = 1
                index = parsed[2]
            else:
                index += 1
        elif body.startswith("<!--", index):
            end = body.find("-->", index + 4)
            end = len(body) if end < 0 else end + 3
            _mark(mask, index, end)
            index = end
        elif body[index] == "`" and not _escaped(body, index):
            run = re.match(r"`+", body[index:])[0]
            end = index + len(run)
            while True:
                end = body.find(run, end)
                if end < 0:
                    index += len(run)
                    break
                after = end + len(run)
                if (
                    not mask[end]
                    and body[end - 1] != "`"
                    and (after == len(body) or body[after] != "`")
                ):
                    _mark(mask, index, after)
                    index = after
                    break
                end = after
        else:
            index += 1
    return mask


def _math_end(body: str, index: int, mask: bytearray):
    opener = closer = None
    if body.startswith("$$", index):
        opener = closer = "$$"
    elif body[index] == "$" and index + 1 < len(body) and not body[index + 1].isspace():
        opener = closer = "$"
    elif body.startswith((r"\(", r"\["), index):
        opener = body[index : index + 2]
        closer = r"\)" if opener == r"\(" else r"\]"
    if opener:
        end = index + len(opener)
        while True:
            end = body.find(closer, end)
            if end < 0:
                return None
            if not mask[end] and not _escaped(body, end):
                if closer != "$" or (body[end - 1] != "$" and body[end : end + 2] != "$$"):
                    return end + len(closer)
            end += len(closer)
    return None


def _bracket_end(body: str, opening: int):
    depth, index = 1, opening + 1
    while index < len(body):
        if body[index] == "\\":
            index += 2
            continue
        if body[index] == "[":
            depth += 1
        elif body[index] == "]":
            depth -= 1
            if depth == 0:
                return index
        if body[index : index + 2] == "\n\n":
            return None
        index += 1
    return None


def _wiki_end(body: str, opening: int):
    depth, index = 0, opening + 2
    while index < len(body) and body[index] not in "\r\n":
        if body[index] == "\\":
            index += 2
            continue
        if depth == 0 and body.startswith("]]", index):
            return index
        if body[index] == "[":
            depth += 1
        elif body[index] == "]" and depth:
            depth -= 1
        index += 1
    return None


def _inline_target(body: str, opening: int):
    """Return (target_start, target_end, reference_end), excluding title/angles."""
    index = opening + 1
    while index < len(body) and body[index].isspace():
        index += 1
    start = index
    if index < len(body) and body[index] == "<":
        start = index = index + 1
        while index < len(body) and body[index] != ">":
            if body[index] in "\n\r<":
                return None
            index += 2 if body[index] == "\\" else 1
        if index >= len(body):
            return None
        end, index = index, index + 1
    else:
        depth = 0
        while index < len(body):
            character = body[index]
            if character == "\\" and index + 1 < len(body):
                index += 2
                continue
            if character.isspace():
                if depth:
                    return None
                break
            if character == "(":
                depth += 1
            elif character == ")":
                if depth == 0:
                    break
                depth -= 1
            index += 1
        if depth:
            return None
        end = index
    separated = index < len(body) and body[index].isspace()
    while index < len(body) and body[index].isspace():
        index += 1
    if index < len(body) and body[index] == ")":
        return start, end, index + 1
    if not separated or index >= len(body) or body[index] not in "\"'(":
        return None
    closer = ")" if body[index] == "(" else body[index]
    index += 1
    while index < len(body) and body[index] != closer:
        index += 2 if body[index] == "\\" else 1
    index += 1
    while index < len(body) and body[index].isspace():
        index += 1
    if index < len(body) and body[index] == ")":
        return start, end, index + 1
    return None


def _target(raw: str) -> str:
    return html.unescape(_ESCAPE.sub(r"\1", raw))


def _legacy_link_target(body: str, opening: int):
    """Accept old title/filename links with spaces; resolution must verify them."""
    start, index, depth = opening + 1, opening + 1, 0
    while index < len(body):
        if body[index] in "\r\n\"'<>" or body[index : index + 2] == "![":
            return None
        if body[index] == "\\":
            index += 2
            continue
        if body[index] == "(":
            depth += 1
        elif body[index] == ")":
            if not depth:
                end = index
                while start < end and body[start].isspace():
                    start += 1
                while end > start and body[end - 1].isspace():
                    end -= 1
                return start, end, index + 1
            depth -= 1
        index += 1
    return None


def scan_markdown(body: str) -> tuple[list[Reference], list[tuple[int, str]]]:
    """Find inline links/images and Wikilinks; return 1-based syntax issue lines."""
    references, issues = [], []
    mask = _literal_mask(body)
    index = 0
    while index < len(body):
        if mask[index]:
            index += 1
            continue
        math_end = _math_end(body, index, mask)
        if math_end is not None:
            index = math_end
            continue
        if body[index] == "\\":
            index += 2
            continue
        image = body.startswith("![", index)
        opening = index + 1 if image else index
        if body.startswith("[[", opening):
            end = _wiki_end(body, opening)
            if image:
                issues.append(
                    (
                        body.count("\n", 0, index) + 1,
                        "Unsupported image embed; use ![plain alt](path).",
                    )
                )
                index = len(body) if end is None else end + 2
                continue
            if end is not None:
                split = body.find("|", opening + 2, end)
                target_end = end if split < 0 else split
                if split >= 0 and _escaped(body, split):
                    target_end -= 1  # Obsidian table cells escape the alias delimiter.
                start = opening + 2
                while start < target_end and body[start].isspace():
                    start += 1
                while target_end > start and body[target_end - 1].isspace():
                    target_end -= 1
                raw = body[start:target_end]
                label = raw if split < 0 else body[split + 1 : end]
                references.append(
                    Reference("wiki", index, end + 2, start, target_end, label, _target(raw))
                )
                index = end + 2
                continue
        elif opening < len(body) and body[opening] == "[":
            close = _bracket_end(body, opening)
            parsed = None
            inline = close is not None and body[close + 1 : close + 2] == "("
            if inline:
                parsed = _inline_target(body, close + 1)
                if not parsed and not image:
                    parsed = _legacy_link_target(body, close + 1)
            if parsed:
                start, end, reference_end = parsed
                label = body[opening + 1 : close]
                if not image:
                    nested_references, nested_issues = scan_markdown(label)
                    if nested_issues or any(ref.kind == "image" for ref in nested_references):
                        issues.append(
                            (
                                body.count("\n", 0, index) + 1,
                                "Unsupported image or nested syntax in link label; "
                                "use a standalone image.",
                            )
                        )
                references.append(
                    Reference(
                        "image" if image else "link",
                        index,
                        reference_end,
                        start,
                        end,
                        label,
                        _target(body[start:end]),
                    )
                )
                index = reference_end
                continue
            if image:
                issues.append(
                    (
                        body.count("\n", 0, index) + 1,
                        "Malformed or reference-style image; use ![plain alt](path).",
                    )
                )
                index = close + 1 if close is not None else opening + 1
                continue
            if inline:
                issues.append(
                    (body.count("\n", 0, index) + 1, "Malformed inline link destination.")
                )
                index = close + 1
                continue
        index += 1
    return references, issues


def math_issues(body: str) -> list[tuple[int, str]]:
    """Flag Unicode math and image-alt formulas without guessing variable names."""
    mask = _literal_mask(body)
    references, _ = scan_markdown(body)
    issues = []
    for reference in references:
        _mark(mask, reference.target_start, reference.target_end)
        if reference.kind == "image":
            label_mask = _literal_mask(reference.label)
            for index in range(len(reference.label)):
                if not label_mask[index] and not _escaped(reference.label, index):
                    if _math_end(reference.label, index, label_mask) is not None:
                        issues.append(
                            (
                                body.count("\n", 0, reference.start) + 1,
                                "Math in image alt text cannot render; "
                                "move it to a caption paragraph.",
                            )
                        )
                        break
    reported = set()
    for index, character in enumerate(body):
        if mask[index] or character.isascii():
            continue
        if unicodedata.decomposition(character).startswith(("<super>", "<sub>", "<fraction>")):
            line = body.count("\n", 0, index) + 1
            if line not in reported:
                issues.append(
                    (line, "Use LaTeX for Unicode superscripts, subscripts and fractions.")
                )
                reported.add(line)
    return sorted(issues)
