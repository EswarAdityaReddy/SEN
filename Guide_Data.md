# Build a Robust SEN Data Downloader for GOV.UK and Explore Education Statistics

You are an expert Python data-engineering developer. Build a **production-quality, fault-tolerant Python downloader** for my SEN Vector RAG project.

The goal is to automatically collect the official UK Department for Education **"Special educational needs in England"** resources from **2010 through 2026**, while preserving the original source information and creating clean metadata.

## 1. OFFICIAL SOURCE WEBSITES

Use ONLY official UK government sources.

Main collection:

https://www.gov.uk/government/collections/statistics-special-educational-needs-sen

The collection contains the annual:

"Special educational needs in England: January YYYY"

publications.

Do NOT use Google search results, third-party websites, Kaggle, GitHub mirrors, or scraped copies when an official GOV.UK/EES source exists.

The current GOV.UK collection lists annual SEN publications from 2010 through 2026.

---

# 2. IMPORTANT WEBSITE STRUCTURE

The website changed around 2020, so DO NOT assume every year has the same download structure.

Implement two different download strategies.

## STRATEGY A — 2020 AND LATER

For 2020–2026, first open the corresponding GOV.UK publication page.

Example:

https://www.gov.uk/government/statistics/special-educational-needs-in-england-january-2026

The GOV.UK page can redirect/reference the Explore Education Statistics platform.

For example, the 2026 publication points to:

https://explore-education-statistics.service.gov.uk/find-statistics/special-educational-needs-in-england/2025-26

For the relevant publication, locate its EES "Explore and download data" page.

Example:

https://explore-education-statistics.service.gov.uk/find-statistics/special-educational-needs-in-england/2025-26/explore

On the EES page:

1. Identify all available datasets.
2. Locate the official **"Download all (ZIP)"** option if available.
3. Download the ZIP.
4. Save the original ZIP.
5. Extract the ZIP into a year-specific directory.
6. Preserve every CSV/data file contained in the ZIP.
7. Do not randomly select only one CSV.
8. Record the original dataset name and source URL in metadata.

The EES page can contain multiple datasets, so the downloader must handle all datasets rather than assuming there is only one file.

---

# 3. STRATEGY B — BELOW 2020

For years before 2020, use the GOV.UK publication page directly.

Examples:

2018:

https://www.gov.uk/government/statistics/special-educational-needs-in-england-january-2018

2019:

https://www.gov.uk/government/statistics/special-educational-needs-in-england-january-2019

The publication page contains a "Documents" section.

For example, the 2018 publication contains:

* Main text PDF
* National tables Excel
* Local authority tables Excel
* Additional tables Excel
* Technical document PDF
* Underlying data ZIP
* Pre-release access list HTML

Download the relevant data/document resources from the Documents section.

DO NOT assume that every year has exactly the same document names or file types.

The program must inspect the actual page and discover the available documents dynamically.

---

# 4. YEARS TO DOWNLOAD

The target annual corpus is:

2010
2011
2012
2013
2014
2015
2016
2017
2018
2019
2020
2021
2022
2023
2024
2025
2026

Do not silently skip a year.

If a year cannot be downloaded, record it in an error report and continue with the remaining years.

At the end, clearly report:

SUCCESSFUL YEARS
FAILED YEARS
PARTIAL YEARS
MISSING FILES

---

# 5. DO NOT HARD-CODE FILE URLs

This is extremely important.

Do NOT assume that the direct PDF/ZIP/Excel URL follows a predictable pattern.

Instead:

1. Request the publication page.
2. Parse the page.
3. Identify the Documents section.
4. Extract actual document links.
5. Download those links.

Similarly, for EES:

1. Open the correct publication page.
2. Navigate to the Explore/download page.
3. Detect available datasets/download links.
4. Download using the discovered URLs.

The website structure may change, so use page inspection rather than constructing URLs blindly.

---

# 6. FILE TYPES

The downloader must support at least:

.pdf
.csv
.txt
.xlsx
.xls
.zip
.html
.json

For ZIP files:

1. Download the ZIP.
2. Preserve the original ZIP.
3. Extract it.
4. Recursively inspect extracted files.
5. Preserve CSV/TXT/XLSX/etc.
6. Record the relationship between the ZIP and extracted files.

Do not delete the original ZIP.

