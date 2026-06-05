# Paper Research System

> LLM 评估人类职业素养 / 人格方向的论文自动追踪系统  
> 每日搜索 arXiv + Semantic Scholar，生成 Obsidian 领域雷达（论文 + 开源工具 + 权威快讯）

---

## 功能一览

| 模块 | 脚本 | 说明 |
|------|------|------|
| **一键推送（推荐）** | `推送今日领域雷达.bat` | 双击 → 抓取 → 去重 → 生成 Obsidian 日报并自动打开 |
| 领域雷达流水线 | `push_today_radar.py` / `run_radar.py` | 论文 + 工具 + 快讯 → 约 25 条 |
| 跨日去重 | `radar_dedup.py` | 近 N 天内已推送的论文/工具/快讯不重复出现 |
| 论文搜索 | `arxiv_daily.py` | arXiv + Semantic Scholar，四维评分排序 |
| 日报生成 | `generate_radar_daily.py` | 小白向深读（一句话 + 核心发现 + 配图 + 研究关联） |
| 新闻快讯 | `news_digest.py` | 权威 RSS，2–3 条/天（中文在生成阶段） |
| 开源工具 | `tools_scan.py` | GitHub 检索，仅 ⭐≥50，不含商业产品 |
| 深读档案 | `config/deep_analysis_profiles.yaml` | 高价值论文预设中文深读 |
| 图片提取 | `extract_images.py` | 从 arXiv 源码 / PDF 提取论文配图 |
| 顶会搜索 | `conf_search.py` | DBLP + Semantic Scholar 顶会论文 |

---

## 一键推送（最常用）

### Windows：双击运行

```
推送今日领域雷达.bat
```

### 命令行

```bash
python push_today_radar.py
```

**自动完成：**

1. 抓取今日 arXiv 论文（多抓候选，去重后保留约 22 篇）
2. 抓取开源 AI 工具（GitHub，⭐≥50）与权威快讯（RSS）
3. **跨日去重**（论文 14 天 / 工具 7 天 / 快讯 3 天，可配置）
4. 合并约 **25 条**，生成 Obsidian 笔记
5. 自动打开 `D:/Obsidian/10_Daily/YYYY-MM-DD领域雷达.md`

**输出格式（对齐 6/2、6/3 手写标准）：**

- 深读 4 篇：中文一句话 + 小白向核心发现（针对什么 → 痛点 → 方法 → 结果）+ 配图 + 研究关联
- 补课 1 篇：高影响力固定深读（如招聘公平性 2506.10922）
- 简读区 + 工具卡片（中文简介）+ 快讯（引人入胜一句话）

---

## 快速开始

### 1. 安装依赖

```bash
pip install PyYAML requests PyMuPDF
```

### 2. 配置研究兴趣

编辑 `D:/Obsidian/99_System/Config/research_interests.yaml`（或项目内 `config/research_interests.yaml`）：

```yaml
research_domains:
  "LLM评估与评分":
    keywords:
      - "llm-as-a-judge"
      - "scoring bias"
    arxiv_categories:
      - "cs.CL"
      - "cs.AI"
    priority: 10

excluded_keywords:
  - "medical image"
```

### 3. 配置 Obsidian 路径

`push_today_radar.py` 默认：

- Vault：`D:/Obsidian`
- 研究配置：`D:/Obsidian/99_System/Config/research_interests.yaml`

可通过参数修改：

```bash
python push_today_radar.py --vault "D:/Obsidian" --config "path/to/research_interests.yaml"
```

---

## 领域雷达工作流

```bash
# 完整流水线（与一键推送相同，不自动打开 Obsidian）
python run_radar.py --date 2026-06-05

# arXiv 限流时跳过重新抓取，用本地缓存
python run_radar.py --date 2026-06-05 --no-arxiv

# 关闭跨日去重
python push_today_radar.py --no-dedup
```

**数据流：**

```
arxiv_daily.py → news_digest.py → tools_scan.py
       ↓              ↓                ↓
   [radar_dedup 跨日去重]
       ↓
  merge_radar.py → generate_radar_daily.py → Obsidian 10_Daily/
```

