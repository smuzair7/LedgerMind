"""Docling wrapper.

Docling is loaded lazily — its model load adds ~3-5s to the first call. The
worker process invokes this once per ingestion job.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)

_converter = None


def _get_converter():  # type: ignore[no-untyped-def]
    """Lazy import + singleton. Docling pulls in heavy deps; load on first use."""
    global _converter
    if _converter is None:
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption

        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True
        pipeline_options.do_table_structure = True
        pipeline_options.table_structure_options.do_cell_matching = True

        _converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
            }
        )
    return _converter


@dataclass(slots=True)
class ParsedTable:
    table_id: str
    page: int
    bbox: tuple[float, float, float, float] | None
    markdown: str
    cells: list[list[str]] = field(default_factory=list)  # row-major
    section_path: tuple[str, ...] = ()


@dataclass(slots=True)
class ParsedSection:
    section_path: tuple[str, ...]
    page: int
    text: str  # cleaned plain text


@dataclass(slots=True)
class ParsedDocument:
    sections: list[ParsedSection]
    tables: list[ParsedTable]
    page_count: int


def parse_pdf(path: Path | str) -> ParsedDocument:
    """Convert a PDF into typed sections + tables. Heavy: avoid in hot paths."""
    converter = _get_converter()
    result = converter.convert(str(path))
    doc = result.document

    sections: list[ParsedSection] = []
    tables: list[ParsedTable] = []

    # Walk the structured doc. Docling's iterators surface headings, paragraphs,
    # and tables with provenance (page_no + bbox). The exact API surface shifts
    # between minor versions; we fall back to plain markdown export if the
    # structured walk fails.
    try:
        current_section: tuple[str, ...] = ()
        last_section_page = 1
        section_buffer: list[str] = []

        for item, _level in doc.iterate_items():
            kind = getattr(item, "label", None) or item.__class__.__name__.lower()
            page_no = _first_page(item) or last_section_page

            if kind in {"section_header", "heading"}:
                _flush_section(sections, current_section, last_section_page, section_buffer)
                title = (getattr(item, "text", None) or "").strip()
                if title:
                    current_section = current_section + (title,) if _level == 0 else (title,)
                last_section_page = page_no
            elif kind in {"paragraph", "text", "list_item"}:
                t = (getattr(item, "text", None) or "").strip()
                if t:
                    section_buffer.append(t)
                    last_section_page = page_no
            elif kind == "table":
                tbl = _table_to_parsed(item, page_no, current_section)
                if tbl:
                    tables.append(tbl)

        _flush_section(sections, current_section, last_section_page, section_buffer)
    except Exception as e:  # noqa: BLE001
        log.warning("docling structured walk failed, falling back to markdown export: %s", e)
        sections = [ParsedSection(section_path=(), page=1, text=doc.export_to_markdown())]

    page_count = getattr(doc, "num_pages", 0) or _estimate_pages(sections, tables)
    return ParsedDocument(sections=sections, tables=tables, page_count=page_count)


def _flush_section(
    out: list[ParsedSection],
    path: tuple[str, ...],
    page: int,
    buffer: list[str],
) -> None:
    text = "\n\n".join(buffer).strip()
    buffer.clear()
    if not text:
        return
    out.append(ParsedSection(section_path=path, page=page, text=text))


def _first_page(item: object) -> int | None:
    prov = getattr(item, "prov", None)
    if not prov:
        return None
    try:
        return int(prov[0].page_no)
    except (AttributeError, IndexError, TypeError):
        return None


def _table_to_parsed(item: object, page: int, section_path: tuple[str, ...]) -> ParsedTable | None:
    table_id = getattr(item, "self_ref", None) or f"table-{id(item):x}"
    bbox = _first_bbox(item)
    try:
        markdown = item.export_to_markdown()  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        markdown = ""
    try:
        # Docling's TableData has `.table_cells` with row/col indices.
        data = getattr(item, "data", None)
        cells_raw = getattr(data, "table_cells", None) if data else None
        if cells_raw:
            rows = max((c.start_row_offset_idx for c in cells_raw), default=-1) + 1
            cols = max((c.start_col_offset_idx for c in cells_raw), default=-1) + 1
            grid: list[list[str]] = [["" for _ in range(cols)] for _ in range(rows)]
            for c in cells_raw:
                grid[c.start_row_offset_idx][c.start_col_offset_idx] = (c.text or "").strip()
        else:
            grid = []
    except Exception:  # noqa: BLE001
        grid = []

    if not markdown and not grid:
        return None
    return ParsedTable(
        table_id=str(table_id),
        page=page,
        bbox=bbox,
        markdown=markdown or "",
        cells=grid,
        section_path=section_path,
    )


def _first_bbox(item: object) -> tuple[float, float, float, float] | None:
    prov = getattr(item, "prov", None)
    if not prov:
        return None
    try:
        b = prov[0].bbox
        return (float(b.l), float(b.t), float(b.r), float(b.b))
    except (AttributeError, IndexError, TypeError):
        return None


def _estimate_pages(sections: list[ParsedSection], tables: list[ParsedTable]) -> int:
    pages = {s.page for s in sections} | {t.page for t in tables}
    return max(pages) if pages else 1
