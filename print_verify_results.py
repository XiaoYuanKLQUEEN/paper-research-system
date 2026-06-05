#!/usr/bin/env python3
"""打印验证输出摘要（UTF-8）。"""
import json
from pathlib import Path

arxiv = json.loads(Path("verify_arxiv.json").read_text(encoding="utf-8"))
print("=== arxiv_daily 验证 (top 5, skip-hot) ===")
for i, p in enumerate(arxiv["top_papers"], 1):
    s = p["scores"]
    print(f"{i}. [{p.get('matched_domain')}] 推荐={s['recommendation']} 相关={s['relevance']}")
    print(f"   {p['title'][:75]}")
    print(f"   关键词: {p.get('matched_keywords', [])[:6]}")

conf_path = Path("verify_conf_live.json")
if conf_path.exists():
    conf = json.loads(conf_path.read_text(encoding="utf-8"))
    print("\n=== conf_search 验证 ===")
    for i, p in enumerate(conf.get("top_papers", [])[:5], 1):
        print(f"{i}. [{p.get('conference')}] {p['title'][:60]}... score={p['scores']['recommendation']}")
