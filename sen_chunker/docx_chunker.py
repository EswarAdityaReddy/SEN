"""
DOCX document chunking for SEN Word document files.
Extracts paragraphs and tables from .docx files, groups them into
semantically sensible chunks by character budget, and creates RAGChunk
objects with full section/page metadata.
"""

import os
import warnings
from typing import List, Dict, Any

try:
    import docx as python_docx
except ImportError:
    python_docx = None  # handled gracefully below

from .schema import RAGChunk

warnings.filterwarnings('ignore')


def estimate_tokens(text: str) -> int:
    """Rough estimate of token count (1 token ~= 4 characters or ~0.75 words)."""
    if not text:
        return 0
    words = text.split()
    return int(len(words) * 1.3)


def _table_to_markdown(table) -> str:
    """Convert a python-docx Table object to a markdown table string."""
    rows = []
    for i, row in enumerate(table.rows):
        cells = [cell.text.strip().replace('\n', ' ') for cell in row.cells]
        row_str = '| ' + ' | '.join(cells) + ' |'
        rows.append(row_str)
        if i == 0:
            sep = '| ' + ' | '.join(['---'] * len(cells)) + ' |'
            rows.append(sep)
    return '\n'.join(rows)


def chunk_docx_file(
    file_path: str,
    meta_info: Dict[str, Any],
    max_chars_per_chunk: int = 3500,
    max_chunks_per_file: int = 500,
) -> List[RAGChunk]:
    """
    Extracts paragraphs and tables from a .docx file and groups them into
    RAGChunk objects bounded by max_chars_per_chunk. Tables are rendered
    as Markdown. Headings are used as section titles.

    Args:
        file_path: Absolute path to the .docx file.
        meta_info: Dict with file/document lineage metadata.
        max_chars_per_chunk: Soft character cap per chunk (default 3500).
        max_chunks_per_file: Hard cap on number of chunks per file.

    Returns:
        List of RAGChunk objects.
    """
    if python_docx is None:
        print("python-docx is not installed. Cannot process .docx files.")
        return []

    if not os.path.exists(file_path):
        return []

    try:
        doc = python_docx.Document(file_path)
    except Exception as e:
        print(f"Failed to open DOCX file {file_path}: {e}")
        return []

    filename = meta_info.get('filename', os.path.basename(file_path))

    # Collect all content blocks: (type, text)
    # type is 'heading', 'paragraph', or 'table'
    blocks: List[tuple] = []
    for element in doc.element.body:
        tag = element.tag.split('}')[-1]  # strip namespace

        if tag == 'p':
            # Re-wrap as docx paragraph to use style info
            para = python_docx.text.paragraph.Paragraph(element, doc)
            text = para.text.strip()
            if not text:
                continue
            style_name = (para.style.name or '').lower()
            if 'heading' in style_name:
                blocks.append(('heading', text))
            else:
                blocks.append(('paragraph', text))

        elif tag == 'tbl':
            table = python_docx.table.Table(element, doc)
            md = _table_to_markdown(table)
            if md.strip():
                blocks.append(('table', md))

    if not blocks:
        return []

    chunks: List[RAGChunk] = []
    current_section = ''
    current_lines: List[str] = []
    current_chars = 0
    chunk_index = 0

    def _flush_chunk():
        nonlocal current_lines, current_chars, chunk_index
        if not current_lines or chunk_index >= max_chunks_per_file:
            return
        body_text = '\n\n'.join(current_lines)
        header_prefix = (
            f"--- [DOCUMENT: {filename}] [YEAR: {meta_info.get('year')}] "
            f"[SECTION: {current_section or 'General'}] [CHUNK: {chunk_index + 1}] ---\n\n"
        )
        full_text = header_prefix + body_text

        chunk_id = f"CHUNK_DOCX_{meta_info.get('file_id', 'UNKNOWN')}_{chunk_index + 1}"
        chunk = RAGChunk(
            chunk_id=chunk_id,
            year=int(meta_info.get('year', 0)),
            academic_year=str(meta_info.get('academic_year', '') or ''),
            document_id=str(meta_info.get('document_id', '')),
            file_id=str(meta_info.get('file_id', '')),
            filename=str(filename),
            relative_path=str(meta_info.get('relative_path', '')),
            source_url=meta_info.get('source_url'),
            publication_url=meta_info.get('publication_url'),
            file_type='.docx',
            content_type='text_doc',
            section_title=current_section or None,
            chunk_index=chunk_index,
            char_count=len(full_text),
            token_count_approx=estimate_tokens(full_text),
            text=full_text,
            extra_metadata={
                'source_format': 'docx',
            }
        )
        chunks.append(chunk)
        chunk_index += 1
        current_lines = []
        current_chars = 0

    for block_type, text in blocks:
        if block_type == 'heading':
            # Flush what we have before starting a new section
            _flush_chunk()
            current_section = text
            # Add the heading to the new chunk as context
            current_lines.append(f'## {text}')
            current_chars += len(text) + 4
        else:
            # Would adding this block exceed the budget?
            added_chars = len(text) + 2  # +2 for double newline separator
            if current_chars + added_chars > max_chars_per_chunk and current_lines:
                _flush_chunk()
                # Carry the section heading forward into the new chunk
                if current_section:
                    current_lines.append(f'## {current_section} (continued)')
                    current_chars += len(current_section) + 15

            current_lines.append(text)
            current_chars += added_chars

    # Flush any remaining content
    _flush_chunk()

    return chunks
