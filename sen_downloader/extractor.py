import os
import zipfile
import hashlib
from pathlib import Path
from typing import List, Dict, Any

from .config import EXTRACTED_DIR, SUPPORTED_EXTENSIONS
from .logger import logger

def calculate_sha256(filepath: Path) -> str:
    """Calculates SHA256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def process_and_extract_zip(year: int, zip_path: Path, doc_id: str) -> List[Dict[str, Any]]:
    """
    Validates ZIP file integrity with zipfile.testzip(), extracts contents
    into sen_data/extracted/{year}/, applies clean year prefixes, and returns
    extracted file metadata dicts.
    """
    extracted_records: List[Dict[str, Any]] = []
    if not zip_path.exists():
        logger.error(f"ZIP file does not exist for extraction: {zip_path}")
        return extracted_records

    target_extract_dir = EXTRACTED_DIR / str(year)
    target_extract_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Extracting ZIP archive for year {year}: {zip_path.name} -> {target_extract_dir}")

    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            # 1. Test ZIP integrity
            test_res = zip_ref.testzip()
            if test_res is not None:
                logger.error(f"Corrupt ZIP file detected in {zip_path.name}: bad file {test_res}")
                return extracted_records

            # 2. Extract files
            for member in zip_ref.infolist():
                if member.is_dir():
                    continue

                orig_name = member.filename.replace("\\", "/")
                basename = os.path.basename(orig_name)
                
                if not basename or basename.startswith("."):
                    continue

                ext = os.path.splitext(basename)[1].lower()
                clean_base = os.path.splitext(basename)[0]
                clean_base = clean_base.replace(" ", "_").replace("-", "_")

                # Format clean extracted filename with year prefix
                new_filename = f"SEN_{year}_EXT_{clean_base}{ext}"
                out_filepath = target_extract_dir / new_filename

                # Extract content
                with zip_ref.open(member) as source_file, open(out_filepath, "wb") as target_file:
                    target_file.write(source_file.read())

                file_size = out_filepath.stat().st_size
                sha256 = calculate_sha256(out_filepath)

                rel_path = f"extracted/{year}/{new_filename}"

                record = {
                    "file_id": f"FILE_{year}_{len(extracted_records)+1:03d}",
                    "year": year,
                    "document_id": doc_id,
                    "filename": new_filename,
                    "relative_path": rel_path,
                    "file_type": ext.lstrip("."),
                    "file_size_bytes": file_size,
                    "sha256": sha256,
                    "parent_archive": zip_path.name,
                    "extraction_status": "EXTRACTED"
                }
                extracted_records.append(record)
                logger.info(f"Extracted {basename} -> {new_filename} ({file_size} bytes)")

    except Exception as e:
        logger.error(f"Failed to extract ZIP {zip_path.name}: {e}")

    return extracted_records
