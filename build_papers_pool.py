#!/usr/bin/env python3
"""合并本地多篇 arxiv JSON 的 top_papers，去重后输出供雷达使用。"""
import json
import re
from pathlib import Path


def norm_title(t):
    return re.sub(r"[^a-z0-9\s]", "", (t or "").lower()).strip()


def main():
    sources = [
        "verify_arxiv.json",
        "arxiv_merged_2026-06-04.json",
        "arxiv_filtered_2026-06-04.json",
    ]
    seen = set()
    papers = []
    for f in sources:
        p = Path(f)
        if not p.exists():
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        for paper in data.get("top_papers") or []:
            key = paper.get("arxiv_id") or norm_title(paper.get("title"))
            if key and key not in seen:
                seen.add(key)
                papers.append(paper)
            elif not key:
                t = norm_title(paper.get("title"))
                if t and t not in seen:
                    seen.add(t)
                    papers.append(paper)

    papers.sort(key=lambda x: (x.get("scores") or {}).get("recommendation", 0), reverse=True)
    out = {
        "target_date": "2026-06-05",
        "total_unique": len(papers),
        "top_papers": papers,
    }
    Path("papers_pool.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    print(f"papers_pool: {len(papers)} unique")


if __name__ == "__main__":
    main()
