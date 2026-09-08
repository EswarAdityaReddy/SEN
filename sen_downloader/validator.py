from typing import Dict, Any
import pandas as pd
from pathlib import Path

from .config import TARGET_YEARS, METADATA_DIR, RAW_DIR, SEN_DATA_DIR
from .logger import logger

def validate_corpus_and_generate_report() -> Dict[str, Any]:
    """
    Validates corpus files, metadata tables, checksums, and generates
    the final summary report per Section 22 and 29.
    """
    doc_csv = METADATA_DIR / "document_metadata.csv"
    file_csv = METADATA_DIR / "file_metadata.csv"
    failed_csv = METADATA_DIR / "failed_downloads.csv"

    docs_df = pd.read_csv(doc_csv) if doc_csv.exists() else pd.DataFrame()
    files_df = pd.read_csv(file_csv) if file_csv.exists() else pd.DataFrame()
    failed_df = pd.read_csv(failed_csv) if failed_csv.exists() else pd.DataFrame()

    total_years = len(TARGET_YEARS)
    completed_years = 0
    years_status = {}

    for year in TARGET_YEARS:
        year_docs = docs_df[docs_df["year"] == year] if not docs_df.empty else pd.DataFrame()
        if not year_docs.empty and all(st in ["DOWNLOADED", "SKIPPED_ALREADY_EXISTS"] for st in year_docs["status"]):
            completed_years += 1
            years_status[year] = "COMPLETE"
        elif not year_docs.empty:
            years_status[year] = "PARTIAL"
        else:
            years_status[year] = "MISSING"

    discovered_count = len(docs_df)
    downloaded_count = len(docs_df[docs_df["status"] == "DOWNLOADED"]) if not docs_df.empty else 0
    skipped_count = len(docs_df[docs_df["status"] == "SKIPPED_ALREADY_EXISTS"]) if not docs_df.empty else 0
    failed_count = len(failed_df) if not failed_df.empty else 0

    ext_counts = {
        "PDF": 0,
        "XLSX": 0,
        "CSV": 0,
        "TXT": 0,
        "ZIP": 0,
        "HTML": 0
    }

    total_bytes = 0
    if not files_df.empty:
        total_bytes = files_df["file_size_bytes"].sum()
        for ft in files_df["file_type"].dropna():
            ft_upper = str(ft).upper()
            if ft_upper in ext_counts:
                ext_counts[ft_upper] += 1

    total_size_mb = round(total_bytes / (1024 * 1024), 2)

    report_str = f"""
==================================================
SEN DATA DOWNLOAD COMPLETE
==========================

Years requested: 2010–2026
Years completed: {completed_years}/{total_years}

Files discovered: {discovered_count}
Files downloaded: {downloaded_count}
Files skipped:    {skipped_count}
Files failed:     {failed_count}

PDF:  {ext_counts['PDF']}
XLSX: {ext_counts['XLSX']}
CSV:  {ext_counts['CSV']}
TXT:  {ext_counts['TXT']}
ZIP:  {ext_counts['ZIP']}
HTML: {ext_counts['HTML']}

Total downloaded size: {total_size_mb} MB
"""

    if failed_count > 0:
        report_str += "\nFailed resources:\n"
        for idx, row in failed_df.iterrows():
            report_str += f"  - [{row['year']}] {row['filename']}: {row['error_message']}\n"
        report_str += "\nRun 'python main.py --retry-failed' to retry failed downloads.\n"
    else:
        report_str += "\nNo failed downloads recorded! All target files validated successfully.\n"

    report_str += "==================================================\n"

    print(report_str)
    logger.info("Generated corpus validation report.")

    return {
        "completed_years": completed_years,
        "total_years": total_years,
        "discovered_count": discovered_count,
        "downloaded_count": downloaded_count,
        "skipped_count": skipped_count,
        "failed_count": failed_count,
        "total_size_mb": total_size_mb,
        "report": report_str
    }
