import re
from typing import Dict, List, Any, Optional
import requests
from bs4 import BeautifulSoup

from .config import DEFAULT_HEADERS, CONNECT_TIMEOUT, READ_TIMEOUT, SUPPORTED_EXTENSIONS
from .logger import logger

def sanitize_govuk_filename(year: int, title: str, download_url: str) -> str:
    """
    Sanitizes title into a clean, machine-readable filename per specification (Section 8 & 9).
    Example: 'Special educational needs in England - January 2018: national tables'
             -> 'SEN_2018_National_Tables.xlsx'
    """
    # Extract extension from URL
    ext = ""
    for e in SUPPORTED_EXTENSIONS:
        if download_url.lower().endswith(e) or f"{e}?" in download_url.lower():
            ext = e
            break
    if not ext:
        if "." in download_url.rsplit("/", 1)[-1]:
            ext = "." + download_url.rsplit("/", 1)[-1].split(".", 1)[-1].split("?")[0]
        else:
            ext = ".pdf"

    clean_title = title.lower()
    
    # Remove standard prefix phrases
    clean_title = re.sub(r"special\s+educational\s+needs\s+in\s+england\s*[-:]?\s*", "", clean_title)
    clean_title = re.sub(r"january\s+\d{4}\s*[-:]?\s*", "", clean_title)
    clean_title = re.sub(r"statements\s+of\s+sen\s+and\s+ehc\s+plans\s*[-:]?\s*", "", clean_title)

    # Standard category mapping
    if "main text" in clean_title or "national headline text" in clean_title or "main report" in clean_title or clean_title.strip() == "pdf":
        doc_type = "Main_Text"
    elif "national table" in clean_title:
        doc_type = "National_Tables"
    elif "local authority table" in clean_title or "la table" in clean_title:
        doc_type = "Local_Authority_Tables"
    elif "additional table" in clean_title:
        doc_type = "Additional_Tables"
    elif "technical document" in clean_title or "methodology" in clean_title or "technical" in clean_title:
        doc_type = "Technical_Document"
    elif "underlying data" in clean_title or "data" in clean_title or "csv" in clean_title:
        doc_type = "Underlying_Data"
    else:
        # Fallback to sanitized title words
        words = re.sub(r"[^a-zA-Z0-9\s]", "", clean_title).split()
        words = [w.capitalize() for w in words if w]
        doc_type = "_".join(words[:4]) if words else "Document"

    filename = f"SEN_{year}_{doc_type}{ext}"
    return filename


def parse_govuk_publication_page(year: int, publication_url: str) -> Dict[str, Any]:
    """
    Parses a GOV.UK publication page.
    Checks if redirected/linked to EES platform, or extracts GOV.UK document attachments.

    Returns:
        Dict[str, Any]: {
            'strategy': 'EES' or 'GOVUK',
            'ees_url': Optional[str],
            'documents': List[Dict[str, Any]]
        }
    """
    logger.info(f"Parsing GOV.UK publication page for year {year}: {publication_url}")
    result = {
        "strategy": "GOVUK",
        "ees_url": None,
        "documents": []
    }

    try:
        response = requests.get(
            publication_url,
            headers=DEFAULT_HEADERS,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)
        )
        if response.status_code != 200:
            logger.error(f"GOV.UK publication page returned status {response.status_code} for {publication_url}")
            return result

        soup = BeautifulSoup(response.text, "html.parser")

        # 1. Check for EES link/redirect
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if "explore-education-statistics.service.gov.uk/find-statistics/" in href:
                result["strategy"] = "EES"
                result["ees_url"] = href
                logger.info(f"Year {year} links to EES platform: {href}")
                return result

        # 2. Extract documents from GOV.UK page (Strategy B)
        seen_urls = set()
        seen_filenames = {}

        # Look for attachments in document sections or general link tags
        attachments = soup.find_all("section", class_=re.compile(r"attachment|document"))
        if not attachments:
            attachments = [soup]

        for container in attachments:
            for a in container.find_all("a", href=True):
                href = a["href"].strip()
                title = a.get_text(strip=True)
                full_url = href if href.startswith("http") else f"https://www.gov.uk{href}"

                # Check if file has target extension or comes from assets.publishing.service.gov.uk
                is_doc_url = any(full_url.lower().endswith(ext) or f"{ext}?" in full_url.lower() for ext in SUPPORTED_EXTENSIONS)
                is_asset_url = "assets.publishing.service.gov.uk" in full_url

                if (is_doc_url or is_asset_url) and full_url not in seen_urls:
                    seen_urls.add(full_url)
                    base_filename = sanitize_govuk_filename(year, title, full_url)

                    # Deduplicate filenames with suffix
                    if base_filename in seen_filenames:
                        seen_filenames[base_filename] += 1
                        name, ext = base_filename.rsplit(".", 1)
                        final_filename = f"{name}_{seen_filenames[base_filename]:02d}.{ext}"
                    else:
                        seen_filenames[base_filename] = 1
                        final_filename = base_filename

                    doc = {
                        "document_id": f"SEN_{year}_{len(result['documents'])+1:03d}",
                        "year": year,
                        "title": title or final_filename,
                        "publisher": "Department for Education",
                        "publication_date": f"{year}-01-01",
                        "document_type": final_filename.split("_", 2)[-1].rsplit(".", 1)[0],
                        "filename": final_filename,
                        "source_url": publication_url,
                        "download_url": full_url,
                        "file_extension": "." + final_filename.rsplit(".", 1)[-1],
                    }
                    result["documents"].append(doc)
                    logger.info(f"Discovered GOV.UK document for {year}: {final_filename} -> {full_url}")

    except Exception as e:
        logger.error(f"Error parsing GOV.UK publication page for {year}: {e}")

    return result
