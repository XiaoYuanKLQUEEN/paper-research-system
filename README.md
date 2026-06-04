# Paper Research System

> LLM 评估人类职业素养/人格方向的论文自动追踪系统  
> 每日搜索 arXiv + Semantic Scholar，评分筛选，提取图片，生成深度分析

---

## 快速开始（5 分钟上手）

### 1. 安装依赖

```bash
pip install PyYAML requests PyMuPDF
```

### 2. 配置研究兴趣

编辑 `config/research_interests.yaml`，改三个地方：

```yaml
# 你的研究关键词（改成你自己的方向）
research_domains:
  "你的领域名":
    keywords:
      - "关键词1"
      - "关键词2"
    arxiv_categories:        # arXiv 分类代码
      - "cs.CL"              # NLP
      - "cs.AI"              # AI
    priority: 10             # 1-10，越高越优先

# 排除这些词（避免搜到不相关的论文）
excluded_keywords:
  - "medical image"
  - "drug"
```

常用 arXiv 分类：

| 代码 | 含义 |
|------|------|
| `cs.CL` | NLP / 计算语言学 |
| `cs.AI` | 人工智能 |
| `cs.LG` | 机器学习 |
| `cs.CV` | 计算机视觉 |
| `cs.MA` | 多智能体系统 |
| `cs.CY` | 计算机与社会（公平性/偏见） |
| `cs.HC` | 人机交互（面试/评估） |
| `cs.MM` | 多媒体（多模态） |

### 3. 运行每日搜索

```bash
# 基础用法：搜索最近 30 天，返回 15 篇
python arxiv_daily.py --config config/research_interests.yaml --top-n 15

# 只看最近 7 天（更快）
python arxiv_daily.py --config config/research_interests.yaml --top-n 10 --days 7

# 跳过 Semantic Scholar（纯 arXiv，最快）
python arxiv_daily.py --config config/research_interests.yaml --top-n 20 --skip-hot-papers
```

**输出**：`arxiv_filtered.json` — 包含每篇论文的标题、作者、摘要、评分（相关性/新近性/热度/质量）、匹配关键词。

**评分含义**：

| 维度 | 权重 | 说明 |
|------|------|------|
| 相关性 | 40% | 和你的关键词有多匹配 |
| 新近性 | 20% | 最近 30 天=满分，越旧越低 |
| 热度 | 30% | Semantic Scholar 引用数 |
| 质量 | 10% | 从摘要推断的创新性 |

结果按综合评分降序排列。**建议人工二次筛选**（自动化匹配会有噪声）。

---

## 各脚本详解

### `arxiv_daily.py` — 每日论文搜索

```bash
python arxiv_daily.py \
  --config config/research_interests.yaml \  # 必填：研究配置
  --top-n 15 \                               # 返回前 N 篇（默认 10）
  --max-results 200 \                        # arXiv 搜索上限（默认 200）
  --categories "cs.CL,cs.AI" \               # arXiv 分类（逗号分隔）
  --days 30 \                                # 搜索天数（默认 30）
  --skip-hot-papers \                        # 跳过 Semantic Scholar（提速）
  --output results.json                      # 输出文件名
```

**工作流**：arXiv API（近 30 天）→ Semantic Scholar（近 1 年热门）→ 合并去重 → 关键词匹配评分 → 按综合分排序。

> 💡 **网络慢怎么办？** 脚本内置 3 个镜像回退：官方 → 中科院镜像 → 国内镜像，自动切换。

### `extract_images.py` — 提取论文图片

```bash
python extract_images.py "2606.02578" "images/2606.02578" "images/2606.02578_index.md"
#                        ↑ arXiv ID    ↑ 图片保存目录     ↑ 索引文件
```

**优先从 arXiv 源码包提取**（.tar.gz 里的 pics/figures/ 目录），找不到才从 PDF 提取。过滤掉小图标/logo（<200px 或 <5KB）。

### `conf_search.py` — 顶会论文搜索

```bash
# 搜索 ACL 2025 的评估相关论文
python conf_search.py --year 2025 --conferences "ACL" --top-n 15 --config conf-papers.yaml

# 搜多个会议
python conf_search.py --year 2025 --conferences "ACL,EMNLP,NeurIPS,ICML,ICLR,AAAI"

# 搜 CHI（人机交互，AI 面试官相关）
python conf_search.py --year 2025 --conferences "CHI" --top-n 15 --config conf-papers.yaml
```

**工作流**：DBLP API（获取会议论文列表）→ 标题关键词轻量筛选 → Semantic Scholar（补充摘要+引用）→ 三维评分（相关性 40% + 热度 40% + 质量 20%）。

支持的会议：`ACL`, `EMNLP`, `NAACL`, `NeurIPS`, `ICML`, `ICLR`, `AAAI`, `CHI`, `FAccT`

编辑 `conf-papers.yaml` 修改关键词和默认会议列表。

### `cleanup_images.py` — 清理旧图片

```bash
python cleanup_images.py
```

删除 `images/` 下 3 个月前的图片文件夹。建议每月跑一次。

---

## 完整工作流示例

```bash
# 1. 每日搜索
python arxiv_daily.py --config config/research_interests.yaml --top-n 15

# 2. 查看结果（挑 3 篇最相关的）
cat arxiv_filtered.json | python -c "import json,sys; d=json.load(sys.stdin); [print(p['title'][:60], p['scores']['recommendation']) for p in d['top_papers'][:10]]"

# 3. 提取前 3 篇的图片
python extract_images.py "2606.02578" "images/2606.02578" "images/2606.02578_index.md"
python extract_images.py "2506.22316" "images/2506.22316" "images/2506.22316_index.md"

# 4. （可选）搜索顶会补充
python conf_search.py --year 2025 --conferences "ACL,ICML" --top-n 10

# 5. 每月清理
python cleanup_images.py
```

---

## 环境要求

- Python 3.8+
- 依赖：`pip install PyYAML requests PyMuPDF`
- （可选）Semantic Scholar API Key — 免费注册 https://www.semanticscholar.org/product/api#api-key ，能避免 429 限流

---

## 目录结构

```
paper-research-system/
├── arxiv_daily.py              # 每日搜索主脚本
├── extract_images.py            # 图片提取
├── conf_search.py               # 顶会搜索
├── conf-papers.yaml             # 顶会配置
├── cleanup_images.py            # 图片清理
├── config/
│   └── research_interests.yaml  # 你的研究配置
└── README.md
```

---

## 常见问题

**Q: 搜索没有结果？**  
A: 检查 `research_interests.yaml` 里的关键词和 arXiv 分类是否匹配。可以用 `--days 14` 扩大范围试试。

**Q: arXiv 连接超时？**  
A: 脚本已内置中科院镜像回退，会自动切换。如果所有镜像都失败，检查网络。

**Q: 评分结果不准？**  
A: 自动化评分有噪声，建议人工二次筛选。看到高分但明显不相关的论文，在 `excluded_keywords` 里加排除词。

**Q: 怎么改评分权重？**  
A: 编辑 `arxiv_daily.py` 顶部的 `WEIGHTS_NORMAL`：
```python
WEIGHTS_NORMAL = {
    'relevance': 0.40,  # 相关性
    'recency': 0.20,    # 新近性
    'popularity': 0.30, # 热度
    'quality': 0.10,    # 质量
}
```
