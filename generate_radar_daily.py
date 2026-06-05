#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 radar_merged.json 生成 Obsidian 领域雷达（试刊版）。
深读区：评分最高的 4 篇；其余论文为简读；工具与新闻为中文快讯。
"""

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List


def _authors(p: Dict) -> str:
    raw = p.get("authors") or []
    names = []
    for a in raw:
        if isinstance(a, str):
            names.append(a)
        elif isinstance(a, dict):
            names.append(a.get("name") or "")
    names = [n for n in names if n]
    if not names:
        return "（待补充）"
    return ", ".join(names[:5]) + (f" 等 {len(names)} 人" if len(names) > 5 else "")


def _link(p: Dict) -> tuple:
    aid = p.get("arxiv_id")
    if aid:
        return "arXiv", f"https://arxiv.org/abs/{aid}", f"https://arxiv.org/pdf/{aid}v1"
    url = p.get("url", "#")
    return "链接", url, url


def _scores_line(p: Dict) -> str:
    s = p.get("scores") or {}
    if not s:
        return ""
    return (
        f"{s.get('recommendation', '-')}/10"
        f"（相关 {s.get('relevance', '-')} | 新 {s.get('recency', '-')} "
        f"| 热 {s.get('popularity', '-')} | 质 {s.get('quality', '-')}）"
    )


def _note_link(p: Dict) -> str:
    fn = p.get("note_filename")
    return f"[[{fn}]]" if fn else ""


def _zh_news_flash(item: Dict) -> str:
    """英文源 → 中文快讯（固定映射 + 摘要；联网后可换 LLM 润色）。"""
    title = item.get("title", "")
    summary_en = (item.get("summary_en") or "").strip()
    source = item.get("source", "")
    tier = item.get("tier", "official")
    tier_zh = {"official": "官方", "media": "权威媒体"}.get(tier, "资讯")

    zh_map = {
        "OpenAI": (
            "【官方】OpenAI 动态入口",
            "关注新模型卡、安全报告与 API 变更；做 LLM-as-Judge 实验前建议核对默认 judge 模型版本。",
        ),
        "DeepMind": (
            "【官方】Google DeepMind 研究博客",
            "Gemini、Agent 与科学计算方向更新；多模态与推理类进展可能影响你的评测基线选择。",
        ),
        "Hugging Face": (
            "【官方】Hugging Face 博客 / Hub",
            "开源权重、数据集与评测脚本集中发布；适合快速复现 bias / benchmark 实验。",
        ),
    }
    zh_title, zh_body = title, summary_en
    for key, (zt, zb) in zh_map.items():
        if key in source and not title.strip():
            zh_title, zh_body = zt, zb
            break
    if summary_en:
        zh_body = summary_en[:300] + ("…" if len(summary_en) > 300 else "")
    elif not zh_body:
        for key, (zt, zb) in zh_map.items():
            if key in source:
                zh_title, zh_body = zt, zb
                break

    return "\n".join([
        f"**{tier_zh} · {source}**",
        f"- **{zh_title}**",
        f"- {zh_body}",
        f"- [阅读原文]({item.get('url', '#')})",
    ])


def _research_blurb(p: Dict) -> str:
    domain = p.get("matched_domain", "")
    summary = (p.get("summary") or p.get("abstract") or "").strip()
    if not summary:
        return f"- **关联**：匹配域「{domain}」；建议结合摘要精读原文。"
    snippet = re.sub(r"\s+", " ", summary)[:350]
    hints = []
    sl = summary.lower()
    if any(k in sl for k in ("bias", "judge", "evaluation", "scoring")):
        hints.append("与 LLM 评估/偏差诊断相关")
    if any(k in sl for k in ("agent", "multi-agent")):
        hints.append("与多智能体流水线相关")
    if any(k in sl for k in ("personality", "mbti", "big five")):
        hints.append("与人格推断相关")
    if any(k in sl for k in ("interview", "video", "audio", "multimodal")):
        hints.append("与多模态/交互评估相关")
    hint = "；".join(hints) if hints else f"匹配域「{domain}」"
    return f"- **摘要要点**：{snippet}…\n- **与你研究**：{hint}。"


def render_deep(p: Dict, idx: int) -> List[str]:
    label, arxiv, pdf = _link(p)
    title = p.get("title", "")
    lines = [
        f"### {idx}. {title}",
        "",
        f"- **作者**：{_authors(p)}",
        f"- **链接**：[{label}]({arxiv}) | [PDF]({pdf})",
        f"- **评分**：{_scores_line(p)}",
        f"- **匹配领域**：{p.get('matched_domain', '')}",
        f"- **笔记**：{_note_link(p)}",
        "",
        "#### 研究问题",
        "",
        _research_blurb(p).replace("**摘要要点**", "本文关注").replace("**与你研究**", "**关联**"),
        "",
        "#### 与你的研究关联",
        "",
    ]
    domain = p.get("matched_domain", "")
    if "多智能体" in domain:
        lines.append("- 🔥 可对照你的多智能体评分/去偏设计：信息流、早停高置信步骤、评委并行。")
    elif "LLM" in domain or "评估" in domain:
        lines.append("- 🔥 与 LLM-as-Judge、自动化评分、rubric 设计直接相关。")
    elif "人格" in domain or "多模态" in domain:
        lines.append("- 🎯 可作为人格/多模态面试评估的 related work 或边界讨论。")
    else:
        lines.append("- 📎 建议速读摘要后决定是否进入精读队列。")
    lines.append("")
    return lines


def render_brief(p: Dict, idx: int) -> List[str]:
    label, arxiv, _ = _link(p)
    title = p.get("title", "")
    summary = (p.get("summary") or p.get("abstract") or "")
    one = re.sub(r"\s+", " ", summary)[:200] + ("…" if len(summary) > 200 else "")
    return [
        f"#### {idx}. {title}",
        "",
        f"- **评分**：{_scores_line(p)} | **域**：{p.get('matched_domain', '')}",
        f"- **链接**：[{label}]({arxiv}) | {_note_link(p)}",
        f"- **一句**：{one}",
        "",
    ]


def render_tool(t: Dict, idx: int) -> List[str]:
    return [
        f"| {idx} | [{t.get('full_name', t.get('name'))}]({t.get('url', '#')}) "
        f"| ⭐{t.get('stars', 0)} | {(t.get('description') or '')[:80]}… "
        f"| {t.get('source', '')} |",
    ]


def generate(data: Dict, date_str: str) -> str:
    papers: List[Dict] = data.get("papers") or []
    tools: List[Dict] = data.get("tools") or []
    news: List[Dict] = data.get("news") or []
    alloc = data.get("allocation") or {}

    papers_sorted = sorted(
        papers,
        key=lambda x: (x.get("scores") or {}).get("recommendation", 0),
        reverse=True,
    )
    deep_n = min(4, len(papers_sorted))
    deep = papers_sorted[:deep_n]
    brief = papers_sorted[deep_n:]

    kw = []
    for p in papers_sorted[:6]:
        kw.extend(p.get("matched_keywords") or [])
    kw = list(dict.fromkeys(kw))[:10]

    parts = [
        "---",
        f"keywords: [{', '.join(kw)}]",
        'tags: ["llm-generated", "domain-radar"]',
        f"date: {date_str}",
        "---",
        "",
        "## 今日概览",
        "",
        f"今日 **领域雷达** 共 **{alloc.get('total', len(papers)+len(tools)+len(news))}** 条："
        f"论文 **{alloc.get('papers', len(papers))}**、开源工具 **{alloc.get('tools', len(tools))}**、"
        f"权威快讯 **{alloc.get('news', len(news))}**（英文源，下文为中文快讯）。",
        "",
        "- **阅读策略**：先读 🔥 深读区（Top 4），简读区按评分扫标题；工具表挑 1 个可 clone 的 repo 试跑。",
        "- **说明**：论文由 `arxiv_daily` 评分排序；工具来自 GitHub 开源检索；新闻仅官方/顶媒 RSS。",
        "",
        "---",
        "",
        f"## 🔥 论文深读（{deep_n} 篇）",
        "",
    ]

    for i, p in enumerate(deep, 1):
        parts.extend(render_deep(p, i))

    parts.extend([
        "---",
        "",
        f"## 📋 论文简读（{len(brief)} 篇）",
        "",
    ])
    for i, p in enumerate(brief, deep_n + 1):
        parts.extend(render_brief(p, i))

    parts.extend([
        "---",
        "",
        f"## 🛠 开源工具 / 项目（{len(tools)} 条）",
        "",
        "| # | 项目 | Stars | 简介 | 来源 |",
        "|---|------|-------|------|------|",
    ])
    for i, t in enumerate(tools, 1):
        parts.extend(render_tool(t, i))

    parts.extend([
        "",
        "---",
        "",
        f"## 📰 领域快讯（{len(news)} 条）",
        "",
    ])
    for i, n in enumerate(news, 1):
        parts.append(f"### 快讯 {i}")
        parts.append("")
        parts.append(_zh_news_flash(n))
        parts.append("")

    parts.extend([
        "---",
        "",
        "## 已有笔记关联",
        "",
    ])
    for p in deep[:3]:
        fn = p.get("note_filename")
        if fn:
            parts.append(f"- [[{fn}]] — {p.get('matched_domain', '')}")

    parts.append("")
    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--date", required=True)
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    md = generate(data, args.date)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")
    print(f"Wrote: {out}")
    print(f"Allocation: {data.get('allocation')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
