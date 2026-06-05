#!/usr/bin/env python3
"""为雷达深读论文提取 arXiv 图片，返回 Obsidian 可嵌入的文件名列表。"""
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

VAULT_IMAGES = Path("D:/Obsidian/20_Research/Papers/images")
SCRIPT = Path(__file__).parent / "extract_images.py"


def ensure_images(arxiv_id: str, max_images: int = 3) -> List[str]:
    if not arxiv_id:
        return []
    out_dir = VAULT_IMAGES / arxiv_id
    index = VAULT_IMAGES / f"{arxiv_id}_index.md"
    pngs = sorted(out_dir.glob("*.png")) if out_dir.exists() else []
    if len(pngs) < 1 and SCRIPT.exists():
        out_dir.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(
                [sys.executable, str(SCRIPT), arxiv_id, str(out_dir), str(index)],
                capture_output=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            # 配图超时不阻断日报生成
            pass
        pngs = sorted(out_dir.glob("*.png"))
    # Obsidian 按文件名全局解析（与 6/2、6/3 一致）
    return [p.name for p in pngs[:max_images]]


def enrich_papers_with_images(papers: List[Dict], top_n: int = 4) -> None:
    for p in papers[:top_n]:
        aid = p.get("arxiv_id")
        p["_images"] = ensure_images(aid) if aid else []
