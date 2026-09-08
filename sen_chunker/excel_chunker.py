"""
Excel document chunking for SEN dataset workbooks (.xlsx and .xls).
Extracts sheets, cleans tabular data, formats into markdown tables with repeated headers,
and creates RAGChunk objects with full sheet and row-range metadata.
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
    
    # Truncate columns if extremely wide
    if len(df.columns) > max_cols:
        df = df.iloc[:, :max_cols]
    
    # Replace NaN values with empty string or '-'
    df_clean = df.fillna("-").astype(str)
    
    # Format headers
    headers = [str(c).strip().replace("\n", " ") for c in df_clean.columns]
    header_str = "| " + " | ".join(headers) + " |"
    sep_str = "| " + " | ".join(["---"] * len(headers)) + " |"
    
    rows_str = []
    for _, row in df_clean.iterrows():
        row_vals = [str(val).strip().replace("\n", " ") for val in row.values]
        rows_str.append("| " + " | ".join(row_vals) + " |")
        
    return header_str + "\n" + sep_str + "\n" + "\n".join(rows_str)

def chunk_excel_file(
    file_path: str,
    meta_info: Dict[str, Any],
    max_rows_per_chunk: int = 60,
    max_chars_per_chunk: int = 3500
) -> List[RAGChunk]:
    """
    Extracts sheets from an Excel workbook (.xlsx or .xls).
    Creates Markdown table chunks with sheet and row range metadata.
    """
    if not os.path.exists(file_path):
        return []
    
    chunks: List[RAGChunk] = []
    filename = meta_info.get('filename', os.path.basename(file_path))
    file_ext = os.path.splitext(file_path)[1].lower()
    
    try:
        # Determine pandas excel engine
        engine = 'openpyxl' if file_ext == '.xlsx' else 'xlrd'
        xl = pd.ExcelFile(file_path, engine=engine)
        sheet_names = xl.sheet_names
        
        for sheet_name in sheet_names:
            try:
                df = pd.read_excel(xl, sheet_name=sheet_name)
            except Exception as se:
                print(f"Error reading sheet '{sheet_name}' in {filename}: {se}")
                continue
                
            # Drop completely empty rows & columns
            df = df.dropna(how='all').dropna(how='all', axis=1)
            if df.empty or len(df.columns) == 0:
                continue
                
            total_rows = len(df)
            
            # Process in row batches
            start_idx = 0
            chunk_sub_idx = 1
            
            while start_idx < total_rows:
                end_idx = min(start_idx + max_rows_per_chunk, total_rows)
                df_batch = df.iloc[start_idx:end_idx]
                
                md_table = df_to_markdown_batch(df_batch)
                
                if not md_table.strip():
                    start_idx = end_idx
                    continue
                    
                row_range_str = f"Rows {start_idx + 1}-{end_idx} of {total_rows}"
                header_prefix = (
                    f"--- [DOCUMENT: {filename}] [YEAR: {meta_info.get('year')}] "
                    f"[SHEET: {sheet_name}] [{row_range_str}] ---\n\n"
                )
                full_chunk_text = header_prefix + md_table
                
                # Check character count; if it exceeds max_chars, reduce batch size next time
                if len(full_chunk_text) > max_chars_per_chunk and (end_idx - start_idx) > 10:
                    end_idx = start_idx + max(10, (end_idx - start_idx) // 2)
                    df_batch = df.iloc[start_idx:end_idx]
                    md_table = df_to_markdown_batch(df_batch)
                    row_range_str = f"Rows {start_idx + 1}-{end_idx} of {total_rows}"
                    header_prefix = (
                        f"--- [DOCUMENT: {filename}] [YEAR: {meta_info.get('year')}] "
                        f"[SHEET: {sheet_name}] [{row_range_str}] ---\n\n"
                    )
                    full_chunk_text = header_prefix + md_table

                chunk_id = f"CHUNK_XLS_{meta_info.get('file_id', 'UNKNOWN')}_{re.sub(r'[^a-zA-Z0-9]', '_', sheet_name)}_{chunk_sub_idx}"
                
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
                    content_type='excel_sheet',
                    sheet_name=str(sheet_name),
                    row_range=f"{start_idx + 1}-{end_idx}",
                    chunk_index=len(chunks),
                    char_count=len(full_chunk_text),
                    token_count_approx=estimate_tokens(full_chunk_text),
                    text=full_chunk_text,
                    extra_metadata={
                        'total_rows_in_sheet': total_rows,
                        'total_cols_in_sheet': len(df.columns),
                        'sheet_name': str(sheet_name)
                    }
                )
                chunks.append(chunk)
                
                chunk_sub_idx += 1
                start_idx = end_idx
                
        xl.close()
    except Exception as e:
        print(f"Error processing Excel file {file_path}: {e}")
        
    return chunks