---

## 跨日去重

配置：`config/radar_dedup.yaml`

| 类型 | 默认窗口 | 标识 |
|------|----------|------|
| 论文 | 14 天 | arXiv ID / 标题 |
| 工具 | 7 天 | GitHub `owner/repo` |
| 快讯 | 3 天 | URL |

- **同日多次运行**：允许刷新，不会把当天内容全部滤掉
- **历史库**：`data/radar_delivered.json`（首次运行从已有 `radar_merged_*.json` 与 Obsidian 历史日报自动导入）
- 日报「今日概览」会显示去重统计

---

## 深读档案

高价值论文在 `config/deep_analysis_profiles.yaml` 中预设中文深读（一句话、核心发现、研究关联）。  
无档案的论文走 `generate_radar_daily.py` 内摘要解析 + 小白向模板。

新增深读：在 yaml 中按 arxiv_id 添加 profile 即可。

---

## 各脚本详解

### `arxiv_daily.py` — 每日论文搜索

```bash
python arxiv_daily.py \
  --config config/research_interests.yaml \
  --target-date 2026-06-05 \
  --top-n 22 \
  --skip-hot-papers \
  --output arxiv_filtered_20260605.json
```

**工作流**：arXiv API（近 30 天）→ Semantic Scholar 热门 → 合并去重 → 关键词评分 → 排序。

> 网络慢时自动切换镜像；429 限流时 `push_today_radar.py` 会回退昨日缓存。

### `extract_images.py` — 提取论文图片

```bash
python extract_images.py "2606.06416" "D:/Obsidian/20_Research/Papers/images/2606.06416" "index.md"
```

### `conf_search.py` — 顶会论文

```bash
python conf_search.py --year 2025 --conferences "ACL,CHI,FAccT" --top-n 15 --config conf-papers.yaml
```

### `cleanup_images.py` — 清理旧图片

```bash
python cleanup_images.py
```

---

## 目录结构

```
paper-research-system/
├── 推送今日领域雷达.bat      # 双击一键推送
├── push_today_radar.py       # 一键推送（含去重 + 打开 Obsidian）
├── run_radar.py              # 领域雷达流水线
├── radar_dedup.py            # 跨日去重
├── arxiv_daily.py            # arXiv 搜索
├── generate_radar_daily.py   # Obsidian 日报生成
├── news_digest.py            # RSS 快讯
├── tools_scan.py             # GitHub 工具扫描
├── merge_radar.py            # 合并约 25 条
├── radar_images.py           # 深读配图
├── extract_images.py
├── conf_search.py
├── config/
│   ├── research_interests.yaml
│   ├── radar.yaml            # 配额（论文/工具/快讯）
│   ├── radar_dedup.yaml      # 去重窗口
│   ├── deep_analysis_profiles.yaml
│   ├── tools_discovery.yaml
│   └── news_sources.yaml
└── data/
    └── radar_delivered.json  # 去重历史（本地，不提交）
```

---

## 常见问题

**Q: 双击 bat 没反应？**  
A: 确认已安装 Python 且 `pip install PyYAML requests PyMuPDF` 完成。在 cmd 中手动运行 `python push_today_radar.py` 查看报错。

**Q: arXiv 连接超时 / 429？**  
A: 脚本会自动回退昨日缓存。也可加 `--no-arxiv` 用本地 JSON。

**Q: 论文重复出现？**  
A: 检查 `data/radar_delivered.json` 是否正常写入；调整 `config/radar_dedup.yaml` 中的 `lookback_days`。

**Q: 深读质量不够？**  
A: 在 `config/deep_analysis_profiles.yaml` 为该 arxiv_id 补全中文 profile。

**Q: 怎么改评分权重？**  
A: 编辑 `arxiv_daily.py` 中的 `WEIGHTS_NORMAL`。

---

## 环境要求

- Python 3.8+
- 依赖：`PyYAML`, `requests`, `PyMuPDF`
- （可选）Semantic Scholar API Key — https://www.semanticscholar.org/product/api#api-key
