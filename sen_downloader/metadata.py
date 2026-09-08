import json
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from .config import METADATA_DIR, MANIFESTS_DIR, SEN_DATA_DIR
from .logger import logger

class MetadataManager:
    """Manages creation, updates, and persistence of CSV metadata tables and JSON manifests."""

    def __init__(self):
        self.doc_metadata_path = METADATA_DIR / "document_metadata.csv"
        self.file_metadata_path = METADATA_DIR / "file_metadata.csv"
        self.download_log_path = METADATA_DIR / "download_log.csv"
        self.failed_downloads_path = METADATA_DIR / "failed_downloads.csv"

        self.documents: List[Dict[str, Any]] = []
        self.files: List[Dict[str, Any]] = []
        self.download_logs: List[Dict[str, Any]] = []
        self.failed_downloads: List[Dict[str, Any]] = []

        self._load_existing()

    def _load_existing(self):
        """Loads existing CSV metadata if present to ensure resumability."""
        if self.doc_metadata_path.exists():
            try:
                self.documents = pd.read_csv(self.doc_metadata_path).to_dict(orient="records")
            except Exception:
                self.documents = []

        if self.file_metadata_path.exists():
            try:
                self.files = pd.read_csv(self.file_metadata_path).to_dict(orient="records")
            except Exception:
                self.files = []

        if self.download_log_path.exists():
            try:
                self.download_logs = pd.read_csv(self.download_log_path).to_dict(orient="records")
            except Exception:
                self.download_logs = []

        if self.failed_downloads_path.exists():
            try:
                self.failed_downloads = pd.read_csv(self.failed_downloads_path).to_dict(orient="records")
            except Exception:
                self.failed_downloads = []

    def record_document(self, doc_info: Dict[str, Any], download_res: Dict[str, Any]):
        """Records document entry and physical raw file entry."""
        year = doc_info["year"]
        filename = doc_info["filename"]
        status = download_res["status"]

        # Check existing document record
        self.documents = [d for d in self.documents if not (d.get("year") == year and d.get("filename") == filename)]

        doc_entry = {
            "document_id": doc_info["document_id"],
            "year": year,
            "title": doc_info.get("title", ""),
            "publisher": doc_info.get("publisher", "Department for Education"),
            "publication_date": doc_info.get("publication_date", f"{year}-01-01"),
            "document_type": doc_info.get("document_type", "Document"),
            "filename": filename,
            "source_url": doc_info.get("source_url", ""),
            "download_url": doc_info.get("download_url", ""),
            "file_extension": doc_info.get("file_extension", ""),
            "status": status
        }
        self.documents.append(doc_entry)

        # Record physical raw file if downloaded successfully
        if status in ["DOWNLOADED", "SKIPPED_ALREADY_EXISTS"]:
            file_entry = {
                "file_id": f"FILE_RAW_{doc_info['document_id']}",
                "year": year,
                "document_id": doc_info["document_id"],
                "filename": filename,
                "relative_path": f"raw/{year}/{filename}",
                "file_type": doc_info.get("file_extension", "").lstrip("."),
                "file_size_bytes": download_res.get("file_size", 0),
                "sha256": download_res.get("sha256", ""),
                "source_url": doc_info.get("source_url", ""),
                "download_url": doc_info.get("download_url", ""),
                "parent_archive": "N/A",
                "extraction_status": "RAW_FILE"
            }
            self.files = [f for f in self.files if not (f.get("year") == year and f.get("filename") == filename)]
            self.files.append(file_entry)

        # Record log entry
        log_entry = {
            "download_id": f"LOG_{year}_{len(self.download_logs)+1:04d}",
            "year": year,
            "filename": filename,
            "status": status,
            "download_timestamp": datetime.now().isoformat(),
            "http_status": 200 if status in ["DOWNLOADED", "SKIPPED_ALREADY_EXISTS"] else 500,
            "error_message": download_res.get("error", "") or "None",
            "attempts": 1,
            "source_url": doc_info.get("source_url", "")
        }
        self.download_logs.append(log_entry)

        # Handle failed downloads table
        if status == "FAILED":
            fail_entry = {
                "year": year,
                "filename": filename,
                "source_url": doc_info.get("source_url", ""),
                "download_url": doc_info.get("download_url", ""),
                "error_message": download_res.get("error", ""),
                "attempts": 5
            }
            self.failed_downloads = [f for f in self.failed_downloads if not (f.get("year") == year and f.get("filename") == filename)]
            self.failed_downloads.append(fail_entry)
        else:
            self.failed_downloads = [f for f in self.failed_downloads if not (f.get("year") == year and f.get("filename") == filename)]

    def record_extracted_files(self, extracted_records: List[Dict[str, Any]]):
        """Records extracted file entries into file_metadata.csv."""
        for rec in extracted_records:
            self.files = [f for f in self.files if not (f.get("year") == rec["year"] and f.get("filename") == rec["filename"])]
            self.files.append(rec)

    def save_all(self):
        """Flushes in-memory data to CSV files."""
        if self.documents:
            pd.DataFrame(self.documents).to_csv(self.doc_metadata_path, index=False)
        if self.files:
            pd.DataFrame(self.files).to_csv(self.file_metadata_path, index=False)
        if self.download_logs:
            pd.DataFrame(self.download_logs).to_csv(self.download_log_path, index=False)

        # Write failed downloads CSV (even if empty, write headers)
        pd.DataFrame(self.failed_downloads, columns=["year", "filename", "source_url", "download_url", "error_message", "attempts"]).to_csv(self.failed_downloads_path, index=False)
        logger.info("Successfully updated metadata CSV files.")

    def write_year_manifest(self, year: int) -> Path:
        """Generates JSON manifest for a single year."""
        year_docs = [d for d in self.documents if d.get("year") == year]
        year_files = [f for f in self.files if f.get("year") == year]

        manifest = {
            "year": year,
            "generated_at": datetime.now().isoformat(),
            "total_documents": len(year_docs),
            "total_files": len(year_files),
            "documents": year_docs,
            "files": year_files
        }

        manifest_path = MANIFESTS_DIR / f"manifest_{year}.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        return manifest_path

    def write_corpus_manifest(self) -> Path:
        """Generates corpus_manifest.json covering all years."""
        corpus = {
            "generated_at": datetime.now().isoformat(),
            "total_documents": len(self.documents),
            "total_files": len(self.files),
            "documents": self.documents,
            "files": self.files
        }
        corpus_path = SEN_DATA_DIR / "corpus_manifest.json"
        with open(corpus_path, "w", encoding="utf-8") as f:
            json.dump(corpus, f, indent=2)
        return corpus_path
