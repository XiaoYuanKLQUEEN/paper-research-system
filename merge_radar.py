#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合并论文 + 工具 + 新闻，配额约 25 条。"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List


def load_yaml(path: str) -> Dict:
    import yaml
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_json(path: str) -> Dict:
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def allocate(papers: List, tools: List, news: List, cfg: Dict) -> Dict:
    target = cfg.get("target_total", 25)
    min_news = cfg.get("min_news", 2)
    max_news = cfg.get("max_news", 3)
    min_tools = cfg.get("min_tools", 2)
    max_tools = cfg.get("max_tools", 6)

    n_news = min(len(news), max_news)
    n_news = max(n_news, min(min_news, len(news)))

    n_tools = min(len(tools), max_tools)
    n_tools = max(n_tools, min(min_tools, len(tools)))

    n_papers = min(len(papers), target - n_news - n_tools)
    if n_papers < 0:
        n_papers = 0
        n_tools = min(len(tools), target - n_news)
        n_papers = target - n_news - n_tools

    return {
        "papers": papers[:n_papers],
        "tools": tools[:n_tools],
        "news": news[:n_news],
        "counts": {
            "papers": n_papers,
            "tools": n_tools,
            "news": n_news,
            "total": n_papers + n_tools + n_news,
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--papers", default="arxiv_filtered.json")
    parser.add_argument("--tools", default="tools_raw.json")
    parser.add_argument("--news", default="news_raw.json")
    parser.add_argument("--config", default="config/radar.yaml")
    parser.add_argument("--output", default="radar_merged.json")
    parser.add_argument("--date", default=None)
    args = parser.parse_args()

    rcfg = load_yaml(args.config)
    pdata = load_json(args.papers)
    tdata = load_json(args.tools)
    ndata = load_json(args.news)

    papers = pdata.get("top_papers") or []
    tools = tdata.get("items") or []
    news = ndata.get("items") or []

    bundle = allocate(papers, tools, news, rcfg)

    out = {
        "target_date": args.date or pdata.get("target_date") or datetime.now().strftime("%Y-%m-%d"),
        "merged_at": datetime.now().isoformat(),
        "allocation": bundle["counts"],
        "papers": bundle["papers"],
        "tools": bundle["tools"],
        "news": bundle["news"],
        "meta": {
            "papers_source": args.papers,
            "tools_source": args.tools,
            "news_source": args.news,
        },
    }

    Path(args.output).write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"allocation": out["allocation"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
