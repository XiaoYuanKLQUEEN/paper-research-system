#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""发现开源 GitHub 项目候选（不含商业产品）。"""

import argparse
import json
import re
import ssl
import sys
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Set
import urllib.request
import urllib.parse

ssl._create_default_https_context = ssl._create_unverified_context

logger = logging.getLogger(__name__)

GITHUB_SEARCH = "https://api.github.com/search/repositories"


def load_config(path: str) -> Dict:
    import yaml
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def github_search(query: str, per_page: int = 10) -> List[Dict]:
    params = urllib.parse.urlencode({
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": per_page,
    })
    url = f"{GITHUB_SEARCH}?{params}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "PaperRadar/1.0",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data.get("items", [])


def extract_github_from_papers(papers: List[Dict]) -> List[Dict]:
    pattern = re.compile(r"https?://github\.com/[\w.-]+/[\w.-]+", re.I)
    found = []
    seen = set()
    for p in papers:
        text = (p.get("summary") or "") + " " + (p.get("abstract") or "")
        for m in pattern.findall(text):
            m = m.rstrip(").,]")
            if m.lower() not in seen:
                seen.add(m.lower())
                parts = m.replace("https://github.com/", "").split("/")
                if len(parts) >= 2:
                    found.append({
                        "full_name": f"{parts[0]}/{parts[1]}",
                        "html_url": m,
                        "description": f"Linked from paper: {p.get('title', '')[:60]}",
                        "stargazers_count": 0,
                        "source": "paper_link",
                        "pushed_at": None,
                    })
    return found


def should_exclude(name: str, full_name: str, excludes: List[str]) -> bool:
    blob = (name + " " + full_name).lower()
    return any(ex in blob for ex in excludes)


def normalize_repo(item: Dict, query: str = "") -> Dict:
    return {
        "name": item.get("name") or item.get("full_name", ""),
        "full_name": item.get("full_name", ""),
        "url": item.get("html_url", ""),
        "description": (item.get("description") or "")[:300],
        "stars": item.get("stargazers_count", 0),
        "pushed_at": item.get("pushed_at"),
        "source": item.get("source", "github_search"),
        "matched_query": query,
        "language": item.get("language"),
    }


def main():
    parser = argparse.ArgumentParser(description="Scan open-source GitHub tools")
    parser.add_argument("--config", default="config/tools_discovery.yaml")
    parser.add_argument("--papers-json", default=None, help="arxiv JSON to extract repo links")
    parser.add_argument("--output", default="tools_raw.json")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", stream=sys.stderr)

    cfg = load_config(args.config)
    max_candidates = cfg.get("max_candidates", 12)
    min_stars = cfg.get("min_stars", 10)
    excludes = [x.lower() for x in cfg.get("exclude_name_keywords", [])]

    repos: List[Dict] = []
    seen: Set[str] = set()

    if cfg.get("extract_github_from_papers") and args.papers_json and Path(args.papers_json).exists():
        papers_data = json.loads(Path(args.papers_json).read_text(encoding="utf-8"))
        papers = papers_data.get("top_papers") or papers_data.get("papers") or []
        for r in extract_github_from_papers(papers):
            fn = r.get("full_name", "").lower()
            if fn and fn not in seen:
                seen.add(fn)
                repos.append(normalize_repo(r))

    for q in cfg.get("github_queries", []):
        try:
            items = github_search(q, per_page=8)
        except Exception as e:
            logger.warning("GitHub search failed for %s: %s", q, e)
            time.sleep(2)
            continue

        for item in items:
            fn = (item.get("full_name") or "").lower()
            if not fn or fn in seen:
                continue
            if item.get("stargazers_count", 0) < min_stars:
                continue
            if should_exclude(item.get("name", ""), fn, excludes):
                continue
            seen.add(fn)
            repos.append(normalize_repo(item, q))
        time.sleep(1.5)

    eval_hints = (
        "eval", "judge", "benchmark", "assessment", "bias", "agent", "rubric", "ragas"
    )

    def tool_rank(r: Dict) -> tuple:
        text = (
            (r.get("description") or "") + " " + (r.get("matched_query") or "") + " "
            + (r.get("full_name") or "")
        ).lower()
        rel = sum(1 for h in eval_hints if h in text)
        # 不按 paper_link 优先：论文附带 repo 常为 0 star，不应挤占工具榜
        return (rel, r.get("stars", 0))

    repos.sort(key=tool_rank, reverse=True)
    # 正式工具榜：仅保留达到 min_stars 的 GitHub 项目，杜绝 0 star 噪声
    selected = [r for r in repos if r.get("stars", 0) >= min_stars][:max_candidates]

    if not selected:
        fb_path = Path(__file__).parent / "config" / "tools_fallback.yaml"
        if fb_path.exists():
            fb = load_config(str(fb_path))
            for item in fb.get("items") or []:
                selected.append({
                    "name": item.get("full_name", "").split("/")[-1],
                    "full_name": item.get("full_name"),
                    "url": item.get("url"),
                    "description": item.get("description"),
                    "stars": item.get("stars", 0),
                    "source": item.get("source", "fallback"),
                    "pushed_at": None,
                    "matched_query": "",
                    "language": None,
                })
            selected = selected[:max_candidates]
            logger.warning("GitHub failed; using %d fallback tools", len(selected))

    out = {
        "fetched_at": datetime.now().isoformat(),
        "count": len(selected),
        "items": selected,
    }
    json_str = json.dumps(out, ensure_ascii=False, indent=2)
    Path(args.output).write_text(json_str, encoding="utf-8")
    logger.info("Wrote %d tools to %s", len(selected), args.output)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        print(json_str)
    except (AttributeError, UnicodeEncodeError):
        print(json_str.encode("utf-8", errors="replace").decode("utf-8", errors="replace"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
