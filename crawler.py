"""
crawler.py
----------
Plain-English job of this file:
  Visit a company's website and pull text from the pages that actually
  matter: Home, About, Products, Services, Solutions, Contact, Pricing.
  Skip login pages, duplicate pages, and junk (cookie banners, scripts, ads).

  Also pulls out a phone number and address with simple pattern matching,
  since those are often in the footer or contact page rather than
  something an AI needs to "guess."
"""

import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse

HEADERS = {"User-Agent": "Mozilla/5.0 (research-assistant-bot)"}

# Which inner pages we actively look for, and keywords that identify them
PAGE_KEYWORDS = {
    "about": ["about", "who-we-are", "our-story", "company"],
    "products": ["product", "solutions", "platform"],
    "services": ["service"],
    "pricing": ["pricing", "plans"],
    "contact": ["contact", "reach-us", "get-in-touch"],
}

# Pages we deliberately ignore
SKIP_KEYWORDS = ["login", "signin", "sign-in", "signup", "sign-up", "register",
                  "account", "cart", "checkout", "privacy", "terms", "cookie-policy"]

JUNK_CLASS_KEYWORDS = ["cookie", "consent", "popup", "banner", "advert", "subscribe", "newsletter", "modal"]


def clean_soup_text(soup: BeautifulSoup, max_chars: int = 1200) -> str:
    """Strips scripts/nav/footer/junk and returns clean visible text."""
    for tag in soup(["script", "style", "nav", "footer", "noscript", "form", "iframe", "svg"]):
        tag.decompose()

    for tag in soup.find_all(attrs={"class": True}):
        classes = " ".join(tag.get("class", [])).lower()
        if any(k in classes for k in JUNK_CLASS_KEYWORDS):
            tag.decompose()

    text = re.sub(r"\s+", " ", soup.get_text(separator=" ")).strip()
    return text[:max_chars]


def extract_contact_details(full_text: str) -> dict:
    """Simple regex-based phone number and address hints from raw page text."""
    phone_match = re.search(r"(\+?\d[\d\s\-\(\)]{8,15}\d)", full_text)
    # Very rough address hint: look for common address-like patterns (street/road/avenue + number)
    address_match = re.search(
        r"\d{1,5}\s+[A-Za-z0-9.,\s]{5,60}(Street|St\.|Road|Rd\.|Avenue|Ave\.|Boulevard|Blvd\.|Lane|Drive|Building|Floor|Suite)",
        full_text, re.IGNORECASE
    )
    return {
        "phone": phone_match.group(0).strip() if phone_match else "",
        "address": address_match.group(0).strip() if address_match else "",
    }


def discover_pages(base_url: str, homepage_soup: BeautifulSoup, max_pages: int = 5) -> dict:
    """
    Looks at homepage links, matches them against PAGE_KEYWORDS,
    skips login/duplicate/irrelevant pages, and returns
    {page_type: full_url} for the ones it found.
    """
    found = {}
    seen_urls = set()
    parsed_base = urlparse(base_url)

    for a in homepage_soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
            continue

        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)

        # stay on the same domain only
        if parsed.netloc != parsed_base.netloc:
            continue

        normalized = full_url.split("#")[0].rstrip("/")
        if normalized in seen_urls:
            continue  # duplicate

        href_lower = href.lower()
        if any(skip in href_lower for skip in SKIP_KEYWORDS):
            continue  # login/cart/etc - irrelevant to research

        for page_type, keywords in PAGE_KEYWORDS.items():
            if page_type in found:
                continue
            if any(kw in href_lower for kw in keywords):
                found[page_type] = normalized
                seen_urls.add(normalized)
                break

        if len(found) >= max_pages:
            break

    return found


def crawl_company_site(base_url: str) -> dict:
    """
    Main entry point. Returns:
      {
        "pages": {"home": "...text...", "about": "...text...", ...},
        "phone": "...",
        "address": "...",
        "combined_text": "...",  # everything joined, capped in size
      }
    """
    pages_text = {}
    full_text_for_contact_search = ""

    try:
        resp = requests.get(base_url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        homepage_soup = BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        return {"pages": {}, "phone": "", "address": "", "combined_text": f"[Could not reach {base_url}: {e}]"}

    pages_text["home"] = clean_soup_text(homepage_soup, max_chars=1200)
    full_text_for_contact_search += pages_text["home"]

    discovered = discover_pages(base_url, homepage_soup)

    for page_type, url in discovered.items():
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            text = clean_soup_text(soup, max_chars=800)
            pages_text[page_type] = text
            full_text_for_contact_search += " " + text
        except Exception:
            continue  # skip pages that fail rather than crash the whole crawl

    contact_info = extract_contact_details(full_text_for_contact_search)

    combined_text = ""
    for page_type, text in pages_text.items():
        combined_text += f"[{page_type.upper()} PAGE]: {text}\n\n"

    return {
        "pages": pages_text,
        "phone": contact_info["phone"],
        "address": contact_info["address"],
        "combined_text": combined_text[:3500],  # keep total prompt size small for AI token limits
    }