---

# 7. DIRECTORY STRUCTURE

Create this directory:

sen_data/

```
raw/

    2010/

    2011/

    2012/

    2013/

    2014/

    2015/

    2016/

    2017/

    2018/

    2019/

    2020/

    2021/

    2022/

    2023/

    2024/

    2025/

    2026/

extracted/

    2010/

    2011/

    ...

    2026/

metadata/

    document_metadata.csv

    file_metadata.csv

    download_log.csv

    failed_downloads.csv

logs/

    downloader.log

manifests/

    manifest_2010.json

    manifest_2011.json

    ...

    manifest_2026.json
```

Do not mix files from different years.

---

# 8. EXACT FILE NAMING

Use clean, consistent, machine-readable filenames.

Never use random browser-generated filenames.

For annual report documents use:

SEN_2010_Main_Text.pdf
SEN_2010_National_Tables.xlsx
SEN_2010_Local_Authority_Tables.xlsx
SEN_2010_Additional_Tables.xlsx
SEN_2010_Technical_Document.pdf
SEN_2010_Underlying_Data.zip

For 2018:

SEN_2018_Main_Text.pdf
SEN_2018_National_Tables.xlsx
SEN_2018_Local_Authority_Tables.xlsx
SEN_2018_Additional_Tables.xlsx
SEN_2018_Technical_Document.pdf
SEN_2018_Underlying_Data.zip

For 2026 EES datasets, preserve the dataset identity:

SEN_2026_<DATASET_NAME>.csv

or, if the downloaded resource is itself a ZIP:

SEN_2026_EES_All_Datasets.zip

Extracted files should retain a clear year prefix:

SEN_2026_<DATASET_NAME>_<ORIGINAL_FILE_NAME>.csv

Do not create names such as:

download.csv
file1.csv
data.csv
final.csv
new.csv
new_final.csv

---

# 9. FILE NAME SANITIZATION

Create a filename sanitizer.

Rules:

* Replace spaces with underscores.
* Remove unsafe filesystem characters.
* Preserve meaningful words.
* Keep year.
* Keep document/dataset identity.
* Keep original extension.
* Do not create duplicate filenames.

Example:

"Special educational needs in England - January 2018: national tables"

becomes approximately:

SEN_2018_National_Tables.xlsx

If two files would receive the same sanitized name, append a deterministic suffix rather than overwriting:

SEN_2018_National_Tables_01.xlsx
SEN_2018_National_Tables_02.xlsx

---

# 10. METADATA IS CRITICAL

Create a complete metadata database.

At minimum:

document_id
year
title
publisher
publication_date
document_type
resource_type
filename
original_filename
source_url
publication_url
download_url
file_extension
file_size_bytes
sha256
download_status
download_timestamp

For EES datasets additionally capture:

dataset_name
dataset_id
dataset_description
number_of_rows_if_available
number_of_columns_if_available
ees_publication
ees_version

Do not lose the original URL.

---

# 11. CREATE document_metadata.csv

Example:

document_id,year,title,publisher,publication_date,document_type,filename,source_url,download_url,file_type,status

Example record:

SEN_2018_MAIN,2018,Special educational needs in England - January 2018,Department for Education,2018-07-26,Main Text,SEN_2018_Main_Text.pdf,<publication URL>,<download URL>,pdf,success

Create one row per downloaded source file.

---

# 12. CREATE file_metadata.csv

This should describe every physical file.

Include:

file_id
year
document_id
filename
relative_path
file_type
file_size_bytes
sha256
source_url
download_url
parent_archive
extraction_status

This will allow the RAG pipeline to trace:

chunk → file → original URL → publication → year.

---

# 13. CREATE DOWNLOAD LOGGING

The downloader MUST be resumable.

If the script stops halfway through 2024, running it again should NOT start everything from zero.

For every file record:

STARTED
DOWNLOADING
DOWNLOADED
VALIDATED
EXTRACTED
FAILED
SKIPPED_ALREADY_EXISTS

Use Python logging.

Write logs to:

sen_data/logs/downloader.log

Also create:

sen_data/metadata/download_log.csv

---

# 14. HANDLE DOWNLOAD FAILURES

This is extremely important.

Sometimes GOV.UK/EES downloads may:

