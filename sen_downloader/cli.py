import argparse
from typing import List, Optional

from .config import TARGET_YEARS
from .logger import logger
from .discovery import discover_publication_years
from .govuk import parse_govuk_publication_page
from .ees import parse_ees_publication_page
from .downloader import download_file
from .extractor import process_and_extract_zip
from .metadata import MetadataManager
from .validator import validate_corpus_and_generate_report

def run_pipeline(years_to_process: List[int], retry_failed_only: bool = False):
    """
    Main execution pipeline for target years.
    Parses pages, downloads files, extracts ZIP archives, records metadata,
    and writes manifests.
    """
    meta_mgr = MetadataManager()

    if retry_failed_only:
        logger.info("Running in --retry-failed mode.")
        if not meta_mgr.failed_downloads:
            logger.info("No failed downloads found in metadata. Nothing to retry.")
            validate_corpus_and_generate_report()
            return
        
        failed_list = list(meta_mgr.failed_downloads)
        for fail in failed_list:
            doc_info = {
                "document_id": f"SEN_{fail['year']}_RETRY",
                "year": fail["year"],
                "filename": fail["filename"],
                "source_url": fail["source_url"],
                "download_url": fail["download_url"],
                "file_extension": "." + fail["filename"].rsplit(".", 1)[-1]
            }
            dl_res = download_file(doc_info, overwrite=True)
            meta_mgr.record_document(doc_info, dl_res)

            if dl_res["status"] == "DOWNLOADED" and doc_info["filename"].lower().endswith(".zip"):
                ext_records = process_and_extract_zip(fail["year"], dl_res["filepath"], doc_info["document_id"])
                meta_mgr.record_extracted_files(ext_records)

            meta_mgr.save_all()

        validate_corpus_and_generate_report()
        return

    # Standard run: discover publication URLs
    pub_years = discover_publication_years()

    for year in years_to_process:
        if year not in pub_years:
            logger.error(f"Year {year} is not in discovered publications.")
            continue

        pub_url = pub_years[year]
        logger.info(f"\n=================== Processing Year {year} ===================")

        # 1. Parse GOV.UK page first
        page_info = parse_govuk_publication_page(year, pub_url)

        # 2. Strategy A vs Strategy B
        if page_info["strategy"] == "EES":
            ees_url = page_info["ees_url"]
            ees_info = parse_ees_publication_page(year, ees_url)
            documents = ees_info["documents"]
        else:
            documents = page_info["documents"]

        if not documents:
            logger.warning(f"No downloadable documents discovered for year {year}")

        # 3. Download and extract each document
        for doc in documents:
            dl_res = download_file(doc)
            meta_mgr.record_document(doc, dl_res)

            # If file is a ZIP archive, test integrity and extract
            if dl_res["status"] in ["DOWNLOADED", "SKIPPED_ALREADY_EXISTS"] and doc["filename"].lower().endswith(".zip"):
                ext_records = process_and_extract_zip(year, dl_res["filepath"], doc["document_id"])
                meta_mgr.record_extracted_files(ext_records)

        # Flush metadata & write per-year manifest
        meta_mgr.save_all()
        meta_mgr.write_year_manifest(year)

    # Write overall corpus manifest & generate final report
    meta_mgr.write_corpus_manifest()
    validate_corpus_and_generate_report()


def main():
    parser = argparse.ArgumentParser(description="UK DfE Special Educational Needs (SEN) Statistics Data Downloader (2010-2026)")
    parser.add_argument("--all", action="store_true", help="Download and process all target years (2010-2026)")
    parser.add_argument("--year", type=int, choices=TARGET_YEARS, help="Download and process a specific year (2010-2026)")
    parser.add_argument("--retry-failed", action="store_true", help="Retry failed downloads recorded in metadata")
    parser.add_argument("--validate", action="store_true", help="Run corpus validation and print summary report")

    args = parser.parse_args()

    if args.validate:
        validate_corpus_and_generate_report()
        return

    if args.retry_failed:
        run_pipeline(TARGET_YEARS, retry_failed_only=True)
        return

    if args.year:
        run_pipeline([args.year])
        return

    if args.all:
        run_pipeline(TARGET_YEARS)
        return

    # Default if no arguments specified: process all
    parser.print_help()


if __name__ == "__main__":
    main()
