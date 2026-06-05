#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【不推荐单独使用】仅生成条目列表式日报，质量远低于 6/2、6/3 的手工/LLM 深度分析模板。
正式日报请由 Agent 按 10_Daily 历史样例撰写，或扩展本模块的 deep 模式。
将 arxiv_daily 的 JSON 输出转为 Obsidian 日报 Markdown（浅层）。
"""

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def _primary_link(paper: Dict) -> tuple:
    """返回 (链接标签, url)。"""
    aid = paper.get("arxiv_id")
    if aid:
        return "arXiv", f"https://arxiv.org/abs/{aid}"
    url = paper.get("url", "") or paper.get("s2_url", "")
    if "arxiv.org" in url:
        clean = url.split("v1")[0] if "v1" in url else url
        return "arXiv", clean
    if "semanticscholar.org" in url:
        return "Semantic Scholar", url
    return "链接", url or "#"


def _pdf_link(paper: Dict) -> str:
    if paper.get("pdf_url"):
        return paper["pdf_url"]
    aid = paper.get("arxiv_id")
    if aid:
        return f"https://arxiv.org/pdf/{aid}v1"
    return _primary_link(paper)[1]


def _authors_line(paper: Dict) -> str:
    raw = paper.get("authors") or []
    names = []
    for a in raw:
        if isinstance(a, str):
            names.append(a)
        elif isinstance(a, dict):
            names.append(a.get("name") or a.get("text") or "")
    names = [n for n in names if n]
    if not names:
        return "（作者待补充）"
    if len(names) <= 5:
        return ", ".join(names)
    return ", ".join(names[:5]) + f" 等 {len(names)} 人"


def _hot_marker(paper: Dict) -> str:
    return " 🔥HOT" if paper.get("is_hot_paper") else ""


def build_overview(papers: List[Dict], meta: Dict) -> List[str]:
    domains = Counter(p.get("matched_domain") or "未分类" for p in papers)
    hot_n = sum(1 for p in papers if p.get("is_hot_paper"))
    recent_n = meta.get("total_recent") or 0
    hot_src = meta.get("total_hot") or 0
    unique_n = meta.get("total_unique") or len(papers)

    domain_bits = "、".join(f"「{k}」{v}篇" for k, v in domains.most_common(4))
    lines = [
        f"今日从 arXiv 近 {meta.get('days', 30)} 天 + Semantic Scholar 近一年高影响力论文中，"
        f"共检索 recent={recent_n} / hot={hot_src}，去重后 {unique_n} 篇，推荐 **{len(papers)} 篇**。",
        "",
        f"- **HOT 论文**：{hot_n} 篇（近一年高引用，热门度权重更高）",
        f"- **领域分布**：{domain_bits}",
        "- **阅读建议**：优先看推荐分 ≥ 8.0 且匹配你核心方向的条目；带 🔥HOT 的可作 related work 补课。",
    ]
    return lines


def render_paper_section(idx: int, paper: Dict, detailed: bool) -> List[str]:
    scores = paper.get("scores", {})
    title = paper.get("title", "Untitled")
    note_fn = paper.get("note_filename", "")
    domain = paper.get("matched_domain", "")
    kw = paper.get("matched_keywords", [])[:8]
    summary = (paper.get("summary") or paper.get("abstract") or "").strip()
    rec = scores.get("recommendation", "-")
    rel = scores.get("relevance", "-")
    recency = scores.get("recency", "-")
    pop = scores.get("popularity", "-")
    qual = scores.get("quality", "-")

    wikilink = f"[[{note_fn}|{title[:40]}…]]" if note_fn and len(title) > 40 else (f"[[{note_fn}]]" if note_fn else title)

    lines = [
        f"### {idx}. {title}{_hot_marker(paper)}",
        "",
        f"- **作者**：{_authors_line(paper)}",
        f"- **链接**：[{_primary_link(paper)[0]}]({_primary_link(paper)[1]}) | [PDF]({_pdf_link(paper)})",
        f"- **评分**：{rec}/10（相关性 {rel} | 新近性 {recency} | 热度 {pop} | 质量 {qual}）",
        f"- **匹配领域**：{domain}",
        f"- **匹配关键词**：{', '.join(kw) if kw else '—'}",
    ]
    if note_fn:
        lines.append(f"- **Obsidian 笔记**：[[{note_fn}]]（可用 paper-analyze 生成完整笔记）")

    if detailed and summary:
        # 摘要取前 400 字作为速览
        snippet = summary.replace("\n", " ")
        if len(snippet) > 400:
            snippet = snippet[:400].rstrip() + "…"
        lines.extend(["", f"**摘要速览**：{snippet}"])

    lines.append("")
    return lines


def generate_markdown(data: Dict, date_str: str, top_detailed: int = 3) -> str:
    papers: List[Dict] = data.get("top_papers") or []
    meta = {
        "total_recent": data.get("total_recent"),
        "total_hot": data.get("total_hot"),
        "total_unique": data.get("total_unique"),
        "days": 30,
    }
    windows = data.get("date_windows") or {}
    recent = windows.get("recent_30d") or windows.get("recent_30d", {})

    keywords = []
    for p in papers[:5]:
        keywords.extend(p.get("matched_keywords") or [])
    kw_unique = list(dict.fromkeys(keywords))[:12]

    kw_yaml = ", ".join(kw_unique) if kw_unique else ""
    parts = [
        "---",
        f"keywords: [{kw_yaml}]" if kw_yaml else "keywords: []",
        'tags: ["daily-paper-recommend", "arxiv-daily"]',
        f"date: {date_str}",
        "---",
        "",
        "## 今日概览",
        "",
    ]
    note = data.get("note")
    parts.extend(build_overview(papers, meta))
    if note:
        parts.append("")
        parts.append(f"> ⚠️ {note}")
    if recent:
        parts.append("")
        parts.append(
            f"> 检索窗口：最近 {recent.get('start')} ~ {recent.get('end')}；"
            f"高影响力 {windows.get('past_year', {}).get('start', '?')} ~ {windows.get('past_year', {}).get('end', '?')}"
        )

    parts.extend(["", "---", "", "## 📋 今日推荐", ""])

    for i, paper in enumerate(papers, 1):
        parts.extend(render_paper_section(i, paper, detailed=(i <= top_detailed)))

    parts.extend([
        "---",
        "",
        "## 已有笔记关联",
        "",
    ])
    linked = []
    for p in papers[:8]:
        fn = p.get("note_filename")
        if fn:
            linked.append(f"- [[{fn}]] — {p.get('matched_domain', '')}")
    parts.extend(linked if linked else ["- （今日推荐论文尚未生成独立笔记，可对感兴趣的条目运行 paper-analyze）"])
    parts.append("")

    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(description="Generate Obsidian daily paper note from arxiv JSON")
    parser.add_argument("--input", required=True, help="arxiv_daily JSON output")
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--vault", default="D:/Obsidian", help="Obsidian vault root")
    parser.add_argument("--output", default=None, help="Override output md path")
    parser.add_argument("--top-detailed", type=int, default=3, help="How many papers get abstract snippet")
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    md = generate_markdown(data, args.date, top_detailed=args.top_detailed)

    if args.output:
        out_path = Path(args.output)
    else:
        out_path = Path(args.vault) / "10_Daily" / f"{args.date}论文推荐.md"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    print(f"Wrote: {out_path}")
    print(f"Papers: {len(data.get('top_papers', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