* timeout
* return 403/429/5xx
* temporarily fail
* return an HTML error page instead of the expected file
* disconnect
* produce an incomplete ZIP
* fail during extraction
* take a long time to respond

The downloader must handle these safely.

Implement:

* connection timeout
* read timeout
* retry logic
* exponential backoff
* multiple retry attempts
* HTTP status checking
* Content-Type validation
* file-size validation
* checksum calculation
* ZIP integrity checking

Example retry pattern:

Attempt 1
wait
Attempt 2
wait longer
Attempt 3
wait longer
Attempt 4
wait longer
Attempt 5

Do not immediately give up.

---

# 15. PREVENT CORRUPT DOWNLOADS

Never write directly to the final filename.

Download first to:

filename.part

Only rename:

filename.part → filename

after successful validation.

This prevents incomplete files from appearing as successful downloads.

For ZIP files:

1. Download .part
2. Verify it is actually a ZIP
3. Run ZIP integrity check
4. Extract
5. Only then mark it as successful

If validation fails, delete the incomplete .part file and retry.

---

# 16. PREVENT HTML ERROR PAGES FROM BEING SAVED AS PDF/ZIP

Before accepting a download, check:

HTTP status
Content-Type
Content-Length if available
file signature/magic bytes
extension consistency

Examples:

PDF should normally begin with:

%PDF

ZIP should normally have a ZIP signature.

Do not accept:

<html>
<!DOCTYPE html>

as a successful PDF/ZIP download.

---

# 17. HANDLE LARGE FILES

Do not load huge ZIP/CSV files entirely into memory during downloading.

Use streaming downloads:

response.iter_content(...)

Write chunks incrementally.

Show progress:

Downloading:
SEN_2026_EES_All_Datasets.zip
Downloaded: 37 MB / 84 MB
Progress: 44%

Do not use a tiny read timeout that causes large downloads to fail.

---

# 18. HANDLE EES DOWNLOADS CAREFULLY

For EES pages, do not assume the ZIP link is always a normal static href.

The page may contain dynamically generated content.

Implement fallback strategies:

1. Parse normal HTML links.
2. Search for visible "Download all" links.
3. Inspect relevant page elements.
4. If necessary, use a browser automation fallback such as Playwright.
5. Save the discovered final download URL.
6. Download it using the robust streaming downloader.

Do NOT use browser automation for every download if normal HTTP requests are sufficient.

Use browser automation only when necessary.

---

# 19. IMPORTANT: YEAR MAPPING

Do not assume the EES URL's year is the publication year.

For example:

2026 publication:

GOV.UK:
Special educational needs in England: January 2026

EES:
2025-26

Therefore explicitly maintain:

publication_year = 2026
academic_year = 2025-26

Never accidentally label the 2026 publication as 2025.

Store both fields where applicable:

publication_year
academic_year

---

# 20. DISCOVER YEARS DYNAMICALLY

First parse the main collection page.

Find all annual:

Special educational needs in England: January YYYY

publication links.

Build a table:

year
publication_title
publication_url

Then process each year.

Do NOT hard-code only 2020–2026 URLs.

The 2010–2026 list should be discovered from the official collection page, while also checking that all expected years are present.

Expected years:

2010–2026 inclusive.

If a year is missing from the collection, flag it.

---

# 21. PREVENT DUPLICATES

Before downloading:

1. Check source URL.
2. Check existing metadata.
3. Check filename.
4. Check SHA256 if available.

If the same resource already exists:

SKIPPED_ALREADY_EXISTS

Do not download it again unnecessarily.

---

# 22. VALIDATE THE FINAL CORPUS

After processing all years, generate a final report:

Total expected years: 17

Years successfully processed:
2010
2011
...
2026

Years failed:
...

Total publication pages found:
...

Total files discovered:
...

Total files downloaded:
...

Total files extracted:
...

Total failed:
...

Total skipped:
...

Total size:
...

Also generate:

corpus_manifest.json

containing all files and their metadata.

---

# 23. DO NOT STOP THE WHOLE SCRIPT BECAUSE ONE FILE FAILS

This is critical.

Bad behavior:

2018 file fails → program crashes → nothing after 2018 downloads.

Correct behavior:

2018 file fails → log failure → continue → 2019 → 2020 → ... → 2026.

At the end, retry failed files separately.

---

