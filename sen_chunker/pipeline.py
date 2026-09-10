"""
Chunking Pipeline Orchestrator for SEN Vector RAG Corpus.
Processes all files registered in sen_data/metadata/file_metadata.csv,
dispatches to specialized format chunkers, enriches chunks with lineage metadata,
and exports processed chunks and manifests to sen_data/processed/.
"""

import os
import json
import time
import warnings
from typing import List, Dict, Any, Optional
import pandas as pd

warnings.filterwarnings('ignore')

from .schema import RAGChunk
from .pdf_chunker import chunk_pdf_file
from .excel_chunker import chunk_excel_file
from .csv_chunker import chunk_csv_file
from .text_chunker import chunk_text_file
from .docx_chunker import chunk_docx_file

def run_chunking_pipeline(
    data_dir: str,
    output_dir: Optional[str] = None,
    target_year: Optional[int] = None
) -> Dict[str, Any]:
    """
    Executes chunking across the SEN document corpus.
    Reads file_metadata.csv and document_metadata.csv, produces RAGChunk items,
    and writes outputs to sen_data/processed/.
    """
    if not output_dir:
        output_dir = os.path.join(data_dir, "processed")
    os.makedirs(output_dir, exist_ok=True)

    metadata_dir = os.path.join(data_dir, "metadata")
    file_meta_path = os.path.join(metadata_dir, "file_metadata.csv")
    doc_meta_path = os.path.join(metadata_dir, "document_metadata.csv")

    if not os.path.exists(file_meta_path):
        raise FileNotFoundError(f"File metadata not found at {file_meta_path}")

    # Read metadata tables
    df_files = pd.read_csv(file_meta_path)
    
    doc_meta_map: Dict[str, Dict[str, Any]] = {}
    if os.path.exists(doc_meta_path):
        df_docs = pd.read_csv(doc_meta_path)
        for _, row in df_docs.iterrows():
            doc_id = str(row.get('document_id', ''))
            doc_meta_map[doc_id] = row.to_dict()

    archive_count = int((df_files['file_type'].astype(str).str.lower() == 'zip').sum())
    extracted_records = df_files['relative_path'].astype(str).str.replace('\\', '/', regex=False).str.startswith('extracted/')
    df_files = df_files[extracted_records]

    if target_year is not None:
        df_files = df_files[df_files['year'] == target_year]

    total_files_in_manifest = len(df_files)
    print(f"Starting SEN Chunking Pipeline over {total_files_in_manifest} file records...", flush=True)
    start_time = time.time()

    all_chunks: List[RAGChunk] = []
    file_type_counts: Dict[str, int] = {
        'pdf': 0,
        'excel': 0,
        'csv': 0,
        'text': 0,
        'docx': 0,
        'skipped': 0,
        'archives_skipped': archive_count,
    }
    chunk_counts_by_format: Dict[str, int] = {'pdf_page': 0, 'excel_sheet': 0, 'csv_dataset': 0, 'text_doc': 0}
    chunk_counts_by_year: Dict[int, int] = {}
    processed_files_count = 0

    for f_idx, (_, row) in enumerate(df_files.iterrows(), 1):
        file_id = str(row.get('file_id', ''))
        year = int(row.get('year', 0))
        rel_path = str(row.get('relative_path', ''))
        filename = str(row.get('filename', ''))
        file_type = str(row.get('file_type', '')).lower()
        doc_id = str(row.get('document_id', ''))

        # Process only files in the extracted corpus.
        extracted_rel_path = f"extracted/{year}/{filename}"
        full_path = os.path.join(data_dir, extracted_rel_path.replace("/", os.sep))

        if not os.path.exists(full_path):
            print(f"Warning: File not found on disk: {extracted_rel_path} ({full_path})")
            file_type_counts['skipped'] += 1
            continue

        # Skip raw zip containers since their contents are already extracted
        if file_type == 'zip':
            file_type_counts['archives_skipped'] += 1
            continue

        # Retrieve document level metadata if available
        doc_info = doc_meta_map.get(doc_id, {})
        meta_info = {
            'file_id': file_id,
            'year': year,
            'academic_year': doc_info.get('academic_year') or (f"{year-1}-{str(year)[2:]}" if year > 2000 else str(year)),
            'document_id': doc_id,
            'filename': filename,
            'relative_path': extracted_rel_path,
            'source_url': row.get('source_url') or doc_info.get('source_url'),
            'publication_url': row.get('download_url') or doc_info.get('publication_url'),
        }

        file_chunks: List[RAGChunk] = []

        if file_type == 'pdf':
            file_chunks = chunk_pdf_file(full_path, meta_info)
            file_type_counts['pdf'] += 1
        elif file_type in ['xls', 'xlsx']:
            file_chunks = chunk_excel_file(full_path, meta_info)
            file_type_counts['excel'] += 1
        elif file_type == 'csv':
            file_chunks = chunk_csv_file(full_path, meta_info)
            file_type_counts['csv'] += 1
        elif file_type in ['txt', 'text', 'html']:
            file_chunks = chunk_text_file(full_path, meta_info)
            file_type_counts['text'] += 1
        elif file_type == 'docx':
            file_chunks = chunk_docx_file(full_path, meta_info)
            file_type_counts['docx'] += 1
        else:
            file_type_counts['skipped'] += 1
            continue

        if file_chunks:
            processed_files_count += 1
            num_file_chunks = len(file_chunks)
            print(f"[{f_idx}/{total_files_in_manifest}] Chunked {filename} ({file_type}) -> {num_file_chunks} chunks", flush=True)
            for idx, chk in enumerate(file_chunks):
                chk.chunk_index = idx
                chk.total_chunks_in_file = num_file_chunks
                all_chunks.append(chk)

                # Record stats
                chunk_counts_by_format[chk.content_type] = chunk_counts_by_format.get(chk.content_type, 0) + 1
                chunk_counts_by_year[chk.year] = chunk_counts_by_year.get(chk.year, 0) + 1
        else:
            print(f"[{f_idx}/{total_files_in_manifest}] Skipped/0 chunks: {filename} ({file_type})", flush=True)

    # Save all chunks to JSON
    chunks_json_path = os.path.join(output_dir, "chunks.json")
    chunks_data = [chk.to_dict() for chk in all_chunks]
    
    with open(chunks_json_path, 'w', encoding='utf-8') as f:
        json.dump(chunks_data, f, indent=2, ensure_ascii=False)

    # Token and length metrics
    token_counts = [chk.token_count_approx for chk in all_chunks]
    char_counts = [chk.char_count for chk in all_chunks]
    
    total_tokens = sum(token_counts)
    avg_tokens = (total_tokens / len(token_counts)) if token_counts else 0
    min_tokens = min(token_counts) if token_counts else 0
    max_tokens = max(token_counts) if token_counts else 0

    elapsed_sec = round(time.time() - start_time, 2)

    manifest = {
        'total_chunks': len(all_chunks),
        'total_files_chunked': processed_files_count,
        'processing_time_seconds': elapsed_sec,
        'files_by_format': file_type_counts,
        'chunks_by_content_type': chunk_counts_by_format,
        'chunks_by_year': {str(k): v for k, v in sorted(chunk_counts_by_year.items())},
        'token_statistics': {
            'total_tokens_approx': total_tokens,
            'avg_tokens_per_chunk': round(avg_tokens, 1),
            'min_tokens': min_tokens,
            'max_tokens': max_tokens,
            'total_characters': sum(char_counts)
        },
        'output_files': {
            'chunks_json': chunks_json_path,
            'chunks_manifest': os.path.join(output_dir, "chunks_manifest.json")
        }
    }

    manifest_path = os.path.join(output_dir, "chunks_manifest.json")
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)

    print("\n==================================================")
    print("SEN DATA CHUNKING PIPELINE COMPLETE")
    print("==================================================")
    print(f"Total Chunks Generated : {manifest['total_chunks']}")
    print(f"Files Chunked          : {processed_files_count}")
    print(f"Processing Time        : {elapsed_sec} seconds")
    print(f"Total Tokens (approx)  : {total_tokens:,}")
    print(f"Average Tokens / Chunk : {round(avg_tokens, 1)}")
    print("--------------------------------------------------")
    print("Chunks by Content Type:")
    for ctype, ccount in chunk_counts_by_format.items():
        print(f"  - {ctype:<15}: {ccount}")
    print("--------------------------------------------------")
    print(f"Output saved to: {chunks_json_path}")
    print("==================================================\n")

    return manifest
