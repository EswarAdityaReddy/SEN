import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
SEN_DATA_DIR = BASE_DIR / "sen_data"

RAW_DIR = SEN_DATA_DIR / "raw"
EXTRACTED_DIR = SEN_DATA_DIR / "extracted"
METADATA_DIR = SEN_DATA_DIR / "metadata"
LOGS_DIR = SEN_DATA_DIR / "logs"
MANIFESTS_DIR = SEN_DATA_DIR / "manifests"

# Ensure directories exist
for folder in [SEN_DATA_DIR, RAW_DIR, EXTRACTED_DIR, METADATA_DIR, LOGS_DIR, MANIFESTS_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

# Target Years
TARGET_YEARS = list(range(2010, 2027))  # 2010 to 2026 inclusive

# Main GOV.UK collection URL
MAIN_COLLECTION_URL = "https://www.gov.uk/government/collections/statistics-special-educational-needs-sen"

# Supported file extensions
SUPPORTED_EXTENSIONS = [".pdf", ".csv", ".txt", ".xlsx", ".xls", ".zip", ".html", ".json", ".docx", ".doc"]

# File magic bytes for validation
MAGIC_BYTES = {
    "pdf": b"%PDF",
    "zip": b"PK\x03\x04",
    "docx": b"PK\x03\x04",
    "png": b"\x89PNG",
    "html": [b"<!DOCTYPE html", b"<html", b"<!doctype html", b"<!DOCTYPE HTML"],
}

# Network settings
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

CONNECT_TIMEOUT = 15
READ_TIMEOUT = 120
MAX_RETRIES = 5
BACKOFF_FACTOR = 2.0
