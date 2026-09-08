"""
CSV dataset chunking for SEN underlying data files and EES CSV statistical releases.
Extracts rows, cleans columns, formats into markdown tables with repeated headers,
and creates RAGChunk objects with full row-range and dataset metadata.
Includes adaptive row batching and chunk cap to handle multi-gigabyte EES datasets efficiently.
"""

import os
import re
import warnings
from typing import List, Dict, Any, Optional
import pandas as pd
from .schema import RAGChunk

warnings.filterwarnings('ignore')

def estimate_tokens(text: str) -> int:
    """Rough estimate of token count (1 token ~= 4 characters or ~0.75 words)."""
    if not text:
        return 0
    words = text.split()
    return int(len(words) * 1.3)

def df_to_markdown_batch(df: pd.DataFrame, max_cols: int = 15) -> str:
    """Converts a DataFrame batch into a clean Markdown table representation."""
    if df.empty:
        return ""
    
    if len(df.columns) > max_cols:
        df = df.iloc[:, :max_cols]
        
    df_clean = df.fillna("-").astype(str)
    headers = [str(c).strip().replace("\n", " ") for c in df_clean.columns]
    header_str = "| " + " | ".join(headers) + " |"
    sep_str = "| " + " | ".join(["---"] * len(headers)) + " |"
    
    rows_str = []
    for _, row in df_clean.iterrows():
        row_vals = [str(val).strip().replace("\n", " ") for val in row.values]
        rows_str.append("| " + " | ".join(row_vals) + " |")
        
    return header_str + "\n" + sep_str + "\n" + "\n".join(rows_str)

def chunk_csv_file(
    file_path: str,
    meta_info: Dict[str, Any],
    max_rows_per_chunk: int = 60,
    max_chars_per_chunk: int = 3500,
    max_chunks_per_file: int = 1200
) -> List[RAGChunk]:
    """
    Extracts data from a CSV file with adaptive row batching for large EES releases.
    Creates Markdown table chunks tagged with row range and CSV dataset metadata.
    """
    if not os.path.exists(file_path):
        return []
    
    chunks: List[RAGChunk] = []
    filename = meta_info.get('filename', os.path.basename(file_path))
    
    # Check file size to set read options for ultra-fast processing
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    read_kwargs = {'low_memory': False}
    if file_size_mb > 50:
        read_kwargs['nrows'] = 100000

    # Try reading CSV with fallback encodings
    df = None
    for encoding in ['utf-8', 'latin1', 'cp1252', 'iso-8859-1']:
        try:
            df = pd.read_csv(file_path, encoding=encoding, **read_kwargs)
            break
        except Exception:
            continue
            
    if df is None:
        print(f"Failed to read CSV file {file_path} with standard encodings.")
        return []
        
    df = df.dropna(how='all').dropna(how='all', axis=1)
    if df.empty or len(df.columns) == 0:
        return []
        
    total_rows = len(df)
    dataset_name = os.path.splitext(filename)[0]
    
    # Adaptive batching for large datasets
    if total_rows > 100000:
        step_size = max(max_rows_per_chunk, total_rows // max_chunks_per_file)
    elif total_rows > 20000:
        step_size = max(max_rows_per_chunk, total_rows // max_chunks_per_file)
    else:
        step_size = max_rows_per_chunk

    start_idx = 0
    sub_idx = 1
    
    while start_idx < total_rows and len(chunks) < max_chunks_per_file:
        end_idx = min(start_idx + step_size, total_rows)
        df_batch = df.iloc[start_idx:end_idx]
        
        # If batch is still too large for markdown formatting, sample 60 representative rows
        if len(df_batch) > 100:
            df_batch_sample = df_batch.iloc[:60]
        else:
            df_batch_sample = df_batch

        md_table = df_to_markdown_batch(df_batch_sample)
        if not md_table.strip():
            start_idx = end_idx
            continue
            
        row_range_str = f"Rows {start_idx + 1}-{end_idx} of {total_rows}"
        header_prefix = (
            f"--- [DOCUMENT: {filename}] [YEAR: {meta_info.get('year')}] "
            f"[DATASET: {dataset_name}] [{row_range_str}] ---\n\n"
        )
        full_chunk_text = header_prefix + md_table
        
        chunk_id = f"CHUNK_CSV_{meta_info.get('file_id', 'UNKNOWN')}_{sub_idx}"
        
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
            file_type='.csv',
            content_type='csv_dataset',
            row_range=f"{start_idx + 1}-{end_idx}",
            chunk_index=len(chunks),
            char_count=len(full_chunk_text),
            token_count_approx=estimate_tokens(full_chunk_text),
            text=full_chunk_text,
            extra_metadata={
                'total_rows_in_csv': total_rows,
                'total_cols_in_csv': len(df.columns),
                'dataset_name': dataset_name
            }
        )
        chunks.append(chunk)
        
        sub_idx += 1
        start_idx = end_idx
        
    return chunks
