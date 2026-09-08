import re
import json
from typing import Dict, List, Any, Optional
import requests
from bs4 import BeautifulSoup

from .config import DEFAULT_HEADERS, CONNECT_TIMEOUT, READ_TIMEOUT
from .logger import logger

def parse_ees_publication_page(year: int, ees_url: str) -> Dict[str, Any]:
    """
    Parses an Explore Education Statistics (EES) publication page (Strategy A).

    Args:
        year (int): Publication year (e.g. 2026).
        ees_url (str): EES landing page URL.

    Returns:
        Dict[str, Any]: Strategy result containing list of discovered documents.
    """
    logger.info(f"Parsing EES page for year {year}: {ees_url}")

    academic_year = f"{year-1}-{str(year)[2:]}"  # Default mapping e.g. 2026 -> 2025-26

    # Extract academic year from URL if explicit
    slug_match = re.search(r"20\d{2}-\d{2}", ees_url)
    if slug_match:
        academic_year = slug_match.group(0)

    result = {
        "strategy": "EES",
        "academic_year": academic_year,
        "documents": []
    }

    try:
        headers = DEFAULT_HEADERS.copy()
        headers["Referer"] = ees_url

        response = requests.get(
            ees_url,
            headers=headers,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)
        )

        if response.status_code != 200:
            logger.error(f"EES page returned HTTP {response.status_code} for {ees_url}")
            return result

        soup = BeautifulSoup(response.text, "html.parser")
        download_all_url = None

        # 1. Inspect links in HTML for 'Download all data (ZIP)'
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            text = a.get_text(strip=True)
            if "api/releases/" in href and "files" in href:
                download_all_url = href if href.startswith("http") else f"https://content.explore-education-statistics.service.gov.uk{href}"
                logger.info(f"Discovered EES 'Download all' link from HTML for {year}: {download_all_url}")
                break

        # 2. Inspect __NEXT_DATA__ if HTML parsing didn't find direct link
        if not download_all_url:
            script = soup.find("script", id="__NEXT_DATA__")
            if script and script.string:
                try:
                    next_data = json.loads(script.string)
                    props = next_data.get("props", {}).get("pageProps", {})
                    rel_summary = props.get("releaseVersionSummary", {})
                    release_id = rel_summary.get("id") or rel_summary.get("releaseId")
                    if release_id:
                        download_all_url = f"https://content.explore-education-statistics.service.gov.uk/api/releases/{release_id}/files?fromPage=ReleaseDownloads"
                        logger.info(f"Constructed EES 'Download all' link from NEXT_DATA for {year}: {download_all_url}")
                except Exception as ex:
                    logger.debug(f"Error parsing NEXT_DATA for EES: {ex}")

        # Construct primary ZIP document record
        if download_all_url:
            filename = f"SEN_{year}_EES_All_Datasets.zip"
            doc = {
                "document_id": f"SEN_{year}_EES_ALL",
                "year": year,
                "academic_year": academic_year,
                "title": f"Special Educational Needs in England ({academic_year}) - All Datasets",
                "publisher": "Department for Education (EES)",
                "publication_date": f"{year}-06-01",
                "document_type": "Underlying_Data_ZIP",
                "filename": filename,
                "source_url": ees_url,
                "download_url": download_all_url,
                "referer": ees_url,
                "file_extension": ".zip",
            }
            result["documents"].append(doc)
        else:
            logger.warning(f"Could not find EES Download All URL for year {year} at {ees_url}")

    except Exception as e:
        logger.error(f"Error parsing EES publication page for {year}: {e}")

    return result
