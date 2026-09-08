# SEN Data Downloader (GOV.UK & Explore Education Statistics)

A production-grade, fault-tolerant Python data ingestion pipeline to automatically discover, download, validate, extract, and index official UK Department for Education **"Special educational needs in England"** publications from **2010 through 2026**.

---

## 1. Requirements & Dependencies

- **Python Version**: Python 3.10+ (Tested on Python 3.13)
- **Key Libraries**:
  - `requests` (Streaming HTTP downloads & API calls)
  - `beautifulsoup4` & `lxml` (HTML parsing)
  - `pandas` (Metadata CSV indexing)
  - `zipfile` & `hashlib` (ZIP validation, extraction & SHA256 checksums)

### Installation

Install requirements using `pip`:

```bash
pip install -r requirements.txt
```

---

## 2. Quick Start & Execution Commands

### Download All Years (2010–2026)

```bash
python main.py --all
```

### Download a Single Year (e.g. 2026 or 2018)

```bash
python main.py --year 2026
python main.py --year 2018
```

### Retry Failed Downloads

```bash
python main.py --retry-failed
```

### Validate Corpus & Print Summary Report

```bash
python main.py --validate
```

---

## 3. Architecture & Download Strategies

### Strategy A (2020–2026) — Explore Education Statistics (EES)
- Discovers GOV.UK annual publication page redirecting to the EES platform (`explore-education-statistics.service.gov.uk`).
- Parses EES landing pages and API definitions to locate official **"Download all (ZIP)"** archives.
- Passes appropriate `Referer` headers to obtain complete streamable ZIP files.
- Preserves raw ZIPs and extracts all underlying CSV datasets with clean year prefixes (`SEN_{year}_EXT_{name}.csv`).

### Strategy B (2010–2019) — GOV.UK Direct Documents
- Parses GOV.UK publication pages dynamically.
- Identifies main text PDFs, national Excel workbooks, local authority tables, additional tables, technical documents, and underlying data ZIPs.
- Sanitizes file names to standard machine-readable formats (`SEN_{year}_Main_Text.pdf`, `SEN_{year}_National_Tables.xlsx`, etc.).

---

## 4. Directory Structure

```
C:\Users\Reddy\Documents\SEN\
│
├── sen_downloader/
│   ├── __init__.py
│   ├── config.py
│   ├── logger.py
│   ├── discovery.py
│   ├── govuk.py
│   ├── ees.py
│   ├── downloader.py
│   ├── extractor.py
│   ├── metadata.py
│   ├── validator.py
│   └── cli.py
│
├── main.py
├── requirements.txt
├── README.md
│
└── sen_data/
    ├── raw/
    │   ├── 2010/ ... 2026/
    ├── extracted/
    │   ├── 2010/ ... 2026/
    ├── metadata/
    │   ├── document_metadata.csv
    │   ├── file_metadata.csv
    │   ├── download_log.csv
    │   └── failed_downloads.csv
    ├── logs/
    │   └── downloader.log
    └── manifests/
        ├── manifest_2010.json ... manifest_2026.json
        └── corpus_manifest.json
```

---

## 5. Resumability & Fault Tolerance

- **Atomic File Writing**: Files are downloaded first to `.part` files (`filename.part`). Renamed to `filename` only after HTTP 200 verification and magic byte validation (%PDF, ZIP headers).
- **Checksum Verification**: Calculates SHA256 hashes for every raw and extracted file.
- **Skip Existing Valid Files**: Re-executing the script skips existing valid downloads (`SKIPPED_ALREADY_EXISTS`).
- **Retry Logic**: Implements 5 retries with exponential backoff (2^attempt seconds) to handle network interruptions or temporary server limits.
- **Corrupt Prevention**: Rejects HTML error pages accidentally saved with `.pdf` or `.zip` extensions.

---

## 6. Official Data Sources

- **GOV.UK SEN Collection Page**: https://www.gov.uk/government/collections/statistics-special-educational-needs-sen
- **Explore Education Statistics (EES)**: https://explore-education-statistics.service.gov.uk/
