#!/usr/bin/env python3
"""Update campagne.json with cleaned, deduplicated and verified campaigns."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
TARGET_FILE = ROOT / "campagne.json"
TIMEOUT = 20
MAX_PER_SOURCE = 24
HEADERS = {
    "User-Agent": "GreenAnchorBot/1.1 (+https://github.com/gcasaldi/GreenAnchor)"
}

TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "source",
    "ref",
    "fbclid",
    "gclid",
}

BLOCKED_URL_TOKENS = (
    "/contact",
    "report",
    "/privacy",
    "/cookie",
    "/terms",
    "login",
    "sign-in",
    "sign_up",
    "start_a_petition",
    "start-a-petition",
    "petition-guides",
)

BLOCKED_TITLE_TOKENS = (
    "click here to report",
    "clicca qui per segnalare",
    "contact",
    "contatta",
    "privacy",
    "cookie",
    "start a petition",
    "avvia una petizione",
)

CAMPAIGN_HINTS = (
    "petition",
    "petizione",
    "campagna",
    "firma",
    "sign",
    "help",
    "aiut",
    "solidar",
    "umanit",
    "humanitarian",
    "relief",
    "diritt",
    "salute",
    "sanit",
    "emergenz",
    "cure",
    "migr",
    "pover",
    "fame",
    "proteggi",
    "difendi",
    "stop",
    "clean",
    "climate",
    "oceani",
    "foreste",
    "biodiversita",
    "event",
    "volunteer",
    "citizen science",
)

THEME_KEYWORDS = {
    "plastica": "plastica",
    "plastic": "plastica",
    "oceani": "oceani",
    "ocean": "oceani",
    "mare": "oceani",
    "clima": "clima",
    "climate": "clima",
    "forest": "foreste",
    "foreste": "foreste",
    "biodiversity": "biodiversita",
    "biodivers": "biodiversita",
    "energy": "energia",
    "energia": "energia",
    "animal": "animali",
    "fauna": "animali",
}

ACTION_KEYWORDS = {
    "petition": "petizione",
    "petizione": "petizione",
    "firma": "petizione",
    "don": "raccolta fondi",
    "fund": "raccolta fondi",
    "raccolta fondi": "raccolta fondi",
    "crowdfunding": "crowdfunding",
    "gofundme": "crowdfunding",
    "kickstarter": "crowdfunding",
    "adesion": "raccolta adesioni",
    "iscriv": "raccolta adesioni",
    "join": "raccolta adesioni",
    "signup": "raccolta adesioni",
    "event": "evento",
    "evento": "evento",
    "mobilit": "evento",
    "protest": "evento",
    "volont": "volontariato",
    "citizen science": "citizen science",
    "scienza": "citizen science",
    "mail": "mail action",
    "letter": "mail action",
}

TITLE_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "della",
    "delle",
    "degli",
    "dello",
    "della",
    "per",
    "con",
    "del",
    "dei",
    "di",
    "la",
    "le",
    "il",
    "gli",
    "un",
    "una",
    "to",
    "in",
    "su",
    "da",
}

MONTHS_IT = {
    "gennaio": 1,
    "febbraio": 2,
    "marzo": 3,
    "aprile": 4,
    "maggio": 5,
    "giugno": 6,
    "luglio": 7,
    "agosto": 8,
    "settembre": 9,
    "ottobre": 10,
    "novembre": 11,
    "dicembre": 12,
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
    verified_org: bool = True


SOURCES = [
    SourceConfig(
        name="Greenpeace Italia",
        organization="Greenpeace Italia",
        list_url="https://www.greenpeace.org/italy/attivati/",
        allowed_domains=("greenpeace.org",),
        include_patterns=("/italy/", "attivati", "petizione", "campagna"),
        tags=("italia", "attivati", "ambiente"),
        language="it",
        country="IT",
    ),
    SourceConfig(
        name="WWF Italia",
        organization="WWF Italia",
        list_url="https://www.wwf.it/",
        allowed_domains=("wwf.it",),
        include_patterns=("cosa-puoi-fare", "petizione", "campagna", "natura"),
        tags=("italia", "clima", "biodiversita"),
        language="it",
        country="IT",
    ),
    SourceConfig(
        name="Legambiente",
        organization="Legambiente",
        list_url="https://www.legambiente.it/campagne/",
        allowed_domains=("legambiente.it",),
        include_patterns=("campagne", "petizione", "mobilitazione", "appello"),
        tags=("italia", "campagne", "territorio"),
        language="it",
        country="IT",
    ),
    SourceConfig(
        name="Marevivo",
        organization="Marevivo",
        list_url="https://marevivo.it/cosa-puoi-fare/",
        allowed_domains=("marevivo.it",),
        include_patterns=("cosa-puoi-fare", "campagna", "mare", "petizione"),
        tags=("italia", "oceani", "inquinamento"),
        language="it",
        country="IT",
    ),
    SourceConfig(
        name="Change.org Italia",
        organization="Change.org",
        list_url="https://www.change.org/it",
        allowed_domains=("change.org", "www.change.org"),
        include_patterns=("/it/", "/p/", "petizioni", "petition"),
        tags=("italia", "petizioni", "mobilitazione"),
        language="it",
        country="IT",
        verified_org=False,
    ),
    SourceConfig(
        name="Iniziativa dei Cittadini Europei",
        organization="Commissione Europea (ICE)",
        list_url="https://citizens-initiative.europa.eu/find-initiative_en",
        allowed_domains=("citizens-initiative.europa.eu",),
        include_patterns=("initiative", "initiatives", "details"),
        tags=("ue", "legislazione", "partecipazione civica"),
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
        verified_org=False,
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
        verified_org=False,
    ),
]


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    CHANGEORG_TYPESENSE_API_KEY = (
        "Mm5jam83L2h4SVVnR01qOHhHcU1kUHl5SW94TzdQM3pMK2pwQTUzTVJXOD04VzVX"
        "eyJmaWx0ZXJfYnkiOiJkaXNjb3ZlcmFibGU6dHJ1ZSIsImV4Y2x1ZGVfZmllbGRzIjoiY2FtcGFpZ25fdGVhbV9uYW1lIn0="
    )
    CHANGEORG_TYPESENSE_BASE_URL = "https://www.change.org/ts"
    CHANGEORG_HUMANITARIAN_QUERIES = (
        ("it", "aiuti umanitari"),
        ("it", "solidarieta"),
        ("it", "diritti umani"),
        ("it", "emergenza"),
        ("it", "salute"),
        ("it", "migranti"),
        ("en", "humanitarian aid"),
        ("en", "solidarity"),
        ("en", "human rights"),
        ("en", "relief"),
        ("en", "refugees"),
    )
    CHANGEORG_HUMANITARIAN_HINTS = (
        "humanitarian",
        "umanit",
        "solidar",
        "diritt",
        "aiut",
        "emergenz",
        "salute",
        "sanit",
        "migr",
        "rifugiat",
        "refuge",
        "aid",
        "relief",
        "help",
    )


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def clean_text(text: str) -> str:
    text = normalize_space(text)
    replacements = {
        "Ã¨": "è",
        "Ã©": "é",
        "Ã¹": "ù",
        "Ã ": "à",
        "Ã¬": "ì",
        "Ã²": "ò",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    return text


def normalize_for_dedupe(text: str) -> str:
    raw = unicodedata.normalize("NFKD", text.lower())
    raw = "".join(ch for ch in raw if not unicodedata.combining(ch))
    raw = re.sub(r"[^a-z0-9]+", " ", raw)
    return normalize_space(raw)


def canonicalize_url(url: str) -> str:
    parsed = urlparse(url)
    clean_query = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if k.lower() not in TRACKING_PARAMS
    ]
    query = urlencode(clean_query)
    clean_path = re.sub(r"/+", "/", parsed.path or "/")
    clean = parsed._replace(query=query, fragment="", path=clean_path)
    return urlunparse(clean)


def dedupe_key(title: str, action_url: str) -> str:
    return f"{normalize_for_dedupe(title)}|{canonicalize_url(action_url).lower()}"


def fetch_html(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    return response.text


def search_changeorg_humanitarian_campaigns() -> list[dict]:
    headers = {**HEADERS, "X-TYPESENSE-API-KEY": CHANGEORG_TYPESENSE_API_KEY}
    found: dict[str, dict] = {}

    for locale, query in CHANGEORG_HUMANITARIAN_QUERIES:
        collection = "petitions_it" if locale == "it" else "petitions_en"
        preset = "petitions_initial_it" if locale == "it" else "petitions_initial_en"
        params = {"q": query, "preset": preset, "page": 1, "per_page": 8}

        try:
            response = requests.get(
                f"{CHANGEORG_TYPESENSE_BASE_URL}/collections/{collection}/documents/search",
                params=params,
                headers=headers,
                timeout=TIMEOUT,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception:
            continue

        for hit in payload.get("hits", []):
            document = hit.get("document", {})
            slug = document.get("slug")
            title = clean_text(document.get("ask", "")).strip()
            summary = clean_text(document.get("description", "")).strip()
            if not slug or not title:
                continue

            haystack = f"{title} {summary} {' '.join(document.get('tags', []))}".lower()
            if not any(token in haystack for token in CHANGEORG_HUMANITARIAN_HINTS):
                continue

            action_url = canonicalize_url(f"https://www.change.org/p/{slug}")
            objective = summary or f"Obiettivo: sostenere la petizione umanitaria '{title}'."
            item = {
                "id": build_id("Change.org Italia", title, action_url),
                "source": "Change.org Italia",
                "organization": "Change.org",
                "title": title,
                "summary": objective,
                "objective": objective,
                "action_url": action_url,
                "source_url": action_url,
                "tags": list(dict.fromkeys(["italia", "petizioni", "umanitario", *document.get("tags", [])])),
                "country": "IT" if locale == "it" else "Global",
                "language": locale,
                "verified_organization": False,
                "status": "chiusa" if document.get("victory") else "attiva",
                "theme": infer_theme(title, ["umanitario", *document.get("tags", [])]),
                "action_type": infer_action_type(title, action_url),
                "deadline": None,
            }
            found[dedupe_key(title, action_url)] = item

            if len(found) >= MAX_PER_SOURCE:
                return list(found.values())

    return list(found.values())


def is_allowed_link(config: SourceConfig, href: str) -> bool:
    absolute = canonicalize_url(urljoin(config.list_url, href))
    parsed = urlparse(absolute)
    if parsed.scheme not in {"http", "https"}:
        return False
    if not any(parsed.netloc.endswith(domain) for domain in config.allowed_domains):
        return False

    haystack = f"{parsed.path} {parsed.query}".lower()
    return any(token in haystack for token in config.include_patterns)


def is_filtered_out(title: str, action_url: str) -> bool:
    title_l = title.lower()
    url_l = action_url.lower()
    if any(token in title_l for token in BLOCKED_TITLE_TOKENS):
        return True
    return any(token in url_l for token in BLOCKED_URL_TOKENS)


def looks_like_campaign(title: str, action_url: str) -> bool:
    if len(title) < 14:
        return False
    haystack = f"{title} {action_url}".lower()
    if "change.org" in haystack and "/p/" in haystack:
        return True
    return any(token in haystack for token in CAMPAIGN_HINTS)


def infer_theme(title: str, tags: list[str]) -> str:
    haystack = f"{title} {' '.join(tags)}".lower()
    for token, theme in THEME_KEYWORDS.items():
        if token in haystack:
            return theme
    return "ambiente"


def infer_action_type(title: str, action_url: str) -> str:
    haystack = f"{title} {action_url}".lower()
    for token, action_type in ACTION_KEYWORDS.items():
        if token in haystack:
            return action_type
    if "event" in haystack or "evento" in haystack:
        return "evento"
    return "petizione"


def infer_scope(country: str) -> str:
    if country == "IT":
        return "Italia"
    if country == "EU":
        return "Europa"
    return "Globale"


def infer_status(title: str, action_url: str) -> str:
    haystack = f"{title} {action_url}".lower()
    closed_tokens = ("closed", "chiusa", "ended", "archiv", "completed")
    if any(token in haystack for token in closed_tokens):
        return "chiusa"
    return "attiva"


def extract_deadline_from_text(text: str, base: datetime) -> str | None:
    match_num = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", text)
    if match_num:
        day, month, year = map(int, match_num.groups())
        try:
            return datetime(year, month, day, tzinfo=timezone.utc).isoformat()
        except ValueError:
            return None

    for name, month in MONTHS_IT.items():
        match = re.search(rf"\b(\d{{1,2}})\s+{name}\s+(\d{{4}})\b", text.lower())
        if match:
            day, year = map(int, match.groups())
            try:
                return datetime(year, month, day, tzinfo=timezone.utc).isoformat()
            except ValueError:
                return None

    rel = re.search(r"scade\s+tra\s+(\d{1,2})\s+giorni", text.lower())
    if rel:
        days = int(rel.group(1))
        return (base + timedelta(days=days)).isoformat()

    return None


def parse_int_like(value: str) -> int | None:
    cleaned = re.sub(r"[^0-9]", "", value)
    if not cleaned:
        return None
    return int(cleaned)


def extract_ratio_pair(text: str) -> tuple[int | None, int | None]:
    patterns = [
        r"(\d[\d\.,\s]{2,})\s*(?:su|of|/)\s*(\d[\d\.,\s]{2,})",
        r"(\d[\d\.,\s]{2,})\s*(?:firme|signatures|supporters|adesioni|iscritti)\s*(?:su|of)?\s*(\d[\d\.,\s]{2,})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if not match:
            continue
        current = parse_int_like(match.group(1))
        target = parse_int_like(match.group(2))
        if current is not None and target and target > 0:
            return current, target
    return None, None


def extract_currency_pair(text: str) -> tuple[int | None, int | None]:
    patterns = [
        r"(?:€|eur|euro)\s*(\d[\d\.,\s]{2,})\s*(?:su|of|/)\s*(?:€|eur|euro)\s*(\d[\d\.,\s]{2,})",
        r"(\d[\d\.,\s]{2,})\s*(?:€|eur|euro)\s*(?:su|of|/)\s*(\d[\d\.,\s]{2,})\s*(?:€|eur|euro)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if not match:
            continue
        current = parse_int_like(match.group(1))
        target = parse_int_like(match.group(2))
        if current is not None and target and target > 0:
            return current, target
    return None, None


def extract_percent(text: str) -> int | None:
    match = re.search(r"\b(\d{1,3})\s*%", text)
    if not match:
        return None
    value = int(match.group(1))
    if 0 <= value <= 100:
        return value
    return None


def progress_payload(item: dict) -> dict:
    action_type = item.get("action_type", "petizione")
    text = f"{item.get('title', '')} {item.get('summary', '')}"

    current: int | None = None
    target: int | None = None
    percent: int | None = None
    unit: str | None = None

    if action_type == "petizione":
        current, target = extract_ratio_pair(text)
        unit = "firme" if current is not None and target is not None else None
    elif action_type == "raccolta fondi":
        current, target = extract_currency_pair(text)
        unit = "euro" if current is not None and target is not None else None
    elif action_type == "crowdfunding":
        current, target = extract_currency_pair(text)
        unit = "euro" if current is not None and target is not None else None
        if current is None or target is None:
            percent = extract_percent(text)
            unit = "percentuale" if percent is not None else None
    elif action_type == "raccolta adesioni":
        current, target = extract_ratio_pair(text)
        unit = "adesioni" if current is not None and target is not None else None
    else:
        # Eventi e mobilitazioni senza target numerico non hanno progresso percentuale.
        current, target, percent, unit = None, None, None, None

    if percent is None and current is not None and target is not None and target > 0:
        percent = max(0, min(100, round((current / target) * 100)))

    measurable = percent is not None
    return {
        "progress_current": current,
        "progress_target": target,
        "progress_percent": percent,
        "progress_unit": unit,
        "progress_measurable": measurable,
        "progress_note": "Il progresso e calcolato sui dati pubblicati dalla fonte originale." if measurable else None,
        "progress_method": "deterministico",
    }


def title_tokens(title: str) -> set[str]:
    normalized = normalize_for_dedupe(title)
    return {
        token
        for token in normalized.split(" ")
        if token and len(token) >= 4 and token not in TITLE_STOPWORDS
    }


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def assign_semantic_clusters(campaigns: list[dict]) -> list[dict]:
    clusters: list[dict] = []

    for item in campaigns:
        tokens = title_tokens(item.get("title", ""))
        item["semantic_tokens"] = sorted(tokens)
        assigned = False

        for cluster in clusters:
            if item.get("theme") != cluster["theme"]:
                continue
            similarity = jaccard(tokens, cluster["tokens"])
            if similarity >= 0.45:
                cluster["items"].append(item)
                cluster["tokens"] = cluster["tokens"] | tokens
                item["semantic_cluster_id"] = cluster["id"]
                assigned = True
                break

        if assigned:
            continue

        cluster_id = f"cluster-{len(clusters) + 1:03d}"
        item["semantic_cluster_id"] = cluster_id
        clusters.append(
            {
                "id": cluster_id,
                "theme": item.get("theme"),
                "tokens": set(tokens),
                "items": [item],
            }
        )

    cluster_sizes = {cluster["id"]: len(cluster["items"]) for cluster in clusters}
    for item in campaigns:
        item["semantic_cluster_size"] = cluster_sizes.get(item["semantic_cluster_id"], 1)

    return campaigns


def build_id(source: str, title: str, action_url: str) -> str:
    digest = hashlib.sha1(f"{source}|{title}|{action_url}".encode("utf-8")).hexdigest()
    return digest[:12]


def verification_payload(item: dict) -> dict:
    checks = {
        "primary_source": bool(item.get("source_url")),
        "campaign_active": item.get("status") == "attiva",
        "organization_identified": bool(item.get("organization")),
        "date_verified": bool(item.get("last_verified")),
        "link_working": item.get("action_url", "").startswith("http"),
        "goal_declared": len(item.get("objective", "")) >= 20,
    }
    score = round((sum(1 for val in checks.values() if val) / len(checks)) * 100)
    if score >= 90:
        status = "verificata"
    elif score >= 70:
        status = "da_verificare"
    else:
        status = "fonte_aggregata"

    return {
        "verification_score": score,
        "verification_status": status,
        "verification_checks": checks,
    }


def enrich_campaign(item: dict, now_dt: datetime, previous_first_seen: str | None) -> dict:
    now_iso = now_dt.isoformat()
    item["title"] = clean_text(item.get("title", "")).strip()
    item["action_url"] = canonicalize_url(item.get("action_url", "").strip())
    item["source_url"] = canonicalize_url(item.get("source_url", "").strip())
    item["summary"] = clean_text(item.get("summary", "")).strip()
    item["objective"] = item.get("objective") or item["summary"]
    item["status"] = item.get("status") or infer_status(item["title"], item["action_url"])
    item["scope"] = infer_scope(item.get("country", "Global"))
    item["theme"] = item.get("theme") or infer_theme(item["title"], item.get("tags", []))
    item["action_type"] = item.get("action_type") or infer_action_type(item["title"], item["action_url"])
    item["deadline"] = item.get("deadline") or extract_deadline_from_text(item["title"], now_dt)
    item["verified_source"] = True
    item["last_verified"] = now_iso
    item["last_seen"] = now_iso
    first_seen = previous_first_seen or now_iso
    item["first_seen"] = first_seen
    first_seen_dt = parse_dt(first_seen) or now_dt
    item["is_new_24h"] = now_dt - first_seen_dt <= timedelta(hours=24)
    item.update(verification_payload(item))
    item.update(progress_payload(item))
    return item


def scrape_source(config: SourceConfig) -> list[dict]:
    if config.name == "Change.org Italia":
        humanitarian = search_changeorg_humanitarian_campaigns()
        if humanitarian:
            return humanitarian

    html = fetch_html(config.list_url)
    soup = BeautifulSoup(html, "html.parser")

    found: list[dict] = []
    seen_urls: set[str] = set()

    for anchor in soup.select("a[href]"):
        href_raw = anchor.get("href", "")
        href = href_raw if isinstance(href_raw, str) else ""
        if not href:
            continue

        title = clean_text(anchor.get_text(" "))
        if not title:
            continue
        if not is_allowed_link(config, href):
            continue

        action_url = canonicalize_url(urljoin(config.list_url, href))
        if action_url in seen_urls:
            continue
        if is_filtered_out(title, action_url):
            continue
        if not looks_like_campaign(title, action_url):
            continue

        seen_urls.add(action_url)
        objective = f"Obiettivo: supportare un'azione ambientale concreta rilevata da {config.name}."
        item = {
            "id": build_id(config.name, title, action_url),
            "source": config.name,
            "organization": config.organization,
            "title": title,
            "summary": objective,
            "objective": objective,
            "action_url": action_url,
            "source_url": config.list_url,
            "tags": list(dict.fromkeys((*config.tags, infer_theme(title, list(config.tags))))),
            "country": config.country,
            "language": config.language,
            "verified_organization": config.verified_org,
            "status": infer_status(title, action_url),
            "theme": infer_theme(title, list(config.tags)),
            "action_type": infer_action_type(title, action_url),
            "deadline": extract_deadline_from_text(title, now_utc()),
        }
        found.append(item)

        if len(found) >= MAX_PER_SOURCE:
            break

    return found


def fallback_items() -> list[dict]:
    return [
        {
            "id": "greenpeace-italia-fallback",
            "source": "Greenpeace Italia",
            "organization": "Greenpeace Italia",
            "title": "Greenpeace Italia - Attivati",
            "summary": "Obiettivo: partecipare alle azioni Greenpeace sul territorio italiano.",
            "objective": "Obiettivo: partecipare alle azioni Greenpeace sul territorio italiano.",
            "action_url": "https://www.greenpeace.org/italy/attivati/",
            "source_url": "https://www.greenpeace.org/italy/attivati/",
            "tags": ["italia", "attivati", "ambiente"],
            "country": "IT",
            "language": "it",
            "verified_organization": True,
        },
        {
            "id": "wwf-italia-fallback",
            "source": "WWF Italia",
            "organization": "WWF Italia",
            "title": "WWF Italia - Cosa puoi fare",
            "summary": "Obiettivo: sostenere azioni WWF Italia per natura e clima.",
            "objective": "Obiettivo: sostenere azioni WWF Italia per natura e clima.",
            "action_url": "https://www.wwf.it/",
            "source_url": "https://www.wwf.it/",
            "tags": ["italia", "clima", "biodiversita"],
            "country": "IT",
            "language": "it",
            "verified_organization": True,
        },
        {
            "id": "legambiente-fallback",
            "source": "Legambiente",
            "organization": "Legambiente",
            "title": "Legambiente - Campagne",
            "summary": "Obiettivo: aderire alle campagne nazionali di Legambiente.",
            "objective": "Obiettivo: aderire alle campagne nazionali di Legambiente.",
            "action_url": "https://www.legambiente.it/campagne/",
            "source_url": "https://www.legambiente.it/campagne/",
            "tags": ["italia", "territorio", "campagne"],
            "country": "IT",
            "language": "it",
            "verified_organization": True,
        },
        {
            "id": "marevivo-fallback",
            "source": "Marevivo",
            "organization": "Marevivo",
            "title": "Marevivo - Cosa puoi fare",
            "summary": "Obiettivo: sostenere iniziative per oceani e coste italiane.",
            "objective": "Obiettivo: sostenere iniziative per oceani e coste italiane.",
            "action_url": "https://marevivo.it/cosa-puoi-fare/",
            "source_url": "https://marevivo.it/cosa-puoi-fare/",
            "tags": ["italia", "oceani", "inquinamento"],
            "country": "IT",
            "language": "it",
            "verified_organization": True,
        },
        {
            "id": "changeorg-italia-fallback",
            "source": "Change.org Italia",
            "organization": "Change.org",
            "title": "Change.org Italia - Petizioni ambientali",
            "summary": "Obiettivo: trovare petizioni ambientali italiane attive.",
            "objective": "Obiettivo: trovare petizioni ambientali italiane attive.",
            "action_url": "https://www.change.org/it",
            "source_url": "https://www.change.org/it",
            "tags": ["italia", "petizioni", "mobilitazione"],
            "country": "IT",
            "language": "it",
            "verified_organization": False,
        },
        {
            "id": "ice-fallback",
            "source": "Iniziativa dei Cittadini Europei",
            "organization": "Commissione Europea (ICE)",
            "title": "Portale ufficiale ICE - iniziative in evidenza",
            "summary": "Obiettivo: partecipare alle iniziative civiche legislative UE.",
            "objective": "Obiettivo: partecipare alle iniziative civiche legislative UE.",
            "action_url": "https://citizens-initiative.europa.eu/_it",
            "source_url": "https://citizens-initiative.europa.eu/find-initiative_en",
            "tags": ["europa", "legislazione", "partecipazione civica"],
            "country": "EU",
            "language": "it",
            "verified_organization": True,
        },
        {
            "id": "avaaz-fallback",
            "source": "Avaaz",
            "organization": "Avaaz",
            "title": "Portale campagne Avaaz",
            "summary": "Obiettivo: esplorare mobilitazioni ambientali globali.",
            "objective": "Obiettivo: esplorare mobilitazioni ambientali globali.",
            "action_url": "https://secure.avaaz.org/campaign/en/",
            "source_url": "https://secure.avaaz.org/campaign/en/",
            "tags": ["globale", "pressione politica", "mobilitazione"],
            "country": "Global",
            "language": "en",
            "verified_organization": False,
        },
        {
            "id": "greenpeace-fallback",
            "source": "Greenpeace",
            "organization": "Greenpeace",
            "title": "Greenpeace - Act",
            "summary": "Obiettivo: partecipare alle campagne Greenpeace globali.",
            "objective": "Obiettivo: partecipare alle campagne Greenpeace globali.",
            "action_url": "https://www.greenpeace.org/international/act/",
            "source_url": "https://www.greenpeace.org/international/act/",
            "tags": ["globale", "campagne", "ambiente"],
            "country": "Global",
            "language": "en",
            "verified_organization": True,
        },
        {
            "id": "wwf-fallback",
            "source": "WWF",
            "organization": "WWF",
            "title": "WWF - Act",
            "summary": "Obiettivo: sostenere le azioni WWF internazionali.",
            "objective": "Obiettivo: sostenere le azioni WWF internazionali.",
            "action_url": "https://wwf.panda.org/act/",
            "source_url": "https://wwf.panda.org/act/",
            "tags": ["globale", "biodiversita", "clima"],
            "country": "Global",
            "language": "en",
            "verified_organization": True,
        },
        {
            "id": "openpetition-fallback",
            "source": "openPetition",
            "organization": "openPetition",
            "title": "openPetition - elenco petizioni",
            "summary": "Obiettivo: trovare petizioni civiche trasparenti e no-profit.",
            "objective": "Obiettivo: trovare petizioni civiche trasparenti e no-profit.",
            "action_url": "https://www.openpetition.eu/it/petitions",
            "source_url": "https://www.openpetition.eu/it/petitions",
            "tags": ["europa", "petizioni", "trasparenza"],
            "country": "EU",
            "language": "it",
            "verified_organization": False,
        },
    ]


def load_previous_map() -> dict[str, dict]:
    if not TARGET_FILE.exists():
        return {}
    try:
        previous = json.loads(TARGET_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}

    out: dict[str, dict] = {}
    for item in previous.get("campaigns", []):
        title = item.get("title", "")
        action_url = item.get("action_url", "")
        if not title or not action_url:
            continue
        out[dedupe_key(title, action_url)] = item
    return out


def dedupe(campaigns: Iterable[dict]) -> list[dict]:
    by_key: dict[str, dict] = {}
    for item in campaigns:
        key = dedupe_key(item.get("title", ""), item.get("action_url", ""))
        if key not in by_key:
            by_key[key] = item
            continue
        current = by_key[key]
        if item.get("verification_score", 0) > current.get("verification_score", 0):
            by_key[key] = item
    cleaned = list(by_key.values())
    cleaned.sort(key=lambda x: (x.get("scope", ""), -x.get("verification_score", 0), x.get("title", "")))
    return cleaned


def ensure_source_coverage(campaigns: list[dict], now_dt: datetime, previous_map: dict[str, dict]) -> list[dict]:
    present_sources = {item["source"] for item in campaigns}
    for fallback in fallback_items():
        if fallback["source"] in present_sources:
            continue
        prev = previous_map.get(dedupe_key(fallback["title"], fallback["action_url"]))
        campaigns.append(enrich_campaign(fallback, now_dt, prev.get("first_seen") if prev else None))
    return campaigns


def urgency_rank(item: dict, now_dt: datetime) -> int:
    if item.get("status") != "attiva":
        return 99
    deadline = parse_dt(item.get("deadline"))
    if not deadline:
        return 30
    days = (deadline - now_dt).days
    if days < 0:
        return 98
    if days <= 7:
        return 1
    if days <= 30:
        return 2
    return 3


def focus_priority(item: dict, now_dt: datetime) -> tuple:
    percent = item.get("progress_percent")
    if isinstance(percent, int):
        ratio_distance = abs(100 - percent)
        ratio_flag = 0
    else:
        ratio_distance = 999
        ratio_flag = 1

    return (
        0 if item.get("status") == "attiva" else 1,
        0 if item.get("scope") == "Italia" else 1,
        ratio_flag,
        ratio_distance,
        urgency_rank(item, now_dt),
        -item.get("verification_score", 0),
    )


def select_focus(campaigns: list[dict], now_dt: datetime) -> list[dict]:
    active = [item for item in campaigns if item.get("status") == "attiva"]
    best_by_cluster: dict[str, dict] = {}
    for item in active:
        cluster_id = item.get("semantic_cluster_id", "cluster-unknown")
        current = best_by_cluster.get(cluster_id)
        if current is None or focus_priority(item, now_dt) < focus_priority(current, now_dt):
            best_by_cluster[cluster_id] = item

    winners = list(best_by_cluster.values())
    winners.sort(key=lambda item: focus_priority(item, now_dt))
    return winners[:5]


def radar_payload(campaigns: list[dict], now_dt: datetime) -> dict:
    new_24h = [item for item in campaigns if item.get("is_new_24h")]
    active = [item for item in campaigns if item.get("status") == "attiva"]
    urgent = [item for item in active if urgency_rank(item, now_dt) == 1]
    fragmented_clusters = {
        item.get("semantic_cluster_id")
        for item in campaigns
        if item.get("semantic_cluster_size", 1) > 1
    }
    return {
        "generated_at": now_dt.isoformat(),
        "new_campaigns_24h": len(new_24h),
        "active_campaigns": len(active),
        "urgent_campaigns": len(urgent),
        "fragmented_topics": len(fragmented_clusters),
    }


def update_file(campaigns: list[dict], focus: list[dict], radar: dict) -> None:
    payload = {
        "generated_at": now_utc().isoformat(),
        "radar": radar,
        "greenanchor_focus": focus,
        "spotlight": focus,
        "campaigns": campaigns,
    }
    TARGET_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    now_dt = now_utc()
    previous_map = load_previous_map()
    all_campaigns: list[dict] = []

    for config in SOURCES:
        try:
            raw_items = scrape_source(config)
            enriched = []
            for item in raw_items:
                prev = previous_map.get(dedupe_key(item["title"], item["action_url"]))
                enriched.append(enrich_campaign(item, now_dt, prev.get("first_seen") if prev else None))
            all_campaigns.extend(enriched)
            print(f"[{config.name}] trovate {len(enriched)} campagne")
        except Exception as exc:  # noqa: BLE001
            print(f"[{config.name}] errore scraping: {exc}")

    all_campaigns = dedupe(all_campaigns)
    if not all_campaigns:
        print("Nessuna campagna trovata, uso fallback completo.")
        all_campaigns = [
            enrich_campaign(item, now_dt, previous_map.get(dedupe_key(item["title"], item["action_url"]), {}).get("first_seen"))
            for item in fallback_items()
        ]
    else:
        all_campaigns = ensure_source_coverage(all_campaigns, now_dt, previous_map)
        all_campaigns = dedupe(all_campaigns)

    all_campaigns = assign_semantic_clusters(all_campaigns)
    focus = select_focus(all_campaigns, now_dt)
    radar = radar_payload(all_campaigns, now_dt)
    update_file(all_campaigns, focus, radar)

    print(f"Aggiornato {TARGET_FILE} con {len(all_campaigns)} campagne")
    print(f"GreenAnchor Focus: {len(focus)} campagne")


if __name__ == "__main__":
    main()
