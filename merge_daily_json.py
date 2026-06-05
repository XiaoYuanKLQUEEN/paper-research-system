#!/usr/bin/env python3
"""合并近期 arXiv 结果与高影响力论文，供日报生成。"""

import json
import re
from pathlib import Path


def norm_title(t: str) -> str:
    return re.sub(r"[^a-z0-9\s]", "", (t or "").lower()).strip()


def main():
    recent_path = Path("verify_arxiv.json")
    hot_path = Path("arxiv_filtered_2026-06-04.json")
    out_path = Path("arxiv_merged_2026-06-04.json")

    recent = json.loads(recent_path.read_text(encoding="utf-8"))
    hot = json.loads(hot_path.read_text(encoding="utf-8"))

    seen = set()
    merged = []

    for p in recent.get("top_papers", []):
        key = p.get("arxiv_id") or norm_title(p.get("title", ""))
        if key and key not in seen:
            seen.add(key)
            merged.append(p)

    for p in hot.get("top_papers", []):
        key = p.get("arxiv_id") or norm_title(p.get("title", ""))
        if key in seen:
            continue
        # 优先保留与核心方向强相关的 HOT
        domain = p.get("matched_domain", "")
        rec = p.get("scores", {}).get("recommendation", 0)
        title_l = (p.get("title") or "").lower()
        core = any(
            x in title_l
            for x in (
                "llm-as-a-judge", "scoring bias", "position bias", "fairness",
                "evaluation", "bias", "personality", "interview", "assessment",
            )
        )
        if core or rec >= 0.9 or domain in ("LLM评估与评分", "LLM偏见与公平性", "多智能体评估与去偏"):
            seen.add(key or norm_title(p.get("title", "")))
            merged.append(p)

    merged.sort(key=lambda x: x.get("scores", {}).get("recommendation", 0), reverse=True)
    top = merged[:12]

    out = {
        "target_date": "2026-06-04",
        "date_windows": recent.get("date_windows"),
        "total_recent": recent.get("total_recent", 0),
        "total_hot": hot.get("total_hot", 0),
        "total_unique": len(merged),
        "note": "arXiv 官方 API 本次抓取超时/503；近期论文沿用今日早些时候成功抓取结果，HOT 来自本次 Semantic Scholar",
        "top_papers": top,
    }
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Merged {len(top)} papers -> {out_path}")


if __name__ == "__main__":
    main()
