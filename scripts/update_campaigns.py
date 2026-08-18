#!/usr/bin/env python3
"""Update campagne.json by scraping free environmental campaign sources."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
TARGET_FILE = ROOT / "campagne.json"
TIMEOUT = 20
MAX_PER_SOURCE = 20
HEADERS = {
    "User-Agent": "GreenAnchorBot/1.0 (+https://github.com/gcasaldi/GreenAnchor)"
}


@dataclass
class SourceConfig:
    name: str
    organization: str
    list_url: str
    allowed_domains: tuple[str, ...]
    include_patterns: tuple[str, ...]
    tags: tuple[str, ...]
    language: str
    country: str


SOURCES = [
    SourceConfig(
        name="Iniziativa dei Cittadini Europei",
        organization="Commissione Europea (ICE)",
        list_url="https://citizens-initiative.europa.eu/find-initiative_en",
        allowed_domains=("citizens-initiative.europa.eu",),
        include_patterns=("initiative", "initiatives", "details"),
        tags=("UE", "legislazione", "partecipazione civica"),
        language="en",
        country="EU",
    ),
    SourceConfig(
        name="Avaaz",
        organization="Avaaz",
        list_url="https://secure.avaaz.org/campaign/en/",
        allowed_domains=("secure.avaaz.org", "avaaz.org"),
        include_patterns=("campaign", "petition", "act"),
        tags=("mobilitazione", "pressione politica", "globale"),
        language="en",
        country="Global",
    ),
    SourceConfig(
        name="Greenpeace",
        organization="Greenpeace",
        list_url="https://www.greenpeace.org/international/act/",
        allowed_domains=("greenpeace.org",),
        include_patterns=("act", "petition", "campaign"),
        tags=("attivati", "ambiente", "azioni legali"),
        language="en",
        country="Global",
    ),
    SourceConfig(
        name="WWF",
        organization="WWF",
        list_url="https://wwf.panda.org/act/",
        allowed_domains=("wwf.panda.org", "wwf.eu", "worldwildlife.org"),
        include_patterns=("act", "petition", "campaign", "take-action"),
        tags=("attivati", "biodiversita", "clima"),
        language="en",
        country="Global",
    ),
    SourceConfig(
        name="openPetition",
        organization="openPetition",
        list_url="https://www.openpetition.eu/it/petitions",
        allowed_domains=("openpetition.eu",),
        include_patterns=("petitions", "petition", "/it/"),
        tags=("no-profit", "trasparenza", "petizioni"),
        language="it",
        country="EU",
    ),
]


def fetch_html(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    return response.text


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def is_allowed_link(config: SourceConfig, href: str) -> bool:
    absolute = urljoin(config.list_url, href)
    parsed = urlparse(absolute)
    if parsed.scheme not in {"http", "https"}:
        return False
    if not any(parsed.netloc.endswith(domain) for domain in config.allowed_domains):
        return False

    haystack = f"{parsed.path} {parsed.query}".lower()
    return any(token in haystack for token in config.include_patterns)


def build_id(source: str, title: str, action_url: str) -> str:
    digest = hashlib.sha1(f"{source}|{title}|{action_url}".encode("utf-8")).hexdigest()
    return digest[:12]


def scrape_source(config: SourceConfig) -> list[dict]:
    html = fetch_html(config.list_url)
    soup = BeautifulSoup(html, "html.parser")

    found: list[dict] = []
    seen_urls: set[str] = set()

    for anchor in soup.select("a[href]"):
        href_raw = anchor.get("href", "")
        href = href_raw if isinstance(href_raw, str) else ""
        if not href:
            continue

        title = normalize_space(anchor.get_text(" "))
        if len(title) < 12:
            continue

        if not is_allowed_link(config, href):
            continue

        action_url = urljoin(config.list_url, href)
        if action_url in seen_urls:
            continue

        seen_urls.add(action_url)
        item = {
            "id": build_id(config.name, title, action_url),
            "source": config.name,
            "organization": config.organization,
            "title": title,
            "summary": f"Campagna individuata automaticamente da {config.name}.",
            "action_url": action_url,
            "source_url": config.list_url,
            "tags": list(config.tags),
            "country": config.country,
            "language": config.language,
            "last_seen": datetime.now(timezone.utc).isoformat(),
        }
        found.append(item)

        if len(found) >= MAX_PER_SOURCE:
            break

    return found


def fallback_items(now_iso: str) -> list[dict]:
    return [
        {
            "id": "ice-fallback",
            "source": "Iniziativa dei Cittadini Europei",
            "organization": "Commissione Europea (ICE)",
            "title": "Portale ufficiale ICE - iniziative in evidenza",
            "summary": "Fallback: usa il portale ICE se lo scraping non produce risultati.",
            "action_url": "https://citizens-initiative.europa.eu/_it",
            "source_url": "https://citizens-initiative.europa.eu/find-initiative_en",
            "tags": ["UE", "legislazione", "fallback"],
            "country": "EU",
            "language": "it",
            "last_seen": now_iso,
        },
        {
            "id": "avaaz-fallback",
            "source": "Avaaz",
            "organization": "Avaaz",
            "title": "Portale campagne Avaaz",
            "summary": "Fallback: elenco campagne globali su Avaaz.",
            "action_url": "https://secure.avaaz.org/campaign/en/",
            "source_url": "https://secure.avaaz.org/campaign/en/",
            "tags": ["globale", "pressione politica", "fallback"],
            "country": "Global",
            "language": "en",
            "last_seen": now_iso,
        },
        {
            "id": "greenpeace-fallback",
            "source": "Greenpeace",
            "organization": "Greenpeace",
            "title": "Greenpeace - Act",
            "summary": "Fallback: azioni e petizioni dal portale ufficiale Greenpeace.",
            "action_url": "https://www.greenpeace.org/international/act/",
            "source_url": "https://www.greenpeace.org/international/act/",
            "tags": ["attivati", "azioni legali", "fallback"],
            "country": "Global",
            "language": "en",
            "last_seen": now_iso,
        },
        {
            "id": "wwf-fallback",
            "source": "WWF",
            "organization": "WWF",
            "title": "WWF - Act",
            "summary": "Fallback: azioni civiche dal portale WWF.",
            "action_url": "https://wwf.panda.org/act/",
            "source_url": "https://wwf.panda.org/act/",
            "tags": ["clima", "biodiversita", "fallback"],
            "country": "Global",
            "language": "en",
            "last_seen": now_iso,
        },
        {
            "id": "openpetition-fallback",
            "source": "openPetition",
            "organization": "openPetition",
            "title": "openPetition - elenco petizioni",
            "summary": "Fallback: portale no-profit e trasparente per petizioni civiche.",
            "action_url": "https://www.openpetition.eu/it/petitions",
            "source_url": "https://www.openpetition.eu/it/petitions",
            "tags": ["no-profit", "trasparenza", "fallback"],
            "country": "EU",
            "language": "it",
            "last_seen": now_iso,
        },
    ]


def dedupe(campaigns: Iterable[dict]) -> list[dict]:
    seen: set[str] = set()
    cleaned: list[dict] = []

    for item in campaigns:
        key = item["action_url"].strip().lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(item)

    cleaned.sort(key=lambda x: (x["source"], x["title"]))
    return cleaned


def ensure_source_coverage(campaigns: list[dict], now_iso: str) -> list[dict]:
    fallback_by_source = {item["source"]: item for item in fallback_items(now_iso)}
    present_sources = {item["source"] for item in campaigns}

    for config in SOURCES:
        if config.name not in present_sources and config.name in fallback_by_source:
            campaigns.append(fallback_by_source[config.name])

    return campaigns


def update_file(campaigns: list[dict]) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "campaigns": campaigns,
    }
    TARGET_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    now_iso = datetime.now(timezone.utc).isoformat()
    all_campaigns: list[dict] = []

    for config in SOURCES:
        try:
            items = scrape_source(config)
            all_campaigns.extend(items)
            print(f"[{config.name}] trovate {len(items)} campagne")
        except Exception as exc:  # noqa: BLE001
            print(f"[{config.name}] errore scraping: {exc}")

    all_campaigns = dedupe(all_campaigns)

    if not all_campaigns:
        print("Nessuna campagna trovata, uso fallback.")
        all_campaigns = fallback_items(now_iso)
    else:
        all_campaigns = ensure_source_coverage(all_campaigns, now_iso)
        all_campaigns = dedupe(all_campaigns)

    update_file(all_campaigns)
    print(f"Aggiornato {TARGET_FILE} con {len(all_campaigns)} campagne")


if __name__ == "__main__":
    main()