# 24. AUTOMATIC RETRY OF FAILED FILES

Implement:

python downloader.py --retry-failed

This should read:

metadata/failed_downloads.csv

and retry only failed resources.

Also support:

python downloader.py --year 2026

python downloader.py --year 2018

python downloader.py --all

python downloader.py --validate

python downloader.py --retry-failed

---

# 25. DO NOT SILENTLY IGNORE MISSING DATA

If a resource exists on the official publication page but could not be downloaded:

mark:

status = failed

and record:

error_type
http_status
error_message
attempts
source_url

Do not pretend the corpus is complete.

---

# 26. DATA SCOPE

The primary corpus is:

"Special educational needs in England"

annual statistics from 2010–2026.

Do not automatically download unrelated resources from the SEN collection such as:

* EHC plans
* absence analysis
* exclusions
* unrelated SEN research

unless explicitly requested.

For this downloader, focus on the annual SEN-in-England statistical publications.

---

# 27. KEEP RAW DATA UNMODIFIED

Never modify the original downloaded files.

Raw files must remain exactly as downloaded.

Any transformation should happen under:

sen_data/extracted/

or later:

sen_data/processed/

This is essential for reproducibility.

---

# 28. PREPARE FOR RAG

The downloader is only the data-ingestion stage.

Do NOT yet create embeddings or FAISS.

First produce a clean corpus with traceable metadata.

The eventual pipeline will be:

Official GOV.UK/EES resources
↓
Downloader
↓
Raw files
↓
Extraction
↓
Normalized documents
↓
Metadata
↓
Chunking
↓
Embeddings
↓
FAISS
↓
Temporal retrieval
↓
LLM
↓
Trust verification

Every chunk must eventually be traceable back to:

year
publication
file
page/sheet/row where applicable
source URL

---

# 29. EXPECTED FINAL OUTPUT

The program must produce:

sen_data/
│
├── raw/
├── extracted/
├── metadata/
│   ├── document_metadata.csv
│   ├── file_metadata.csv
│   ├── download_log.csv
│   └── failed_downloads.csv
│
├── logs/
│   └── downloader.log
│
└── manifests/
├── manifest_2010.json
├── ...
└── manifest_2026.json

Also print a final summary such as:

==================================================
SEN DATA DOWNLOAD COMPLETE
==========================

Years requested: 2010–2026
Years completed: 17/17

Files discovered: XXX
Files downloaded: XXX
Files skipped: XXX
Files failed: XXX

PDF: XXX
XLSX: XXX
CSV: XXX
TXT: XXX
ZIP: XXX
HTML: XXX

Total downloaded size: XXX MB

Failed resources:
...

Run --retry-failed to retry failed downloads.

==================================================

# 30. CODE QUALITY REQUIREMENTS

Use:

Python 3.10+

requests/httpx for HTTP downloads
BeautifulSoup for HTML parsing
pandas for metadata
pathlib for filesystem operations
hashlib for SHA256
zipfile for ZIP validation/extraction
logging for logs
argparse for command-line options

Use type hints.

Use functions/classes rather than one giant script.

Suggested modules:

sen_downloader/
**init**.py
config.py
discovery.py
govuk.py
ees.py
downloader.py
extractor.py
metadata.py
validator.py
logger.py
cli.py

main.py

requirements.txt

README.md

---

# 31. README REQUIREMENTS

Create a complete README explaining:

1. Installation
2. Python version
3. Dependencies
4. How to run
5. How to download all years
6. How to download one year
7. How to retry failures
8. How to validate
9. Directory structure
10. Metadata schema
11. GOV.UK source
12. EES source
13. Troubleshooting
14. How resumability works

---

# 32. MOST IMPORTANT RULE

Before considering the project complete, test it.

Test at minimum:

* one recent EES year
* one older GOV.UK year
* one PDF
* one Excel file
* one ZIP
* one CSV inside a ZIP
* one failed/retried download
* running the program twice
* interrupted download/resume

Do not just provide code that looks correct.

Actually run the downloader and verify the downloaded files.

If something fails because the website structure is different from the assumptions above, inspect the live official page and adapt the scraper rather than hard-coding a workaround.

The final solution must be **robust, resumable, reproducible, and suitable as the data-ingestion component of a B.Tech final-year Vector RAG project.**
