"""
Page-wise PDF chunking for SEN documents.
Extracts text page by page, maintaining strict page number lineage and page metadata.
"""

import os
import re
from typing import List, Dict, Any, Optional
import fitz  # PyMuPDF
from .schema import RAGChunk

def estimate_tokens(text: str) -> int:
    """Rough estimate of token count (1 token ~= 4 characters or ~0.75 words)."""
    if not text:
        return 0
    words = text.split()
    return int(len(words) * 1.3)

def split_text_with_overlap(text: str, max_chars: int = 3000, overlap: int = 400) -> List[str]:
    """Splits long text into overlapping chunks along paragraph/sentence boundaries."""
    text = text.strip()
    if len(text) <= max_chars:
        return [text]
    
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = []
    current_len = 0
    
    for p in paragraphs:
        p_len = len(p)
        if current_len + p_len > max_chars and current_chunk:
            combined = "\n\n".join(current_chunk)
            chunks.append(combined)
            # Retain overlap from end of current_chunk
            overlap_text = combined[-overlap:] if len(combined) > overlap else combined
            current_chunk = [overlap_text, p]
            current_len = len(overlap_text) + p_len
        else:
            current_chunk.append(p)
            current_len += p_len + 2
            
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
        
    return chunks

def chunk_pdf_file(
    file_path: str,
    meta_info: Dict[str, Any],
    max_chars_per_chunk: int = 3000,
    overlap: int = 400
) -> List[RAGChunk]:
    """
    Extracts text page-by-page from a PDF file.
    Creates RAGChunk objects tagged with page_number and PDF document metadata.
    """
    if not os.path.exists(file_path):
        return []
    
    chunks: List[RAGChunk] = []
    
    try:
        doc = fitz.open(file_path)
        total_pages = len(doc)
        
        for page_idx in range(total_pages):
            page_num = page_idx + 1
            page = doc[page_idx]
            raw_text = page.get_text("text") or ""
            
            # Clean text whitespace
            cleaned_lines = [line.rstrip() for line in raw_text.splitlines()]
            # Collapse multiple empty lines
            cleaned_text = re.sub(r'\n{3,}', '\n\n', "\n".join(cleaned_lines)).strip()
            
            if not cleaned_text or len(cleaned_text) < 15:
                # Skip blank/nearly empty pages (e.g. cover page background or empty divider)
                continue
            
            # Split page text if it exceeds max_chars_per_chunk
            sub_texts = split_text_with_overlap(cleaned_text, max_chars=max_chars_per_chunk, overlap=overlap)
            num_sub = len(sub_texts)
            
            for sub_idx, sub_text in enumerate(sub_texts):
                sub_part_suffix = f" (Part {sub_idx + 1}/{num_sub})" if num_sub > 1 else ""
                
                header_prefix = f"--- [DOCUMENT: {meta_info.get('filename')}] [YEAR: {meta_info.get('year')}] [PAGE {page_num}{sub_part_suffix}] ---\n\n"
                full_chunk_text = header_prefix + sub_text
                
                chunk_id = f"CHUNK_PDF_{meta_info.get('file_id', 'UNKNOWN')}_P{page_num}_{sub_idx+1}"
                
                chunk = RAGChunk(
                    chunk_id=chunk_id,
                    year=int(meta_info.get('year', 0)),
                    academic_year=str(meta_info.get('academic_year', '') or ''),
                    document_id=str(meta_info.get('document_id', '')),
                    file_id=str(meta_info.get('file_id', '')),
                    filename=str(meta_info.get('filename', '')),
                    relative_path=str(meta_info.get('relative_path', '')),
                    source_url=meta_info.get('source_url'),
                    publication_url=meta_info.get('publication_url'),
                    file_type='.pdf',
                    content_type='pdf_page',
                    page_number=page_num,
                    chunk_index=len(chunks),
                    char_count=len(full_chunk_text),
                    token_count_approx=estimate_tokens(full_chunk_text),
                    text=full_chunk_text,
                    extra_metadata={
                        'sub_part': sub_idx + 1,
                        'total_sub_parts': num_sub,
                        'total_pdf_pages': total_pages
                    }
                )
                chunks.append(chunk)
                
        doc.close()
    except Exception as e:
        print(f"Error processing PDF {file_path}: {e}")
        
    return chunks
