#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键推送今日领域雷达到 Obsidian（含跨日去重）。"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from radar_dedup import (  # noqa: E402
    RadarDedup,
    apply_news_dedup,
    apply_paper_dedup,
    apply_tools_dedup,
    load_dedup_config,
)


def run(cmd: list) -> int:
    print(">>", " ".join(cmd), file=sys.stderr)
    return subprocess.call(cmd, cwd=str(ROOT))


def open_in_obsidian(path: Path) -> None:
    if not path.exists():
        return
    try:
        if sys.platform == "win32":
            import os

            os.startfile(str(path))  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except OSError as exc:
        print(f"无法自动打开文件: {exc}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="推送今日领域雷达到 Obsidian")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument(
        "--config",
        default="D:/Obsidian/99_System/Config/research_interests.yaml",
    )
    parser.add_argument("--vault", default="D:/Obsidian")
    parser.add_argument("--paper-top-n", type=int, default=22)
    parser.add_argument("--skip-hot", action="store_true", default=True)
    parser.add_argument("--no-arxiv", action="store_true")
    parser.add_argument("--no-dedup", action="store_true", help="关闭跨日去重")
    parser.add_argument("--no-open", action="store_true", help="完成后不打开 Obsidian 笔记")
    args = parser.parse_args()

    dcfg = load_dedup_config()
    lookback = int(dcfg.get("lookback_days", 14))
    tool_lookback = int(dcfg.get("tool_lookback_days", lookback))
    news_lookback = int(dcfg.get("news_lookback_days", 3))
    min_news = int(dcfg.get("min_news_after_dedup", 2))
    fetch_buffer = int(dcfg.get("paper_fetch_buffer", 45))
    history_path = ROOT / dcfg.get("history_file", "data/radar_delivered.json")

    tag = args.date.replace("-", "")
    papers_out = ROOT / f"arxiv_filtered_{tag}.json"
    news_out = ROOT / "news_raw.json"
    tools_out = ROOT / "tools_raw.json"
    merged_out = ROOT / f"radar_merged_{tag}.json"
    daily = Path(args.vault) / "10_Daily" / f"{args.date}领域雷达.md"

    dedup: RadarDedup | None = None
    dedup_stats: dict = {}
    if not args.no_dedup:
        dedup = RadarDedup(history_path, lookback_days=lookback)
        dedup.bootstrap(ROOT, Path(args.vault))
        print(
            f"[去重] 近 {lookback} 天内已推送条目将自动跳过（历史库: {history_path}）",
            file=sys.stderr,
        )

    fetch_n = fetch_buffer if dedup else args.paper_top_n

    if not args.no_arxiv:
        cmd = [
            sys.executable,
            "arxiv_daily.py",
            "--config",
            args.config,
            "--target-date",
            args.date,
            "--top-n",
            str(fetch_n),
            "--output",
            str(papers_out),
        ]
        if args.skip_hot:
            cmd.append("--skip-hot-papers")
        if run(cmd) != 0:
            print("arxiv_daily failed, trying fallback cache", file=sys.stderr)
            yesterday = (
                datetime.strptime(args.date, "%Y-%m-%d") - timedelta(days=1)
            ).strftime("%Y%m%d")
            prev = ROOT / f"arxiv_filtered_{yesterday}.json"
            pool = ROOT / "papers_pool.json"
            if prev.exists() and prev.stat().st_size > 100:
                papers_out.write_text(prev.read_text(encoding="utf-8"), encoding="utf-8")
                print(f"Using previous day arXiv cache: {prev}", file=sys.stderr)
            elif pool.exists():
                papers_out.write_text(pool.read_text(encoding="utf-8"), encoding="utf-8")
            elif (ROOT / "verify_arxiv.json").exists():
                papers_out.write_text(
                    (ROOT / "verify_arxiv.json").read_text(encoding="utf-8"),
                    encoding="utf-8",
                )
            else:
                return 1
    elif not papers_out.exists():
        print("Missing papers json", file=sys.stderr)
        return 1

    if dedup and papers_out.exists():
        paper_dedup = apply_paper_dedup(
            papers_out, dedup, args.date, keep_n=args.paper_top_n
        )
        dedup_stats["papers"] = paper_dedup
        print(
            f"[去重] 论文: 跳过 {paper_dedup.get('skipped_papers', 0)} 篇，"
            f"保留 {paper_dedup.get('kept_after_dedup', 0)} 篇",
            file=sys.stderr,
        )

    if run([sys.executable, "news_digest.py", "--output", str(news_out)]) != 0:
        return 1

    if dedup and news_out.exists():
        nd = apply_news_dedup(
            news_out, dedup, args.date,
            lookback_days=news_lookback,
            min_keep=min_news,
        )
        dedup_stats["news"] = nd
        print(f"[去重] 快讯: 跳过 {nd.get('skipped_news', 0)} 条", file=sys.stderr)

    if run([
        sys.executable,
        "tools_scan.py",
        "--papers-json",
        str(papers_out),
        "--output",
        str(tools_out),
    ]) != 0:
        return 1

    if dedup and tools_out.exists():
        td = apply_tools_dedup(
            tools_out, dedup, args.date, lookback_days=tool_lookback
        )
        dedup_stats["tools"] = td
        print(f"[去重] 工具: 跳过 {td.get('skipped_tools', 0)} 个", file=sys.stderr)

    if run([
        sys.executable,
        "merge_radar.py",
        "--papers",
        str(papers_out),
        "--tools",
        str(tools_out),
        "--news",
        str(news_out),
        "--output",
        str(merged_out),
        "--date",
        args.date,
    ]) != 0:
        return 1

    # 把去重统计写入 merged，供日报展示
    if dedup_stats:
        merged = json.loads(merged_out.read_text(encoding="utf-8"))
        merged.setdefault("meta", {})["dedup"] = dedup_stats
        merged_out.write_text(
            json.dumps(merged, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    if run([
        sys.executable,
        "generate_radar_daily.py",
        "--input",
        str(merged_out),
        "--output",
        str(daily),
        "--date",
        args.date,
    ]) != 0:
        return 1

    if dedup:
        merged = json.loads(merged_out.read_text(encoding="utf-8"))
        dedup.record_delivery(
            args.date,
            merged.get("papers") or [],
            merged.get("tools") or [],
            merged.get("news") or [],
        )
        dedup.save()
        print(f"[去重] 已记录今日推送 → {history_path}", file=sys.stderr)

    print(f"\n[完成] 已生成: {daily}", file=sys.stderr)
    print(f"   分配: {json.loads(merged_out.read_text(encoding='utf-8')).get('allocation')}", file=sys.stderr)

    if not args.no_open:
        open_in_obsidian(daily)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
