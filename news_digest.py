#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从权威 RSS 抓取 2-3 条英文快讯候选（中文撰写在 merge/日报阶段）。"""

import argparse
import json
import re
import ssl
import sys
import logging
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Dict, List, Optional
from xml.etree import ElementTree as ET
import urllib.request

ssl._create_default_https_context = ssl._create_unverified_context

logger = logging.getLogger(__name__)

# RSS 2.0 / Atom 简易解析
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


def load_config(path: str) -> Dict:
    import yaml
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def fetch_url(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "PaperRadar/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def parse_date(entry: ET.Element, is_atom: bool) -> Optional[datetime]:
    if is_atom:
        for tag in ("updated", "published", "created"):
            el = entry.find(f"atom:{tag}", ATOM_NS)
            if el is not None and el.text:
                try:
                    return datetime.fromisoformat(el.text.replace("Z", "+00:00"))
                except ValueError:
                    pass
    else:
        el = entry.find("pubDate")
        if el is not None and el.text:
            try:
                return parsedate_to_datetime(el.text)
            except (TypeError, ValueError):
                pass
    return None


def parse_feed(xml_bytes: bytes, source: Dict) -> List[Dict]:
    root = ET.fromstring(xml_bytes)
    is_atom = root.tag.endswith("feed")
    items = []

    if is_atom:
        entries = root.findall("atom:entry", ATOM_NS)
    else:
        entries = root.findall(".//item")

    for entry in entries:
        if is_atom:
            title_el = entry.find("atom:title", ATOM_NS)
            link_el = entry.find("atom:link", ATOM_NS)
            summary_el = entry.find("atom:summary", ATOM_NS) or entry.find("atom:content", ATOM_NS)
            link = link_el.get("href") if link_el is not None else ""
            title = (title_el.text or "").strip() if title_el is not None else ""
            summary = (summary_el.text or "").strip() if summary_el is not None else ""
        else:
            title_el = entry.find("title")
            link_el = entry.find("link")
            desc_el = entry.find("description") or entry.find("{http://purl.org/rss/1.0/modules/content/}encoded")
            title = (title_el.text or "").strip() if title_el is not None else ""
            link = (link_el.text or "").strip() if link_el is not None else ""
            summary = (desc_el.text or "").strip() if desc_el is not None else ""

        summary = re.sub(r"<[^>]+>", "", summary)
        summary = re.sub(r"\s+", " ", summary).strip()[:500]

        pub = parse_date(entry, is_atom)
        items.append({
            "title": title,
            "url": link,
            "summary_en": summary,
            "published": pub.isoformat() if pub else None,
            "source": source.get("name"),
            "tier": source.get("tier", "official"),
        })

    return items


def fetch_source(source: Dict, max_age_days: int) -> List[Dict]:
    url = source["url"]
    logger.info("Fetching RSS: %s", source.get("name"))
    try:
        data = fetch_url(url)
        items = parse_feed(data, source)
    except Exception as e:
        logger.warning("Failed %s: %s", source.get("name"), e)
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    fresh = []
    for it in items:
        if it.get("published"):
            try:
                pub = datetime.fromisoformat(it["published"])
                if pub.tzinfo is None:
                    pub = pub.replace(tzinfo=timezone.utc)
                if pub < cutoff:
                    continue
            except ValueError:
                pass
        fresh.append(it)
    return fresh


def rank_items(items: List[Dict]) -> List[Dict]:
    tier_score = {"official": 3, "media": 2, "academic": 1}

    def key(it):
        ts = 0.0
        if it.get("published"):
            try:
                pub = datetime.fromisoformat(it["published"].replace("Z", "+00:00"))
                ts = pub.timestamp()
            except ValueError:
                pass
        return (tier_score.get(it.get("tier"), 0), ts)

    return sorted(items, key=key, reverse=True)


def main():
    parser = argparse.ArgumentParser(description="Fetch authoritative AI news flash items")
    parser.add_argument("--config", default="config/news_sources.yaml")
    parser.add_argument("--output", default="news_raw.json")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", stream=sys.stderr)

    cfg = load_config(args.config)
    max_total = cfg.get("max_total", 3)
    max_age = cfg.get("max_age_days", 7)

    all_items = []
    for src in cfg.get("sources", []):
        per = src.get("max_per_run", 1)
        got = fetch_source(src, max_age)[: per * 3]
        all_items.extend(got[:per])

    ranked = rank_items(all_items)
    # 去重 URL
    seen = set()
    unique = []
    for it in ranked:
        u = it.get("url", "")
        if u and u not in seen:
            seen.add(u)
            unique.append(it)

    selected = unique[:max_total]

    if not selected:
        fb_path = Path(__file__).parent / "config" / "news_fallback.yaml"
        if fb_path.exists():
            fb = load_config(str(fb_path))
            selected = (fb.get("items") or [])[:max_total]
            logger.warning("RSS failed; using %d fallback news items", len(selected))

    out = {
        "fetched_at": datetime.now().isoformat(),
        "count": len(selected),
        "items": selected,
    }
    Path(args.output).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Wrote %d news items to %s", len(selected), args.output)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
