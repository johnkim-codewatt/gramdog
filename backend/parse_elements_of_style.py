#!/usr/bin/env python3
"""
Parse Project Gutenberg pg37134.txt (Strunk, The Elements of Style) into
elements_of_style.md and elements_of_style.json.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "pg37134.txt"
OUT_MD = ROOT / "elements_of_style.md"
OUT_JSON = ROOT / "elements_of_style.json"

CHAPTER_MARKERS = [
    (r"^I\.\s+INTRODUCTORY$", "I", "Introductory"),
    (r"^II\.\s+ELEMENTARY RULES OF USAGE$", "II", "Elementary Rules of Usage"),
    (
        r"^III\.\s+ELEMENTARY PRINCIPLES OF COMPOSITION$",
        "III",
        "Elementary Principles of Composition",
    ),
    (r"^IV\.\s+A FEW MATTERS OF FORM$", "IV", "A Few Matters of Form"),
    (
        r"^V\.\s+WORDS AND EXPRESSIONS COMMONLY MISUSED$",
        "V",
        "Words and Expressions Commonly Misused",
    ),
    (r"^VI\.\s+SPELLING$", "VI", "Spelling"),
    (
        r"^VII\.\s+EXERCISES ON CHAPTERS II AND III$",
        "VII",
        "Exercises on Chapters II and III",
    ),
]


def load_book_lines() -> list[str]:
    raw = SOURCE.read_text(encoding="utf-8", errors="replace").splitlines()
    start = next(
        (i for i, ln in enumerate(raw) if "*** START OF THE PROJECT GUTENBERG" in ln),
        0,
    )
    end = next(
        (
            i
            for i, ln in enumerate(raw)
            if "*** END OF THE PROJECT GUTENBERG EBOOK" in ln
        ),
        len(raw),
    )
    body = raw[start + 1 : end]
    # Drop trailing transcriber errata block inside the ebook
    cut = next(
        (i for i, ln in enumerate(body) if ln.strip().startswith("[ Transcriber's Note:")),
        len(body),
    )
    return body[:cut]


def gutenberg_to_markdown_line(line: str) -> str:
    s = line.rstrip("\n")
    # Bold: =text=
    s = re.sub(r"=([^=]+)=", r"**\1**", s)
    # Italic: _word_ (non-greedy, allow internal apostrophe in rare cases)
    s = re.sub(r"_([^_]+)_", r"*\1*", s)
    return s


def indent_to_blockquote(line: str) -> str:
    """Two-space examples -> markdown blockquote; four spaces -> nested."""
    if not line.strip():
        return ""
    # Measure leading spaces (file uses 2 and 4 for columns)
    m = re.match(r"^( *)(.*)$", line)
    if not m:
        return line
    spaces, rest = m.group(1), m.group(2)
    n = len(spaces)
    if n >= 4:
        level = 2 if n >= 4 else 1
        prefix = "> " * level
        return prefix + rest.rstrip()
    if n >= 2:
        return "> " + rest.rstrip()
    return line.rstrip()


def lines_to_markdown_body(lines: list[str]) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        conv = gutenberg_to_markdown_line(ln)
        stripped = conv.strip()
        if stripped.startswith("="):
            # Should already be converted; if raw slipped through, skip
            out.append(conv.rstrip())
            i += 1
            continue
        if ln.startswith("  ") or (ln.startswith("    ") and ln.strip()):
            block: list[str] = []
            while i < len(lines) and (
                lines[i].startswith("  ") or lines[i].strip() == ""
            ):
                if lines[i].strip() == "":
                    block.append("")
                else:
                    block.append(indent_to_blockquote(gutenberg_to_markdown_line(lines[i])))
                i += 1
            # Collapse multiple blank lines in block
            for b in block:
                if b == "" and out and out[-1] == "":
                    continue
                out.append(b)
            continue
        out.append(conv.rstrip())
        i += 1
    return out


def slugify(s: str, max_len: int = 48) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s[:max_len].rstrip("-")


def summarize_description(text: str, limit: int = 1000) -> str:
    text = re.sub(r"\s+", " ", text.strip())
    if len(text) <= limit:
        return text
    cut = text[: limit - 3]
    sp = cut.rfind(" ")
    if sp > limit // 2:
        cut = cut[:sp]
    return cut + "..."


def extract_checklist(body_text: str) -> list[str]:
    items: list[str] = []
    for m in re.finditer(
        r"(?:^\s*|\n)\(([a-z\d]+)\)\s*([^\n]+)", body_text, re.MULTILINE
    ):
        items.append(f"({m.group(1)}) {m.group(2).strip()}")
    if items:
        return items
    for m in re.finditer(
        r"(?:^\s*|\n)(\d+)\.\s+([A-Z][^\n]{10,120})", body_text, re.MULTILINE
    ):
        items.append(f"{m.group(1)}. {m.group(2).strip()}")
    return items[:12]


def extract_wrong_correct(example_lines: list[str]) -> tuple[str | None, str | None]:
    """First 2-space example line followed (after optional blanks) by 4-space correction."""
    i = 0
    while i < len(example_lines):
        ln = example_lines[i]
        if ln.startswith("  ") and not ln.startswith("    ") and ln.strip():
            cand = ln.strip()
            j = i + 1
            while j < len(example_lines) and not example_lines[j].strip():
                j += 1
            if j < len(example_lines):
                nxt = example_lines[j]
                if nxt.startswith("    ") and nxt.strip():
                    return (
                        re.sub(r"\s+", " ", cand),
                        re.sub(r"\s+", " ", nxt.strip()),
                    )
        i += 1
    return None, None


def prose_only_for_description(body_lines: list[str]) -> str:
    """Drop indented example blocks; keep rule explanation."""
    chunks: list[str] = []
    for ln in body_lines:
        if ln.startswith("  "):
            continue
        t = ln.strip()
        if t:
            chunks.append(t)
    return " ".join(chunks)


def parse_numbered_rule(
    chapter_roman: str,
    category: str,
    rule_num: int,
    title: str,
    body_lines: list[str],
) -> dict[str, Any]:
    body_raw = "\n".join(body_lines)
    wrong, correct = extract_wrong_correct(body_lines)
    desc_src = prose_only_for_description(body_lines)
    if not desc_src:
        desc_src = body_raw
    return {
        "tag_id": f"eos-{chapter_roman}-R{rule_num:02d}",
        "category": category,
        "rule_name": title.strip(),
        "core_formula": title.strip().rstrip("."),
        "checklist": extract_checklist(body_raw),
        "wrong_example": wrong,
        "correct_example": correct,
        "original_description": summarize_description(desc_src),
    }


def parse_chapter_ii_iii(
    lines: list[str], chapter_roman: str, category: str
) -> tuple[list[dict[str, Any]], list[str]]:
    """Returns (json_rules, remaining_lines_not_consumed) — consumes all lines."""
    rules: list[dict[str, Any]] = []
    md_chunks: list[str] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        m = re.match(r"^(\d+)\.\s+(.*)$", line.strip())
        if not m:
            md_chunks.append(gutenberg_to_markdown_line(line))
            i += 1
            continue

        rule_num = int(m.group(1))
        title_parts = [m.group(2).strip()]
        i += 1
        while i < n:
            nxt = lines[i]
            if not nxt.strip():
                break
            if nxt.startswith("  "):
                break
            if re.match(r"^\d+\.\s+", nxt.strip()):
                break
            title_parts.append(nxt.strip())
            i += 1

        title = " ".join(title_parts)

        if i < n and not lines[i].strip():
            i += 1

        body: list[str] = []
        while i < n:
            nxt = lines[i]
            if re.match(r"^\d+\.\s+", nxt.strip()):
                break
            body.append(nxt)
            i += 1

        rules.append(
            parse_numbered_rule(chapter_roman, category, rule_num, title, body)
        )
        md_chunks.append(f"### Rule {rule_num}. {gutenberg_to_markdown_line(title)}")
        md_chunks.append("")
        md_chunks.extend(lines_to_markdown_body(body))
        md_chunks.append("")

    return rules, md_chunks


def parse_chapter_iv(lines: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
    rules: list[dict[str, Any]] = []
    md_out: list[str] = []
    i = 0
    n = len(lines)
    cat = "A Few Matters of Form"

    while i < n:
        ln = lines[i]
        m = re.match(r"^=([^=]+)\.=\s*(.*)$", ln.strip())
        if m:
            topic = m.group(1).strip()
            rest = m.group(2).strip()
            body: list[str] = []
            if rest:
                body.append(rest)
            i += 1
            while i < n:
                nxt = lines[i]
                if nxt.strip().startswith("=") and re.match(
                    r"^=([^=]+)\.=", nxt.strip()
                ):
                    break
                body.append(nxt)
                i += 1
            body_lines = body
            body_text = "\n".join(body_lines)
            w, c = extract_wrong_correct(body_lines)
            desc = prose_only_for_description(body_lines) or body_text
            slug = slugify(topic)
            rules.append(
                {
                    "tag_id": f"eos-IV-{slug}",
                    "category": cat,
                    "rule_name": topic,
                    "core_formula": (rest or topic)[:200],
                    "checklist": extract_checklist(body_text),
                    "wrong_example": w,
                    "correct_example": c,
                    "original_description": summarize_description(desc),
                }
            )
            md_out.append(f"### {topic}")
            md_out.append("")
            md_out.extend(lines_to_markdown_body(body_lines))
            md_out.append("")
            continue
        md_out.append(gutenberg_to_markdown_line(ln))
        i += 1

    return rules, md_out


def parse_chapter_v(lines: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
    rules: list[dict[str, Any]] = []
    md_out: list[str] = []
    i = 0
    n = len(lines)
    cat = "Words and Expressions Commonly Misused"

    while i < n:
        ln = lines[i]
        s = ln.strip()
        if s.startswith("(") and "Some of the forms" in s:
            md_out.append(gutenberg_to_markdown_line(ln))
            i += 1
            continue
        m = re.match(r"^=([^=]+)\.=\s*(.*)$", s)
        if m:
            topic = m.group(1).strip()
            rest = m.group(2).strip()
            body: list[str] = []
            if rest:
                body.append(rest)
            i += 1
            while i < n:
                nxt = lines[i]
                ns = nxt.strip()
                if ns.startswith("=") and re.match(r"^=([^=]+)\.=", ns):
                    break
                body.append(nxt)
                i += 1
            body_lines = body
            body_text = "\n".join(body_lines)
            w, c = extract_wrong_correct(body_lines)
            desc = prose_only_for_description(body_lines) or body_text
            slug = slugify(topic) or "entry"
            rules.append(
                {
                    "tag_id": f"eos-V-{slug}",
                    "category": cat,
                    "rule_name": topic,
                    "core_formula": (rest or topic)[:240],
                    "checklist": extract_checklist(body_text),
                    "wrong_example": w,
                    "correct_example": c,
                    "original_description": summarize_description(desc),
                }
            )
            md_out.append(f"### {topic}")
            md_out.append("")
            md_out.extend(lines_to_markdown_body(body_lines))
            md_out.append("")
            continue
        md_out.append(gutenberg_to_markdown_line(ln))
        i += 1

    return rules, md_out


def parse_chapter_vi(lines: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
    cat = "Spelling"
    md_out: list[str] = []
    words: list[str] = []
    prose_lines: list[str] = []

    for ln in lines:
        m = re.match(r"^  ([a-zA-Z].*)$", ln)
        if m and not ln.startswith("    "):
            w = m.group(1).strip()
            if re.match(r"^[A-Za-z][A-Za-z\-]*$", w):
                words.append(w)
                continue
        prose_lines.append(ln)

    md_out.extend(lines_to_markdown_body(lines))

    intro = " ".join(
        x.strip() for x in prose_lines if x.strip() and not x.startswith("  ")
    )
    rules = [
        {
            "tag_id": "eos-VI-spelling",
            "category": cat,
            "rule_name": "Spelling and words often misspelled",
            "core_formula": "Follow generally agreed spelling; consult the book's misspelling list and hyphenation notes.",
            "checklist": [
                "Double a single consonant after a stressed short vowel before -ed/-ing (with noted exceptions).",
                "Write to-day, to-night, to-morrow hyphenated (not together).",
                "Write any one, every one, some one, some time as two words (except some time = formerly).",
            ],
            "wrong_example": None,
            "correct_example": None,
            "original_description": summarize_description(intro),
        }
    ]
    if words:
        rules[0]["checklist"].append(
            f"Review commonly misspelled words ({len(words)} listed in the source)."
        )
        rules[0]["wrong_example"] = None
        rules[0]["correct_example"] = None
    return rules, md_out


def split_into_chapters(
    lines: list[str],
) -> tuple[list[str], list[tuple[str, str, str, list[str]]]]:
    """Preamble lines before I., then (roman, title, title, chapter_lines)."""
    indexed: list[tuple[int, str, str, str]] = []
    for pattern, roman, title in CHAPTER_MARKERS:
        rx = re.compile(pattern, re.MULTILINE)
        for i, ln in enumerate(lines):
            if rx.match(ln.strip()):
                indexed.append((i, roman, title, pattern))
                break

    indexed.sort(key=lambda x: x[0])
    preamble = lines[: indexed[0][0]] if indexed else lines
    chapters: list[tuple[str, str, str, list[str]]] = []
    for j, (pos, roman, title, _) in enumerate(indexed):
        end = indexed[j + 1][0] if j + 1 < len(indexed) else len(lines)
        chapters.append((roman, title, title, lines[pos + 1 : end]))
    return preamble, chapters


def main() -> None:
    lines = load_book_lines()
    preamble, chapters = split_into_chapters(lines)

    parts: list[str] = [
        "# The Elements of Style",
        "",
        "*William Strunk, Jr.*",
        "",
        "Source: Project Gutenberg eBook #37134 (parsed from `pg37134.txt`).",
        "",
        "---",
        "",
    ]
    json_rules: list[dict[str, Any]] = []

    if preamble:
        parts.append("## Title page and contents")
        parts.append("")
        parts.extend(lines_to_markdown_body(preamble))
        parts.append("")

    for roman, _short, category, ch_lines in chapters:
        parts.append(f"## {roman}. {category.upper()}")
        parts.append("")

        if roman in ("II", "III"):
            jr, md_body = parse_chapter_ii_iii(ch_lines, roman, category)
            json_rules.extend(jr)
            parts.extend(md_body)
        elif roman == "IV":
            jr, md_body = parse_chapter_iv(ch_lines)
            json_rules.extend(jr)
            parts.extend(md_body)
        elif roman == "V":
            jr, md_body = parse_chapter_v(ch_lines)
            json_rules.extend(jr)
            parts.extend(md_body)
        elif roman == "VI":
            jr, md_body = parse_chapter_vi(ch_lines)
            json_rules.extend(jr)
            parts.extend(md_body)
        else:
            parts.extend(lines_to_markdown_body(ch_lines))
            parts.append("")

    OUT_MD.write_text("\n".join(parts) + "\n", encoding="utf-8")
    OUT_JSON.write_text(
        json.dumps(json_rules, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUT_MD} ({len(parts)} lines)")
    print(f"Wrote {OUT_JSON} ({len(json_rules)} rules)")


if __name__ == "__main__":
    main()
