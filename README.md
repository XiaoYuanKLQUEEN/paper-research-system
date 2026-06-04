# Paper Research System

LLM 评估人类职业素养/人格方向的论文追踪系统。

## 功能

- **每日 arXiv 搜索** (`arxiv_daily.py`)：搜索 arXiv + Semantic Scholar，按相关性/新近性/热度/质量评分
- **图片提取** (`extract_images.py`)：从 arXiv 源码包 / PDF 提取论文图片
- **顶会搜索** (`conf_search.py`)：DBLP + Semantic Scholar 搜索 NeurIPS/ICML/ACL 等顶会论文
- **图片清理** (`cleanup_images.py`)：每月清理 3 个月前的图片

## 评分机制

| 维度 | 权重 |
|------|------|
| 相关性 | 40% |
| 新近性 | 20% |
| 热度 | 30% |
| 质量 | 10% |

## 研究领域

1. LLM 评估与评分
2. AI 面试官
3. NLP 人格推断
4. 多模态面试评估
5. 多智能体评估与去偏
6. LLM 偏见与公平性
7. Agent 辅助测评
8. 广义 LLM 评估方法论

## 使用

```bash
# 每日搜索
python arxiv_daily.py --config research_interests.yaml --top-n 15

# 提取论文图片
python extract_images.py "2606.02578" "images/2606.02578" "images/2606.02578_index.md"

# 顶会搜索
python conf_search.py --year 2025 --conferences "ACL,ICML" --top-n 10

# 清理旧图片
python cleanup_images.py
```

## 技术栈

- arXiv API + Semantic Scholar API
- DBLP API（顶会搜索）
- PyMuPDF（图片提取）
- Hermes Agent（cron 定时 + 深度分析 + 微信推送）
- Obsidian（笔记存档）
