"""
Text document chunking for SEN metadata notes, text releases, and plain text files.
Splits text along paragraph/sentence boundaries with configurable overlap,
and creates RAGChunk objects with document metadata lineage.
"""

import os
import re
from typing import List, Dict, Any, Optional
from .schema import RAGChunk

def estimate_tokens(text: str) -> int:
    """Rough estimate of token count (1 token ~= 4 characters or ~0.75 words)."""
    if not text:
        return 0
    words = text.split()
    return int(len(words) * 1.3)

def split_text_with_overlap(text: str, max_chars: int = 2500, overlap: int = 300) -> List[str]:
    """Splits long text into overlapping chunks along paragraph boundaries."""
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []
    
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = []
    current_len = 0
    
    for p in paragraphs:
        p_len = len(p)
        if current_len + p_len > max_chars and current_chunk:
            combined = "\n\n".join(current_chunk)
            chunks.append(combined)
            overlap_text = combined[-overlap:] if len(combined) > overlap else combined
            current_chunk = [overlap_text, p]
            current_len = len(overlap_text) + p_len
        else:
            current_chunk.append(p)
            current_len += p_len + 2
            
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
        
    return chunks

def chunk_text_file(
    file_path: str,
    meta_info: Dict[str, Any],
    max_chars: int = 2500,
    overlap: int = 300
) -> List[RAGChunk]:
    """
    Extracts text from plain text files (.txt).
    Creates RAGChunk objects tagged with document metadata.
    """
    if not os.path.exists(file_path):
        return []
    
    filename = meta_info.get('filename', os.path.basename(file_path))
    file_ext = os.path.splitext(file_path)[1].lower()
    
    raw_text = ""
    for encoding in ['utf-8', 'latin1', 'cp1252', 'iso-8859-1']:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                raw_text = f.read()
            break
        except Exception:
            continue
            
    cleaned_lines = [line.rstrip() for line in raw_text.splitlines()]
    cleaned_text = re.sub(r'\n{3,}', '\n\n', "\n".join(cleaned_lines)).strip()
    
    if not cleaned_text or len(cleaned_text) < 10:
        return []
        
    sub_texts = split_text_with_overlap(cleaned_text, max_chars=max_chars, overlap=overlap)
    num_sub = len(sub_texts)
    chunks: List[RAGChunk] = []
    
    for sub_idx, sub_text in enumerate(sub_texts):
        sub_suffix = f" (Part {sub_idx + 1}/{num_sub})" if num_sub > 1 else ""
        header_prefix = f"--- [DOCUMENT: {filename}] [YEAR: {meta_info.get('year')}] [TEXT{sub_suffix}] ---\n\n"
        full_chunk_text = header_prefix + sub_text
        
        chunk_id = f"CHUNK_TXT_{meta_info.get('file_id', 'UNKNOWN')}_{sub_idx+1}"
        
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
            file_type=file_ext,
            content_type='text_doc',
            chunk_index=sub_idx,
            char_count=len(full_chunk_text),
            token_count_approx=estimate_tokens(full_chunk_text),
            text=full_chunk_text,
            extra_metadata={
                'sub_part': sub_idx + 1,
                'total_sub_parts': num_sub
            }
        )
        chunks.append(chunk)
        
    return chunks
