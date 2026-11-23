"""Load policy documents (.txt / .md / .pdf) into section-level chunks with metadata.

Document layout (plain text, or the text layer of a PDF):

    TITLE: Attendance Requirements Policy
    DOC_ID: ATT-2023-01
    ISSUED: 2023-07-10
    CATEGORY: attendance

    SECTION 3 [facet=value; updates=ATT-2023-01#3]: Heading
    body text...

`updates=DOC#SECTION` declares that this section supersedes an earlier section.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .textutils import tokenize

_SECTION_RE = re.compile(r"^SECTION\s+(\S+?)\s*(?:\[([^\]]*)\])?\s*:\s*(.+)$", re.MULTILINE)


@dataclass
class Chunk:
    doc_id: str
    title: str
    issued: date
    category: str
    section: str
    heading: str
    body: str
    facets: dict = field(default_factory=dict)
    updates: list = field(default_factory=list)  # refs like "ATT-2023-01#3"
    page: int | None = None
    source_file: str = ""

    @property
    def id(self) -> str:
        return f"{self.doc_id}#{self.section}"

    @property
    def issued_str(self) -> str:
        return f"{self.issued.day} {self.issued.strftime('%b %Y')}"

    def citation(self) -> str:
        loc = f"Section {self.section}" + (f", p. {self.page}" if self.page else "")
        return f"{self.title} ({self.doc_id}, issued {self.issued_str}), {loc}"

    def tokens(self) -> list[str]:
        # heading counts double: titles/headings are strong retrieval signals
        return tokenize(self.heading) * 2 + tokenize(self.title) + tokenize(self.body)


def _read_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader

        pages = [(p.extract_text() or "") for p in PdfReader(str(path)).pages]
        return "\n\f\n".join(pages)  # form feed marks page breaks
    return path.read_text(encoding="utf-8")


def _parse_tags(raw: str | None) -> tuple[dict, list]:
    facets, updates = {}, []
    for part in filter(None, (raw or "").split(";")):
        key, _, val = part.partition("=")
        key, val = key.strip(), val.strip()
        if key == "updates":
            updates = [v.strip() for v in val.split("|") if v.strip()]
        elif key:
            facets[key] = val
    return facets, updates


def parse_document(text: str, source_file: str = "") -> list[Chunk]:
    header: dict[str, str] = {}
    first_section = _SECTION_RE.search(text)
    head_text = text[: first_section.start()] if first_section else text
    for line in head_text.splitlines():
        key, sep, val = line.partition(":")
        if sep and key.strip().isupper():
            header[key.strip()] = val.strip()
    missing = {"TITLE", "DOC_ID", "ISSUED", "CATEGORY"} - header.keys()
    if missing:
        raise ValueError(f"{source_file}: missing header fields {sorted(missing)}")

    chunks: list[Chunk] = []
    matches = list(_SECTION_RE.finditer(text))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.end():end].replace("\f", " ").strip()
        facets, updates = _parse_tags(m.group(2))
        page = text.count("\f", 0, m.start()) + 1 if "\f" in text else None
        chunks.append(
            Chunk(
                doc_id=header["DOC_ID"],
                title=header["TITLE"],
                issued=date.fromisoformat(header["ISSUED"]),
                category=header["CATEGORY"],
                section=m.group(1),
                heading=m.group(3).strip(),
                body=re.sub(r"[ \t]+\n", "\n", body),
                facets=facets,
                updates=updates,
                page=page,
                source_file=source_file,
            )
        )
    return chunks


def load_corpus(policy_dir: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    files = sorted(p for p in Path(policy_dir).iterdir() if p.suffix.lower() in {".txt", ".md", ".pdf"})
    if not files:
        raise FileNotFoundError(f"No policy documents found in {policy_dir}")
    for path in files:
        chunks.extend(parse_document(_read_text(path), path.name))
    return chunks
