#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键运行：论文 + 新闻 + 工具 → merge → 生成 Obsidian 日报。"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent


def run(cmd: list) -> int:
    print(">>", " ".join(cmd), file=sys.stderr)
    return subprocess.call(cmd, cwd=str(ROOT))


def main():
    parser = argparse.ArgumentParser(description="Run full domain radar pipeline")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument(
        "--config",
        default="D:/Obsidian/99_System/Config/research_interests.yaml",
    )
    parser.add_argument("--vault", default="D:/Obsidian")
    parser.add_argument("--paper-top-n", type=int, default=22)
    parser.add_argument("--skip-hot", action="store_true", default=True)
    parser.add_argument("--no-arxiv", action="store_true", help="Skip arxiv if API down")
    args = parser.parse_args()

    tag = args.date.replace("-", "")
    papers_out = ROOT / f"arxiv_filtered_{tag}.json"
    news_out = ROOT / "news_raw.json"
    tools_out = ROOT / "tools_raw.json"
    merged_out = ROOT / f"radar_merged_{tag}.json"

    if not args.no_arxiv:
        cmd = [
            sys.executable,
            "arxiv_daily.py",
            "--config",
            args.config,
            "--target-date",
            args.date,
            "--top-n",
            str(args.paper_top_n),
            "--output",
            str(papers_out),
        ]
        if args.skip_hot:
            cmd.append("--skip-hot-papers")
        if run(cmd) != 0:
            print("arxiv_daily failed, trying fallback verify_arxiv.json", file=sys.stderr)
            pool_script = ROOT / "build_papers_pool.py"
            if pool_script.exists():
                subprocess.call([sys.executable, str(pool_script)], cwd=str(ROOT))
            pool = ROOT / "papers_pool.json"
            if pool.exists():
                papers_out.write_text(pool.read_text(encoding="utf-8"), encoding="utf-8")
            elif (ROOT / "verify_arxiv.json").exists():
                papers_out.write_text(
                    (ROOT / "verify_arxiv.json").read_text(encoding="utf-8"), encoding="utf-8"
                )
            else:
                return 1
    else:
        if not papers_out.exists():
            print("Missing papers json", file=sys.stderr)
            return 1

    if run([sys.executable, "news_digest.py", "--output", str(news_out)]) != 0:
        return 1

    if run([
        sys.executable,
        "tools_scan.py",
        "--papers-json",
        str(papers_out),
        "--output",
        str(tools_out),
    ]) != 0:
        return 1

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

    daily = Path(args.vault) / "10_Daily" / f"{args.date}领域雷达.md"
    return run([
        sys.executable,
        "generate_radar_daily.py",
        "--input",
        str(merged_out),
        "--output",
        str(daily),
        "--date",
        args.date,
    ])


if __name__ == "__main__":
    raise SystemExit(main())
