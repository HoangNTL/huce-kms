"""PDF table detection and clean Markdown table extraction utilities."""

import logging
import re

import pymupdf

from api.services.rag.patterns import (
    BARE_PAGE_NUMBER_RE,
    BULLET_OR_ITEM_RE,
    FORM_BLANK_RE,
    REPEATED_COMMA_RE,
    sanitize_pdf_symbols,
)

logger = logging.getLogger("huce_kms.rag.pdf_tables")

_ALNUM_RE = re.compile(r"[A-Za-zÀ-ỹ0-9]")

# Tuple layout: (baseline_y, x0, x1, font_size, char_or_text, mid_x, mid_y)
_Glyph = tuple[float, float, float, float, str, float, float]


def _bbox_overlaps(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    """Return True if two (x0, y0, x1, y1) bounding boxes intersect."""
    return not (a[0] > b[2] or a[2] < b[0] or a[1] > b[3] or a[3] < b[1])


def _collect_glyphs(
    raw_blocks: list[dict], bbox: tuple[float, float, float, float]
) -> list[_Glyph]:
    """Collect glyph tuples from rawdict blocks whose midpoints lie inside bbox."""
    cx0, cy0, cx1, cy1 = bbox
    glyphs: list[_Glyph] = []
    for block in raw_blocks:
        if block.get("type") != 0 or not _bbox_overlaps(block.get("bbox", (0, 0, 0, 0)), bbox):
            continue
        for line in block.get("lines", []):
            if not _bbox_overlaps(line.get("bbox", (0, 0, 0, 0)), bbox):
                continue
            for span in line.get("spans", []):
                sb = span.get("bbox", (0, 0, 0, 0))
                if not _bbox_overlaps(sb, bbox):
                    continue
                font_size = float(span.get("size") or 10.0)
                chars = span.get("chars")
                if chars:
                    for ch in chars:
                        cb = ch["bbox"]
                        mx, my = (cb[0] + cb[2]) * 0.5, (cb[1] + cb[3]) * 0.5
                        if cx0 <= mx <= cx1 and cy0 <= my <= cy1:
                            origin = ch.get("origin")
                            baseline_y = float(origin[1]) if origin else my
                            glyphs.append((baseline_y, float(cb[0]), float(cb[2]), font_size, ch["c"], mx, my))
                elif span_txt := span.get("text", ""):
                    mx, my = (sb[0] + sb[2]) * 0.5, (sb[1] + sb[3]) * 0.5
                    if cx0 <= mx <= cx1 and cy0 <= my <= cy1:
                        glyphs.append((my, float(sb[0]), float(sb[2]), font_size, span_txt, mx, my))
    return glyphs


def _format_cell_glyphs(glyphs: list[_Glyph]) -> str:
    """Reconstruct readable single-line Markdown cell text from visual glyph tuples."""
    if not glyphs:
        return ""

    glyphs.sort(key=lambda g: (g[0], g[1]))
    visual_lines: list[list[_Glyph]] = [[glyphs[0]]]
    line_y, line_size = glyphs[0][0], glyphs[0][3]
    for g in glyphs[1:]:
        if abs(g[0] - line_y) <= max(2.0, 0.35 * line_size):
            visual_lines[-1].append(g)
        else:
            visual_lines.append([g])
            line_y, line_size = g[0], g[3]

    line_strings: list[str] = []
    for vline in visual_lines:
        vline.sort(key=lambda g: g[1])
        parts: list[str] = []
        prev_x1: float | None = None
        prev_size, prev_char, had_space = 10.0, "", False
        for _, gx0, gx1, gsize, ch, _, _ in vline:
            if ch.isspace():
                had_space = True
                continue
            if prev_x1 is not None:
                gap = gx0 - prev_x1
                ref = max(4.0, (prev_size + gsize) * 0.5)
                if (had_space and (gap > ref * 0.12 or prev_char in ",;:.)]")) or gap > ref * 0.22:
                    parts.append(" ")
            parts.append(ch)
            prev_x1, prev_size, prev_char, had_space = gx1, gsize, ch[-1], False
        if line_str := re.sub(r"[ \t]+", " ", "".join(parts)).strip():
            line_strings.append(line_str)

    if not line_strings:
        return ""

    # Join distinct sub-items cleanly without HTML <br> tags
    merged = [line_strings[0]]
    for curr in line_strings[1:]:
        prev = merged[-1]
        is_new_item = bool(BULLET_OR_ITEM_RE.match(curr))
        prev_ended = prev[-1] in ".;:!?" and (curr[0].isupper() or is_new_item)
        if is_new_item and not prev_ended and prev[-1] not in ".;:!?":
            merged.append(f"; {curr}")
        else:
            merged.append(f" {curr}")

    result = sanitize_pdf_symbols("".join(merged).strip())
    result = FORM_BLANK_RE.sub("...", result)
    result = REPEATED_COMMA_RE.sub(", ", result)
    result = re.sub(r"[ \t]+", " ", result).strip()
    return result.replace("|", "\\|")


def extract_cell_text(
    raw_blocks: list[dict], cell_bbox: tuple[float, float, float, float]
) -> str:
    """Extract cell text using visual baseline grouping and inter-glyph x-gap reconstruction."""
    return _format_cell_glyphs(_collect_glyphs(raw_blocks, cell_bbox))


def _assign_glyphs_to_grid(
    tab: pymupdf.table.Table, raw_blocks: list[dict]
) -> list[list[list[_Glyph]]]:
    """Assign each glyph in tab.bbox to at most one cell, preventing merged-cell duplication."""
    num_rows, num_cols = tab.row_count, tab.col_count
    grid: list[list[list[_Glyph]]] = [[[] for _ in range(num_cols)] for _ in range(num_rows)]

    # Deduplicate identical cell bboxes returned by PyMuPDF for horizontally/vertically merged slots
    seen_bboxes: set[tuple[float, float, float, float]] = set()
    unique_cells: list[tuple[int, int, tuple[float, float, float, float], float]] = []
    cell_grid: list[list[tuple[float, float, float, float] | None]] = [
        [None for _ in range(num_cols)] for _ in range(num_rows)
    ]
    col_candidates: list[list[tuple[float, float]]] = [[] for _ in range(num_cols)]

    for r, row in enumerate(tab.rows):
        for c, cell in enumerate(row.cells):
            if cell is None or c >= num_cols:
                continue
            sig = tuple(round(v, 1) for v in cell)
            if sig in seen_bboxes:
                continue
            seen_bboxes.add(sig)
            bbox = (float(cell[0]), float(cell[1]), float(cell[2]), float(cell[3]))
            area = max(0.0, bbox[2] - bbox[0]) * max(0.0, bbox[3] - bbox[1])
            unique_cells.append((r, c, bbox, area))
            cell_grid[r][c] = bbox
            if bbox[2] - bbox[0] >= 4.0:
                col_candidates[c].append((bbox[0], bbox[2]))

    # Narrowest non-degenerate cell per column defines true single-column x-bounds
    col_bounds: list[tuple[float, float] | None] = [
        min(cands, key=lambda pair: pair[1] - pair[0]) if cands else None
        for cands in col_candidates
    ]
    row_ybands = [(float(row.bbox[1]), float(row.bbox[3])) for row in tab.rows]

    for g in _collect_glyphs(raw_blocks, tab.bbox):
        mx, my = g[5], g[6]
        best: tuple[int, int, float] | None = None
        for r, c, bbox, area in unique_cells:
            if bbox[0] <= mx <= bbox[2] and bbox[1] <= my <= bbox[3]:
                if best is None or area < best[2]:
                    best = (r, c, area)
        if best is None:
            continue

        target_r, target_c, _ = best
        # Recover orphaned glyphs when a tall merged cell in another column spills horizontally across None slots
        owner_bounds = col_bounds[target_c]
        if owner_bounds and not (owner_bounds[0] - 2.0 <= mx <= owner_bounds[1] + 2.0):
            for c, bounds in enumerate(col_bounds):
                if c != target_c and bounds and bounds[0] <= mx <= bounds[1]:
                    for r, (ry0, ry1) in enumerate(row_ybands):
                        if r != target_r and ry0 <= my <= ry1 and cell_grid[r][c] is None:
                            target_r, target_c = r, c
                            break
                    break

        grid[target_r][target_c].append(g)

    return grid


def table_to_clean_markdown(
    tab: pymupdf.table.Table, raw_blocks: list[dict], strict_bordered: bool = True
) -> str:
    """Convert a PyMuPDF Table into clean Markdown without ColN placeholders or merged-cell duplication."""
    if tab.col_count < 2 or tab.row_count < 1 or (not strict_bordered and tab.row_count < 3):
        return ""

    glyph_grid = _assign_glyphs_to_grid(tab, raw_blocks)
    rows_text = [
        [_format_cell_glyphs(cell_glyphs) for cell_glyphs in row_glyphs]
        for row_glyphs in glyph_grid
    ]
    rows_text = [r for r in rows_text if any(_ALNUM_RE.search(cell) for cell in r)]
    if not rows_text:
        return ""

    if len(rows_text) == 1:
        if not strict_bordered or sum(1 for c in rows_text[0] if _ALNUM_RE.search(c)) < 2:
            return ""
        return "| " + " | ".join(rows_text[0]) + " |\n| " + " | ".join("---" for _ in rows_text[0]) + " |"

    if not strict_bordered and len(rows_text) < 3:
        return ""

    num_cols = len(rows_text[0])
    keep_cols = [c for c in range(num_cols) if any(r[c].strip() for r in rows_text if c < len(r))]
    if len(keep_cols) < 2:
        return ""

    normalized = [[r[c] if c < len(r) else "" for c in keep_cols] for r in rows_text]
    if not strict_bordered:
        filled = sum(1 for r in normalized for c in r if c.strip())
        if (filled / (len(normalized) * len(keep_cols))) < 0.6:
            return ""

    md_rows = ["| " + " | ".join(normalized[0]) + " |", "| " + " | ".join("---" for _ in keep_cols) + " |"]
    md_rows.extend("| " + " | ".join(row) + " |" for row in normalized[1:])
    return "\n".join(md_rows)


def extract_page_text_with_tables(page: pymupdf.Page) -> str:
    """Extract PDF page text with bordered Markdown tables in top-to-bottom reading order."""
    page_height = float(page.rect.height or 0.0)
    strict_bordered = True
    try:
        try:
            tabs = page.find_tables(strategy="lines_strict", use_layout=False)
            if not tabs or not tabs.tables:
                strict_bordered = False
                tabs = page.find_tables(use_layout=False)
        except TypeError:
            tabs = page.find_tables(strategy="lines_strict")
            if not tabs or not tabs.tables:
                strict_bordered = False
                tabs = page.find_tables()
    except Exception as e:
        logger.warning("Table detection failed on page %d: %s", page.number + 1, e)
        tabs = None

    raw_blocks: list[dict] = []
    if tabs and tabs.tables:
        try:
            raw_blocks = page.get_text("rawdict", flags=pymupdf.TEXTFLAGS_TEXT).get("blocks", [])
        except Exception as e:
            logger.warning("rawdict extraction failed on page %d: %s", page.number + 1, e)

    page_elements: list[tuple[float, float, str]] = []
    accepted_rects: list[pymupdf.Rect] = []
    if tabs and tabs.tables and raw_blocks:
        for tab in tabs.tables:
            try:
                if md := table_to_clean_markdown(tab, raw_blocks, strict_bordered=strict_bordered).strip():
                    accepted_rects.append(pymupdf.Rect(tab.bbox))
                    page_elements.append((tab.bbox[1], tab.bbox[0], md))
            except Exception as e:
                logger.warning("Failed to convert table to markdown on page %d: %s", page.number + 1, e)

    try:
        for b in page.get_text("blocks"):
            if b[6] != 0 or not (block_text := b[4].strip()):
                continue
            rect = pymupdf.Rect(b[:4])
            if page_height and BARE_PAGE_NUMBER_RE.match(block_text) and (
                rect.y1 <= page_height * 0.08 or rect.y0 >= page_height * 0.92
            ):
                continue
            if any(
                tr.intersects(rect) and rect.get_area() > 0 and ((tr & rect).get_area() / rect.get_area()) > 0.3
                for tr in accepted_rects
            ):
                continue
            page_elements.append((rect.y0, rect.x0, block_text))
    except Exception as e:
        logger.warning("Block extraction failed on page %d: %s", page.number + 1, e)

    page_elements.sort(key=lambda item: (round(item[0], 1), item[1]))
    return "\n\n".join(item[2] for item in page_elements).strip() or page.get_text("text").strip()
