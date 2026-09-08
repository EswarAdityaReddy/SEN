"""
Schema definition for SEN RAG document chunks.
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List

@dataclass
class RAGChunk:
    chunk_id: str
    year: int
    academic_year: Optional[str]
    document_id: str
    file_id: str
    filename: str
    relative_path: str
    source_url: Optional[str]
    publication_url: Optional[str]
    file_type: str
    content_type: str  # 'pdf_page', 'excel_sheet', 'csv_dataset', 'text_doc'
    page_number: Optional[int] = None
    sheet_name: Optional[str] = None
    row_range: Optional[str] = None
    section_title: Optional[str] = None
    chunk_index: int = 0
    total_chunks_in_file: int = 1
    char_count: int = 0
    token_count_approx: int = 0
    text: str = ""
    extra_metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if d['extra_metadata'] is None:
            d['extra_metadata'] = {}
        for k, v in list(d.items()):
            if isinstance(v, float) and (v != v or str(v).lower() == 'nan'):
                d[k] = None
            elif isinstance(v, str) and v.lower() == 'nan':
                d[k] = None
        return d
