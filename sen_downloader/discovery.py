import re
from typing import Dict, List
import requests
from bs4 import BeautifulSoup

from .config import MAIN_COLLECTION_URL, DEFAULT_HEADERS, CONNECT_TIMEOUT, READ_TIMEOUT, TARGET_YEARS
from .logger import logger

def discover_publication_years() -> Dict[int, str]:
    """
    Parses the main GOV.UK SEN collection page to discover all annual
    'Special educational needs in England' publication URLs from 2010 through 2026.

    Returns:
        Dict[int, str]: Mapping from publication_year (e.g. 2026) to GOV.UK publication page URL.
    """
    logger.info(f"Fetching main GOV.UK SEN collection page: {MAIN_COLLECTION_URL}")
    years_map: Dict[int, str] = {}

    try:
        response = requests.get(
            MAIN_COLLECTION_URL,
            headers=DEFAULT_HEADERS,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Find all publication links
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            title = a.get_text(strip=True)

            # Match patterns like /government/statistics/special-educational-needs-in-england-january-2024
            if "special-educational-needs-in-england" in href:
                year_match = re.search(r"20\d{2}", href) or re.search(r"20\d{2}", title)
                if year_match:
                    year = int(year_match.group(0))
                    full_url = href if href.startswith("http") else f"https://www.gov.uk{href}"
                    if year not in years_map:
                        years_map[year] = full_url
                        logger.info(f"Discovered publication for year {year}: {full_url}")

    except Exception as e:
        logger.error(f"Error fetching main collection page: {e}")

    # Verify and construct fallbacks for missing target years
    for yr in TARGET_YEARS:
        if yr not in years_map:
            fallback_url = f"https://www.gov.uk/government/statistics/special-educational-needs-in-england-january-{yr}"
            years_map[yr] = fallback_url
            logger.warning(f"Year {yr} not found on collection page; using candidate fallback URL: {fallback_url}")

    return years_map
