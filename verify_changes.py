#!/usr/bin/env python3
"""验证 priority 加权与顶会 DBLP 映射。"""

import argparse
import sys
import time
from pathlib import Path

from arxiv_daily import calculate_relevance_score, RELEVANCE_PRIORITY_BASELINE, load_research_config
from conf_search import DBLP_VENUES, VENUE_TO_CATEGORIES, search_dblp_conference


def test_priority_weighting():
    domains = {
        "高优先级域": {
            "keywords": ["LLM evaluation"],
            "arxiv_categories": ["cs.CL"],
            "priority": 10,
        },
        "低优先级域": {
            "keywords": ["LLM evaluation"],
            "arxiv_categories": ["cs.CL"],
            "priority": 5,
        },
    }
    paper = {
        "title": "A Study on LLM Evaluation for Interviews",
        "summary": "We propose LLM evaluation methods.",
        "categories": ["cs.CL"],
    }
    score_high, domain_high, _ = calculate_relevance_score(
        paper, {"高优先级域": domains["高优先级域"]}, []
    )
    score_low, domain_low, _ = calculate_relevance_score(
        paper, {"低优先级域": domains["低优先级域"]}, []
    )
    assert score_high > score_low, f"高优先级应更高: {score_high} vs {score_low}"
    assert domain_high == "高优先级域"
    print(f"[OK] priority 加权: 高={score_high:.2f}, 低={score_low:.2f} (baseline={RELEVANCE_PRIORITY_BASELINE})")


def test_new_venues_registered():
    for venue in ("NAACL", "CHI", "FAccT"):
        assert venue in DBLP_VENUES, f"缺少 DBLP 映射: {venue}"
        assert venue in VENUE_TO_CATEGORIES, f"缺少分类映射: {venue}"
        info = DBLP_VENUES[venue]
        assert info.get("toc") or info.get("venue_query"), f"{venue} 无查询方式"
    print("[OK] NAACL / CHI / FAccT 已注册到 DBLP_VENUES 与 VENUE_TO_CATEGORIES")


def test_priority_with_real_config():
    config_path = Path(__file__).parent / "config" / "research_interests.yaml"
    config = load_research_config(str(config_path))
    paper = {
        "title": "LLM-as-Judge for Automated Interview Scoring and Personality Assessment",
        "summary": (
            "We study LLM evaluation, inter-rater reliability, and bias mitigation "
            "in competency scoring for AI interviews."
        ),
        "categories": ["cs.CL", "cs.AI"],
    }
    score, domain, keywords = calculate_relevance_score(
        paper, config["research_domains"], config.get("excluded_keywords", [])
    )
    assert score > 0 and domain, "真实配置下应匹配到至少一个研究域"
    print(f"[OK] 真实配置匹配: 域={domain}, 相关性={score:.2f}, 关键词数={len(keywords)}")


def test_dblp_live(venue: str, year: int):
    print(f"\n[Live] DBLP 探测 {venue} {year} ...")
    papers = search_dblp_conference(venue, year, max_results=5, max_retries=2)
    assert papers, f"{venue} 未返回论文（可能 DBLP 限流，请稍后重试）"
    print(f"[OK] {venue} 返回 {len(papers)} 篇（示例: {papers[0]['title'][:60]}...）")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live-dblp", action="store_true", help="额外调用 DBLP API（单会议、少量结果）")
    args = parser.parse_args()

    test_priority_weighting()
    test_new_venues_registered()
    test_priority_with_real_config()
    print("\n本地单元验证全部通过。")

    if args.live_dblp:
        time.sleep(3)
        for venue in ("NAACL", "CHI", "FAccT"):
            test_dblp_live(venue, 2024)
            time.sleep(5)
    return 0


if __name__ == "__main__":
    sys.exit(main())
