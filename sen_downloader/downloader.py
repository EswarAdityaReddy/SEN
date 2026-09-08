import os
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, Tuple
import requests

from .config import (
    RAW_DIR, DEFAULT_HEADERS, CONNECT_TIMEOUT, READ_TIMEOUT,
    MAX_RETRIES, BACKOFF_FACTOR, MAGIC_BYTES
)
from .logger import logger

def calculate_sha256(filepath: Path) -> str:
    """Calculates SHA256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def validate_file_bytes(filepath: Path, expected_ext: str) -> Tuple[bool, str]:
    """
    Validates file magic bytes and prevents HTML error pages saved as PDF/ZIP (Section 15 & 16).
    """
    if not filepath.exists() or filepath.stat().st_size == 0:
        return False, "File is empty or does not exist"

    with open(filepath, "rb") as f:
        header = f.read(1024)

    # Check for HTML error pages
    for html_sig in MAGIC_BYTES["html"]:
        if html_sig.lower() in header.lower():
            return False, "Downloaded file is an HTML error page, not requested document format"

    ext = expected_ext.lower().lstrip(".")

    if ext == "pdf":
        if not header.startswith(MAGIC_BYTES["pdf"]):
            return False, f"Invalid PDF header: expected {MAGIC_BYTES['pdf']}, got {header[:10]}"

    elif ext == "zip" or ext == "docx":
        if not header.startswith(MAGIC_BYTES["zip"]):
            return False, f"Invalid ZIP/DOCX header: expected {MAGIC_BYTES['zip']}, got {header[:10]}"

    return True, "Valid"


def download_file(doc_info: Dict[str, Any], overwrite: bool = False) -> Dict[str, Any]:
    """
    Robust, resumable streaming HTTP downloader with retry logic, exponential backoff,
    .part temporary files, magic byte validation, and SHA256 calculation.
    """
    year = doc_info["year"]
    filename = doc_info["filename"]
    download_url = doc_info["download_url"]
    referer = doc_info.get("referer") or doc_info.get("source_url")
    ext = doc_info.get("file_extension", ".bin")

    year_raw_dir = RAW_DIR / str(year)
    year_raw_dir.mkdir(parents=True, exist_ok=True)

    target_path = year_raw_dir / filename
    part_path = year_raw_dir / f"{filename}.part"

    # Resumability check
    if target_path.exists() and not overwrite:
        valid, msg = validate_file_bytes(target_path, ext)
        if valid:
            sha256 = calculate_sha256(target_path)
            logger.info(f"Skipping {filename} (Already exists and valid): {target_path}")
            return {
                "status": "SKIPPED_ALREADY_EXISTS",
                "filepath": target_path,
                "file_size": target_path.stat().st_size,
                "sha256": sha256,
                "error": None
            }
        else:
            logger.warning(f"Existing file {filename} invalid ({msg}). Re-downloading...")
            target_path.unlink(missing_ok=True)

    headers = DEFAULT_HEADERS.copy()
    if referer:
        headers["Referer"] = referer

    attempt = 0
    success = False
    last_error = ""

    while attempt < MAX_RETRIES and not success:
        attempt += 1
        logger.info(f"Downloading {filename} (Attempt {attempt}/{MAX_RETRIES}) from {download_url}")

        try:
            with requests.get(
                download_url,
                headers=headers,
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                stream=True
            ) as response:

                if response.status_code != 200:
                    last_error = f"HTTP status {response.status_code}"
                    logger.warning(f"Attempt {attempt} failed for {filename}: {last_error}")
                    time.sleep(BACKOFF_FACTOR ** attempt)
                    continue

                total_size = int(response.headers.get("Content-Length", 0))
                downloaded = 0
                last_log_mb = 0

                # Stream download to .part file
                with open(part_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            curr_mb = downloaded // (1024 * 1024)
                            if curr_mb >= last_log_mb + 5:  # Log every 5 MB
                                last_log_mb = curr_mb
                                if total_size > 0:
                                    pct = int((downloaded / total_size) * 100)
                                    logger.info(f"Downloading {filename}: {curr_mb} MB / {total_size // (1024*1024)} MB ({pct}%)")
                                else:
                                    logger.info(f"Downloading {filename}: {curr_mb} MB downloaded")

            # Validate downloaded .part file
            is_valid, val_msg = validate_file_bytes(part_path, ext)
            if not is_valid:
                last_error = f"Validation failed: {val_msg}"
                logger.warning(f"Attempt {attempt} for {filename} failed validation: {last_error}")
                part_path.unlink(missing_ok=True)
                time.sleep(BACKOFF_FACTOR ** attempt)
                continue

            # Atomic rename from .part to final target
            if part_path.exists():
                if target_path.exists():
                    target_path.unlink()
                part_path.rename(target_path)

            sha256 = calculate_sha256(target_path)
            file_size = target_path.stat().st_size
            logger.info(f"Successfully downloaded & validated {filename} ({file_size} bytes, SHA256: {sha256[:10]}...)")
            
            return {
                "status": "DOWNLOADED",
                "filepath": target_path,
                "file_size": file_size,
                "sha256": sha256,
                "error": None
            }

        except Exception as e:
            last_error = str(e)
            logger.warning(f"Attempt {attempt} exception for {filename}: {last_error}")
            part_path.unlink(missing_ok=True)
            time.sleep(BACKOFF_FACTOR ** attempt)

    # All retries exhausted
    logger.error(f"Failed to download {filename} after {MAX_RETRIES} attempts. Error: {last_error}")
    return {
        "status": "FAILED",
        "filepath": target_path,
        "file_size": 0,
        "sha256": "",
        "error": last_error
    }
