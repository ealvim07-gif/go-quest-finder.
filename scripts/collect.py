#!/usr/bin/env python3
"""Conservative public-source collector for GO Quest Finder.

Only stores a quest when task + reward + a valid coordinate pair occur together
in a public RSS item/page. It never logs in, bypasses a paywall, or guesses data.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CONFIG = ROOT / "config" / "searches.json"
QUESTS_FILE = DATA / "quests.json"
STATUS_FILE = DATA / "collection-status.json"
USER_AGENT = "GOQuestFinderBot/1.0 (public community research; contact: repository owner)"
MAX_PAGE_BYTES = 700_000

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "svg"}:
            self.skip += 1
    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg"} and self.skip:
            self.skip -= 1
    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)

def plain(value: str) -> str:
    parser = TextExtractor()
    try:
        parser.feed(html.unescape(value or ""))
        return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()
    except Exception:
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value or "")).strip()

def get(url: str, accept: str = "*/*") -> bytes | None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
    try:
        with urllib.request.urlopen(req, timeout=18) as response:
            final_url = response.geturl().lower()
            if any(x in final_url for x in ("/login", "/signin", "/subscribe", "/paywall")):
                return None
            data = response.read(MAX_PAGE_BYTES + 1)
            return data[:MAX_PAGE_BYTES] if len(data) <= MAX_PAGE_BYTES else data[:MAX_PAGE_BYTES]
    except Exception as exc:
        print(f"[skip] {url}: {exc}")
        return None

def feed_url(kind: str, query: str) -> str:
    q = urllib.parse.quote_plus(query)
    if kind == "reddit":
        return f"https://www.reddit.com/search.rss?q={q}&sort=new&t=month"
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"

def read_feed(url: str, source_kind: str) -> list[dict]:
    raw = get(url, "application/rss+xml, application/atom+xml, application/xml")
    if not raw:
        return []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return []
    entries = []
    for item in root.findall(".//item"):
        title = plain(item.findtext("title", ""))
        link = (item.findtext("link", "") or "").strip()
        description = plain(item.findtext("description", ""))
        published = item.findtext("pubDate", "") or ""
        if link:
            entries.append({"title": title, "link": link, "text": f"{title}. {description}", "published": published, "source_kind": source_kind})
    # Atom fallback
    ns = {"a": "http://www.w3.org/2005/Atom"}
    if not entries:
        for item in root.findall(".//a:entry", ns):
            title = plain(item.findtext("a:title", "", ns))
            link_el = item.find("a:link", ns)
            link = link_el.attrib.get("href", "") if link_el is not None else ""
            summary = plain(item.findtext("a:summary", "", ns))
            published = item.findtext("a:published", "", ns) or ""
            if link:
                entries.append({"title": title, "link": link, "text": f"{title}. {summary}", "published": published, "source_kind": source_kind})
    return entries

def page_text(url: str) -> str:
    # Only fetch the public URL as presented by the feed. No auth or paywall bypass.
    raw = get(url, "text/html,application/xhtml+xml")
    if not raw:
        return ""
    decoded = raw.decode("utf-8", errors="ignore")
    lowered = decoded.lower()
    if any(term in lowered for term in ("subscribe to continue reading", "sign in to continue", "members-only", "paywall")):
        return ""
    return plain(decoded)

def coords(text: str):
    patterns = [
        r"(?:lat(?:itude)?\s*[:=]\s*)([-+]?\d{1,2}\.\d+)\s*[,;/ ]+\s*(?:lon(?:gitude)?|lng)\s*[:=]\s*([-+]?\d{1,3}\.\d+)",
        r"(?:coordinates?|gps|coordenadas?)\s*[:=]?\s*([-+]?\d{1,2}\.\d{3,})\s*[,;/ ]+\s*([-+]?\d{1,3}\.\d{3,})",
        r"(?<!\d)([-+]?\d{1,2}\.\d{4,})\s*,\s*([-+]?\d{1,3}\.\d{4,})(?!\d)"
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.I):
            lat, lng = float(match.group(1)), float(match.group(2))
            if abs(lat) <= 90 and abs(lng) <= 180 and (lat != 0 or lng != 0):
                return lat, lng
    return None

def labeled(text: str, labels: str):
    match = re.search(rf"(?:{labels})\s*[:=\-]\s*([^\n|;•]{{3,150}})", text, re.I)
    return match.group(1).strip(" .") if match else None

def find_target(text: str, targets: list[dict]):
    low = text.casefold()
    for target in targets:
        task = next((term for term in target.get("task_terms", []) if term.casefold() in low), None)
        reward = next((term for term in target.get("reward_terms", []) if term.casefold() in low), None)
        if task and reward:
            return target, task, reward
    return None, None, None

def location(text: str):
    value = labeled(text, r"location|localidade|cidade\s*/\s*pa[ií]s")
    if value:
        parts = [p.strip() for p in re.split(r"[,|]", value, maxsplit=1)]
        return (parts[0], parts[1] if len(parts) > 1 else "")
    return "", ""

def parse_entry(entry: dict, targets: list[dict]):
    text = entry["text"]
    # Read the public post/article when accessible; retain RSS text if not.
    if entry["link"]:
        text += " " + page_text(entry["link"])
    point = coords(text)
    if not point:
        return None
    target, task_term, reward_term = find_target(text, targets)
    group = "specific" if target else "world"
    if target:
        task = task_term
        reward = target.get("name", reward_term)
        search_id = target["id"]
    else:
        task = labeled(text, r"task|mission|field research|tarefa|miss[aã]o")
        reward = labeled(text, r"reward|recompensa")
        if not task or not reward:
            return None
        search_id = "worldwide"
    city, country = location(text)
    lat, lng = point
    published = entry.get("published") or datetime.now(timezone.utc).isoformat()
    return {
        "id": hashlib.sha256(f"{task.casefold()}|{reward.casefold()}|{lat:.6f}|{lng:.6f}".encode()).hexdigest()[:16],
        "task": task,
        "reward": reward,
        "type": "Pesquisa de campo",
        "city": city,
        "country": country,
        "lat": lat,
        "lng": lng,
        "verified": True,
        "verification_note": "Missão, recompensa e par de coordenadas encontrados juntos no conteúdo público da fonte; confirme no jogo antes de viajar.",
        "source": entry["link"],
        "source_title": entry["title"],
        "discovered_at": published,
        "updated_at": datetime.now(timezone.utc).date().isoformat(),
        "search_group": group,
        "search_id": search_id
    }

def main():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    existing = json.loads(QUESTS_FILE.read_text(encoding="utf-8")) if QUESTS_FILE.exists() else []
    if not isinstance(existing, list):
        existing = []
    by_id = {q.get("id") or hashlib.sha256(f"{q.get('task')}|{q.get('reward')}|{q.get('lat')}|{q.get('lng')}".encode()).hexdigest()[:16]: q for q in existing}
    entries = []
    for query in config.get("general_queries", []):
        entries.extend(read_feed(feed_url("google", query), "Google News RSS"))
        entries.extend(read_feed(feed_url("reddit", query), "Reddit RSS"))
        time.sleep(0.4)
    targets = config.get("specific_searches", [])
    for target in targets:
        for query in target.get("search_queries", []):
            entries.extend(read_feed(feed_url("google", query), "Google News RSS"))
            entries.extend(read_feed(feed_url("reddit", query), "Reddit RSS"))
            time.sleep(0.4)
    seen_links = set()
    accepted = []
    for entry in entries:
        if entry["link"] in seen_links:
            continue
        seen_links.add(entry["link"])
        record = parse_entry(entry, targets)
        if record and record["id"] not in by_id:
            by_id[record["id"]] = record
            accepted.append(record)
    all_records = sorted(by_id.values(), key=lambda q: q.get("discovered_at", ""), reverse=True)
    DATA.mkdir(exist_ok=True)
    QUESTS_FILE.write_text(json.dumps(all_records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    status = {
        "last_run_utc": datetime.now(timezone.utc).isoformat(),
        "feeds_checked": len(config.get("general_queries", [])) * 2 + sum(len(t.get("search_queries", [])) * 2 for t in targets),
        "items_seen": len(entries),
        "new_verified_records": len(accepted),
        "total_records": len(all_records),
        "coverage": "partial_public_sources_only",
        "note": "A ausência de resultados não significa ausência de missões no mundo. Apenas fontes públicas consultadas foram cobertas."
    }
    STATUS_FILE.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False))
    for item in accepted:
        print(f"[NEW] {item['task']} | {item['reward']} | {item['lat']},{item['lng']} | {item['source']}")

if __name__ == "__main__":
    main()
