"""
serper_client.py
----------------
Plain-English job of this file:
  Talk to Serper.dev (a paid-but-cheap Google Search API) to:
    1. Find a company's official website if the user only typed a name.
    2. Do a general search for extra info about the company.
    3. Look up a competitor's website once the AI has named the competitor.

Get a free Serper.dev API key at https://serper.dev (they give free credits).
"""

import requests
import os

SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "a9801feb7b30f53028dbcd5ccb0aa3a79c8fd8d2")
SERPER_URL = "https://google.serper.dev/search"

BLOCKED_DOMAINS = ["wikipedia.org", "linkedin.com", "facebook.com", "twitter.com",
                    "instagram.com", "youtube.com", "crunchbase.com", "glassdoor.com"]


def serper_search(query: str, num_results: int = 5) -> list:
    """
    Calls Serper.dev and returns a clean list of:
      {"title": ..., "link": ..., "snippet": ...}
    """
    if not SERPER_API_KEY or SERPER_API_KEY == "PASTE_YOUR_SERPER_KEY_HERE":
        return []

    try:
        resp = requests.post(
            SERPER_URL,
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": query, "num": num_results},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        results = []
        for item in data.get("organic", [])[:num_results]:
            results.append({
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
            })
        return results
    except Exception as e:
        print(f"[serper_search] failed: {e}")
        return []


def find_official_website(company_name: str) -> str:
    """Given just a company name, find the most likely official website."""
    results = serper_search(f"{company_name} official website", num_results=5)
    for r in results:
        link = r["link"].lower()
        if not any(bad in link for bad in BLOCKED_DOMAINS):
            return r["link"]
    return ""


def find_competitor_website(competitor_name: str) -> str:
    """Given a competitor's name (from the AI), find their website."""
    results = serper_search(f"{competitor_name} official website", num_results=3)
    for r in results:
        link = r["link"].lower()
        if not any(bad in link for bad in BLOCKED_DOMAINS):
            return r["link"]
    return ""


def general_company_search(company_label: str) -> list:
    """General search used to enrich AI context (overview, phone, address, competitors)."""
    return serper_search(f"{company_label} company overview contact address", num_results=5)
