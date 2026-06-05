#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""领域雷达跨日去重：避免近 N 天内已推送的论文/工具/快讯重复出现。"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

ROOT = Path(__file__).parent


def norm_title(title: str) -> str:
    return re.sub(r"[^a-z0-9\s]", "", (title or "").lower()).strip()


def paper_id(p: Dict) -> str:
    aid = (p.get("arxiv_id") or "").strip()
    if aid:
        return aid
    return norm_title(p.get("title", ""))


def tool_id(t: Dict) -> str:
    return (
        (t.get("full_name") or t.get("name") or t.get("url") or "")
        .lower()
        .strip()
    )


def news_id(n: Dict) -> str:
    url = (n.get("url") or "").strip().lower()
    if url:
        return url
    return norm_title(n.get("title", ""))


def _parse_date(s: str) -> Optional[datetime]:
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(s[:10].replace("/", "-"), fmt)
        except ValueError:
            continue
    return None


def _date_from_merged_filename(path: Path) -> Optional[str]:
    m = re.search(r"radar_merged_(\d{8})\.json$", path.name)
    if not m:
        return None
    raw = m.group(1)
    return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"


def _date_from_daily_filename(path: Path) -> Optional[str]:
    m = re.search(r"(\d{4}-\d{2}-\d{2})领域雷达\.md$", path.name)
    return m.group(1) if m else None


def _extract_arxiv_ids_from_text(text: str) -> List[str]:
    return list(set(re.findall(r"arxiv\.org/abs/(\d{4}\.\d{4,5})", text, re.I)))


def _extract_github_from_text(text: str) -> List[str]:
    found = re.findall(r"github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)", text, re.I)
    return list({x.lower() for x in found})


class RadarDedup:
    """记录并查询已推送到 Obsidian 的条目。"""

    def __init__(
        self,
        history_path: Path,
        lookback_days: int = 14,
    ):
        self.history_path = history_path
        self.lookback_days = lookback_days
        self.data: Dict[str, Any] = {
            "papers": {},
            "tools": {},
            "news": {},
            "bootstrapped": False,
        }
        self._load()

    def _load(self) -> None:
        if self.history_path.exists():
            try:
                raw = json.loads(self.history_path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    self.data.update(raw)
            except (json.JSONDecodeError, OSError):
                pass

    def save(self) -> None:
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        self.history_path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _get_date(self, category: str, item_id: str) -> Optional[str]:
        if not item_id:
            return None
        rec = (self.data.get(category) or {}).get(item_id)
        if rec is None:
            return None
        if isinstance(rec, str):
            return rec
        return rec.get("date")

    def should_skip(
        self,
        category: str,
        item_id: str,
        today: str,
        lookback_days: Optional[int] = None,
    ) -> bool:
        """同日再次运行不去重；近 lookback_days 内其他日期已推送则跳过。"""
        if not item_id:
            return False
        prev = self._get_date(category, item_id)
        if not prev:
            return False
        if prev == today:
            return False
        prev_dt = _parse_date(prev)
        today_dt = _parse_date(today)
        if not prev_dt or not today_dt:
            return False
        delta = (today_dt - prev_dt).days
        lb = lookback_days if lookback_days is not None else self.lookback_days
        return 0 < delta <= lb

    def filter_items(
        self,
        category: str,
        items: List[Dict],
        id_fn: Callable[[Dict], str],
        today: str,
        lookback_days: Optional[int] = None,
    ) -> Tuple[List[Dict], List[Dict]]:
        kept, skipped = [], []
        for item in items:
            iid = id_fn(item)
            if self.should_skip(category, iid, today, lookback_days=lookback_days):
                skipped.append(item)
            else:
                kept.append(item)
        return kept, skipped

    def _mark(self, category: str, item_id: str, date: str, title: str = "") -> None:
        if not item_id:
            return
        bucket = self.data.setdefault(category, {})
        bucket[item_id] = {"date": date, "title": title[:120] if title else ""}

    def record_delivery(
        self,
        date: str,
        papers: List[Dict],
        tools: List[Dict],
        news: List[Dict],
    ) -> None:
        for p in papers:
            self._mark("papers", paper_id(p), date, p.get("title", ""))
        for t in tools:
            self._mark("tools", tool_id(t), date, t.get("full_name") or t.get("name", ""))
        for n in news:
            self._mark("news", news_id(n), date, n.get("title", ""))
        self.data["last_delivery_date"] = date
        self.data["last_updated"] = datetime.now().isoformat()

    def bootstrap(self, project_root: Path, vault: Path) -> None:
        if self.data.get("bootstrapped"):
            return

        for path in project_root.glob("radar_merged_*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            d = payload.get("target_date") or _date_from_merged_filename(path)
            if not d:
                continue
            self.record_delivery(
                d,
                payload.get("papers") or [],
                payload.get("tools") or [],
                payload.get("news") or [],
            )

        daily_dir = vault / "10_Daily"
        if daily_dir.is_dir():
            for md in daily_dir.glob("*领域雷达.md"):
                d = _date_from_daily_filename(md)
                if not d:
                    continue
                try:
                    text = md.read_text(encoding="utf-8")
                except OSError:
                    continue
                for aid in _extract_arxiv_ids_from_text(text):
                    self._mark("papers", aid, d, "")
                for repo in _extract_github_from_text(text):
                    self._mark("tools", repo.lower(), d, repo)

        self.data["bootstrapped"] = True
        self.save()


def load_dedup_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    import yaml

    path = config_path or ROOT / "config" / "radar_dedup.yaml"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def apply_paper_dedup(
    papers_json_path: Path,
    dedup: RadarDedup,
    today: str,
    keep_n: int,
) -> Dict[str, Any]:
    payload = json.loads(papers_json_path.read_text(encoding="utf-8"))
    papers = payload.get("top_papers") or []
    kept, skipped = dedup.filter_items("papers", papers, paper_id, today)
    payload["top_papers"] = kept[:keep_n]
    payload["dedup"] = {
        "skipped_papers": len(skipped),
        "skipped_titles": [p.get("title", "")[:80] for p in skipped[:8]],
        "kept_after_dedup": len(payload["top_papers"]),
    }
    papers_json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return payload["dedup"]


def apply_tools_dedup(
    tools_json_path: Path,
    dedup: RadarDedup,
    today: str,
    lookback_days: Optional[int] = None,
) -> Dict[str, Any]:
    payload = json.loads(tools_json_path.read_text(encoding="utf-8"))
    items = payload.get("items") or []
    kept, skipped = dedup.filter_items(
        "tools", items, tool_id, today, lookback_days=lookback_days
    )
    payload["items"] = kept
    payload["dedup"] = {"skipped_tools": len(skipped)}
    tools_json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return payload["dedup"]


def apply_news_dedup(
    news_json_path: Path,
    dedup: RadarDedup,
    today: str,
    lookback_days: Optional[int] = None,
    min_keep: int = 2,
) -> Dict[str, Any]:
    payload = json.loads(news_json_path.read_text(encoding="utf-8"))
    items = payload.get("items") or []
    kept, skipped = dedup.filter_items(
        "news", items, news_id, today, lookback_days=lookback_days
    )
    # 快讯源少：严格去重后若不足 min_keep，用次新条目补位（避免日报无快讯）
    if len(kept) < min_keep and skipped:
        need = min_keep - len(kept)
        kept.extend(skipped[:need])
    payload["items"] = kept
    payload["dedup"] = {"skipped_news": len(skipped)}
    news_json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return payload["dedup"]
