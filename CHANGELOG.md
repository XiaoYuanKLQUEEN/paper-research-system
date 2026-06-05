# 变更日志

> 按时间倒序。历史 commit message 不够精确时，以本文件为准检索功能变更。

格式遵循 [`docs/COMMIT_CONVENTION.md`](docs/COMMIT_CONVENTION.md)。  
协作流程见 [`docs/GITHUB_WORKFLOW.md`](docs/GITHUB_WORKFLOW.md)。

---

## [2026-06-05] GitHub 开发流程文档

### `待推送` — 文档(流程): 新增 GitHub 开发流程与 Cursor Agent 规则

- `docs/GITHUB_WORKFLOW.md`: 完整开发循环（验证→确认最终版→精确 commit→代理 push）
- `.cursor/rules/github-workflow.mdc`: Agent 自动遵循的 alwaysApply 规则
- README / COMMIT_CONVENTION: 链接流程文档

---

## [2026-06-05] 领域雷达 v1 — 一键推送 / 去重 / 小白深读

### `2cdbb9d` — 实际变更（原 message 尚可，可保留）

**应用**: `push-to-github.bat`  
**内容**: GitHub HTTPS 443 不可达时，经本地代理 `127.0.0.1:7897` 执行 `git push`

---

### `d3b4550` — 实际变更（原 message 仅覆盖 README，未描述代码）

**模块**: 文档  
**内容**:

- 修复 `README.md` 合并冲突标记（`<<<<<<< HEAD`）
- 补充：一键推送、跨日去重、深读格式、目录结构、FAQ

> 注：同批次功能代码已在 `f74dde9` 合并进 main，README 此 commit 才文档化。

---

### `f74dde9` — Merge（应拆分为多条 commit，见下表）

合并 `66c0b05` 与远程 `c75dac9`，包含**领域雷达完整实现**。  
若按规范应拆为以下独立 commit：

| 应有 message | 文件 / 模块 | 具体功能 |
|-------------|------------|---------|
| `功能(雷达): 新增 run_radar 一键流水线` | `run_radar.py` | arxiv → news → tools → merge → 生成 Obsidian |
| `功能(新闻): RSS 权威源抓取与 fallback` | `news_digest.py`, `config/news_sources.yaml`, `config/news_fallback.yaml` | 每日 2–3 条快讯 |
| `功能(工具): GitHub 开源 AI 工具扫描` | `tools_scan.py`, `config/tools_discovery.yaml`, `config/tools_fallback.yaml` | 评测相关排序；⭐≥50；禁用 paper_link 0star |
| `功能(合并): 论文/工具/快讯配额约 25 条` | `merge_radar.py`, `config/radar.yaml` | papers 为主，tools≤5，news 2–3 |
| `功能(日报): Obsidian 领域雷达 Markdown 生成` | `generate_radar_daily.py` | 深读 4 + 补课 1 + 简读 + 工具卡片 + 快讯中文 |
| `功能(深读): 高价值论文中文 profile 档案` | `config/deep_analysis_profiles.yaml` | arxiv_id → 一句话/核心发现/关联 |
| `功能(配图): 深读前 arXiv 图片提取` | `radar_images.py` | 超时跳过，不阻断日报 |
| `功能(去重): 跨日推送去重与历史库` | `radar_dedup.py`, `config/radar_dedup.yaml`, `data/radar_delivered.json` | 论文14d/工具7d/快讯3d |
| `功能(推送): 双击一键推送到 Obsidian` | `push_today_radar.py`, `推送今日领域雷达.bat` | 去重 + 自动打开 vault |
| `优化(工具): min_stars 50 与合并二次过滤` | `tools_scan.py`, `merge_radar.py` | 杜绝 0 star 进榜 |
| `优化(深读): 小白向摘要解析与 Top4 profile` | `generate_radar_daily.py` | 针对什么→痛点→方法→结果 |
| `优化(arxiv): priority 加权与 NAACL/CHI/FAccT DBLP` | `arxiv_daily.py`, `conf_search.py` | 评分与顶会映射 |
| `配置: gitignore 忽略去重历史` | `.gitignore` | `data/radar_delivered.json` |

---

### `66c0b05` — 实际变更（❌ 原 message「加上了工具和新闻」严重不准确）

**实际**: 领域雷达 **初版全套**（见上表），远不止「工具+新闻」。  
**涉及**: 21 文件，+2081 行 — 含 `run_radar`、`news_digest`、`tools_scan`、`merge_radar`、`generate_radar_daily` 等。

**建议检索关键词**: `run_radar`, `generate_radar_daily`, `merge_radar`, `news_digest`, `tools_scan`

---

### `c75dac9` — 实际变更

**模块**: 文档  
**内容**: README 重写为详细使用指南（安装、配置、各脚本参数、工作流示例）

---

## [更早]

| Commit | 说明 |
|--------|------|
| `136f830` / `00aacb8` | 项目初始化、research_interests 配置 |
| `e9a149e` / `f25083c` | 初始仓库 |
