#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 radar_merged.json 生成 Obsidian 领域雷达。
深读区对齐 6/2、6/3 格式：偏差关联、一句话总结、核心发现、配图、与你的研究关联。
"""

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from radar_images import enrich_papers_with_images

PROFILES_PATH = Path(__file__).parent / "config" / "deep_analysis_profiles.yaml"
# 每日固定补课一篇（高影响力、与评人方向强相关）
SUPPLEMENT_ARXIV = "2506.10922"


def _load_profiles() -> Dict:
    import yaml
    if PROFILES_PATH.exists():
        with open(PROFILES_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


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
        return "（无自动化评分）"
    return (
        f"{s.get('recommendation', '-')}/10"
        f"（相关性 {s.get('relevance', '-')} | 新近性 {s.get('recency', '-')} "
        f"| 热度 {s.get('popularity', '-')} | 质量 {s.get('quality', '-')}）"
    )


def _note_link(p: Dict) -> str:
    fn = p.get("note_filename")
    return f"[[{fn}]]" if fn else ""


def _extract_method_name(summary: str) -> Optional[str]:
    for pat in (
        r"We propose ([^,.]+)",
        r"We present ([^,.]+)",
        r"We introduce ([^,.]+)",
    ):
        m = re.search(pat, summary, re.I)
        if m:
            name = m.group(1).strip()
            if len(name) > 80:
                name = name[:77] + "…"
            return name
    return None


def _extract_result_snippet(summary: str) -> Optional[str]:
    sl = summary.lower()
    for key in (
        "state-of-the-art",
        "sota",
        "outperform",
        "improves",
        "achieves",
        "consistently improves",
    ):
        idx = sl.find(key)
        if idx >= 0:
            chunk = summary[idx : idx + 200]
            end = chunk.find(". ")
            return chunk[: end if end > 0 else 180].strip()
    nums = re.findall(r"[\d.]+%", summary)
    if nums:
        return f"摘要报告约 {nums[0]} 量级的提升（详见原文表格）。"
    return None


def _topic_context(sl: str) -> str:
    if "data-analytic agent" in sl or "data analysis" in sl:
        return (
            "让 AI 像数据分析师一样查数、写报告、做推理——而不只是聊天。"
            "核心难点往往在于：哪些**可复用流程（skill）**能让 Agent 稳定做好分析。"
        )
    if "emergent language" in sl or "conscious" in sl:
        return (
            "研究「AI 能否/如何表现出意识相关结构」。"
            "关键不是贴标签，而是设计实验让结构**从任务里自然长出**，排除人类语言先验的干扰。"
        )
    if "layout detection" in sl or "document" in sl and "benchmark" in sl:
        return (
            "从 PDF/机构报告里**可靠地找出图表和表格**——尤其是「有分析价值」的那一块，"
            "而不是把装饰性图片也框进来。"
        )
    if "machine learning engineering" in sl or "mle-bench" in sl or "self-evolv" in sl:
        return (
            "LLM 多 Agent **长时程自动做机器学习工程**（写代码、跑实验、迭代算法），"
            "考验的是连续多轮自我改进，而不是一次性生成。"
        )
    if any(k in sl for k in ("agent", "multi-agent")):
        return "多个 AI Agent 分工协作，完成单靠一个模型搞不定的长链条任务。"
    if any(k in sl for k in ("fairness", "bias", "judge", "scoring")):
        return "用大模型当评委或评分器时，分数是否公平、稳定、可被审计。"
    if any(k in sl for k in ("video", "audio", "multimodal", "vlm")):
        return "模型同时理解文字、图像、视频或语音等多模态输入，并在真实交互场景里被评估。"
    if any(k in sl for k in ("personality", "trait", "mbti", "big five")):
        return "从语言或行为信号推断人的性格特质（如大五人格），并评估推断是否可靠。"
    if any(k in sl for k in ("retrieval", "rag")):
        return "模型先检索外部资料再回答，评测重点是检索是否准、生成是否忠实于证据。"
    if any(k in sl for k in ("benchmark", "evaluation framework", "dataset")):
        return "为某一能力建立标准测试集和评测协议，让不同模型/方法可以公平对比。"
    return "在 AI 能力评测或系统搭建场景里，解决一个具体但影响面很广的子问题。"


def _problem_context(sl: str) -> str:
    if "supervision is expensive" in sl or "unlabeled" in sl:
        return (
            "人工标注「什么是好结果」太贵，而且不同任务的成功标准不统一。"
            "能不能**不靠人类标签**，从 Agent 自己的多次尝试里提炼经验？"
        )
    if "inter-branch" in sl or "memoryless" in sl:
        return (
            "长时程搜索里，各条尝试路线**互不相通**，又没有记忆，"
            "好想法容易死在孤立分支里，还会重复踩坑。"
        )
    if "struggle to generalize" in sl or "failure mode" in sl:
        return (
            "在「干净学术数据」上表现不错的模型，一到真实业务文档就翻车——"
            "说明现有 benchmark 和真实需求之间有鸿沟。"
        )
    if "human language priors" in sl or "artifacts" in sl:
        return (
            "你观测到的「高级结构」可能不是任务真正需要的，"
            "而是模型从人类语言训练里带来的**先验假象**——需要可因果归因的实验设计。"
        )
    if any(k in sl for k in ("cost", "latency", "efficient")):
        return "现有方案太慢或太贵，难以在真实产品里持续跑大规模评测/迭代。"
    if any(k in sl for k in ("bias", "fairness")):
        return "评分或决策流程存在系统性偏差，对不同群体不公平，且表面看不出来。"
    if any(k in sl for k in ("long-horizon", "memory", "sustained")):
        return "任务要跑很多轮，但模型/Agent **记不住前面发生了什么**，前后矛盾或重复劳动。"
    if "however" in sl:
        return "摘要前半段交代了方向 promising，但 **However** 之后点出关键瓶颈——这是本文的切入点。"
    return "现有做法在效果、稳定性、成本或可解释性上至少有一项明显不够用。"


def _method_context(summary: str, sl: str) -> str:
    method = _extract_method_name(summary)
    head = f"提出 **{method}**。" if method else "提出一套新框架。"
    tails: List[str] = []
    if "verifier" in sl and "skill" in sl:
        tails.append(
            "系统里通常有「干活的 Agent」和「当评委的 Verifier」："
            "Agent 多试几次，Verifier 在无人工标签的情况下比较哪次更好，"
            "再把好经验蒸馏成可注入的 skill。"
        )
    if "tree search" in sl or "mcgs" in sl:
        tails.append(
            "用**树/图搜索**组织多次尝试，并允许分支之间互相参考，"
            "从广撒网逐渐聚焦到更有希望的路线。"
        )
    if "retrospective memory" in sl or ("memory" in sl and "retriev" in sl):
        tails.append("引入**可检索的记忆库**，让新一次尝试能复用过去成功/失败的经验，而不是从零开始。")
    if "benchmark" in sl and ("dataset" in sl or "evaluation" in sl):
        tails.append("同时发布**数据集 + 评测协议 + 基线结果**，方便后人复现和对比。")
    if "reinforcement" in sl or "multi-agent reinforcement" in sl:
        tails.append("用**多智能体强化学习**：Agent 在任务压力下学策略，观察会涌现什么行为或通信方式。")
    if not tails:
        tails.append("具体模块分工和算法细节见论文 Method 节；摘要里强调的是整体思路而非实现清单。")
    return head + " " + "".join(tails)


def _generic_findings(summary: str) -> List[str]:
    s = re.sub(r"\s+", " ", summary).strip()
    if not s:
        return [
            "针对什么：该工作面向 AI 能力评测或 Agent 系统里的一个具体子问题（建议先读 Abstract 第一段）。",
            "解决了什么问题：现有做法在效果、成本或可复现性上存在瓶颈，作者指出这一瓶颈为何值得单独成文。",
            "创新方法：提出新框架/基准/训练或推理流程——请结合原文图表核对细节。",
            "小白贴士：先搞清论文里的 3 个名词（任务、baseline、指标），再决定要不要精读。",
        ]

    sl = s.lower()
    out = [
        f"针对什么：{_topic_context(sl)}",
        f"解决了什么问题：{_problem_context(sl)}",
        f"创新方法：{_method_context(s, sl)}",
    ]
    result = _extract_result_snippet(s)
    if result:
        out.append(f"结果怎么读：{result}（数字以论文表格为准；这里帮你抓住「有没有实打实提升」）。")
    else:
        out.append("结果怎么读：摘要声称在标准 benchmark 上优于 baseline——精读时重点看评测设置是否贴近你的应用场景。")
    out.append("小白贴士：把论文画成「输入 → 系统模块 → 输出指标」三张卡片，通常 10 分钟就能判断值不值得深读。")
    return out


def _generic_one_liner(p: Dict) -> str:
    summary = (p.get("summary") or p.get("abstract") or "").strip()
    title = p.get("title", "该工作")
    method = _extract_method_name(summary)
    sl = summary.lower()

    if method and "datacope" in sl:
        return (
            f"**DataCOPE** 让数据分析 Agent 在无人工标注时自己探索、自己当评委，"
            f"把好经验蒸馏成可注入技能——报告类 +9.71%、推理类 +32.30%（详见 profile）。"
        )

    hook = _topic_context(sl).split("。")[0] + "。"
    if method:
        return f"{hook} 作者提出 **{method.split(',')[0]}** 来应对摘要里点出的瓶颈（{title}）。"
    return f"{hook} 《{title}》给出一条可操作的解决路线，适合先读摘要再决定是否精读全文。"


def _generic_relevance(p: Dict) -> List[str]:
    domain = p.get("matched_domain", "")
    sl = (p.get("summary") or p.get("abstract") or "").lower()
    out = []
    if any(k in sl for k in ("bias", "fairness", "judge", "scoring")):
        out.append("🔥 与 LLM 评估偏差 / 公平性直接相关。")
    if any(k in sl for k in ("agent", "multi-agent")):
        out.append("🔥 与多智能体评估/去偏流水线相关。")
    if any(k in sl for k in ("interview", "hiring", "recruitment")):
        out.append("🔥 与 AI 面试 / 招聘评估场景相关。")
    if any(k in sl for k in ("personality", "trait", "mbti", "big five")):
        out.append("🎯 与人格推断 / 特质评分相关。")
    if any(k in sl for k in ("video", "audio", "multimodal")):
        out.append("🎯 与多模态面试/交互评估相关。")
    if not out:
        out.append(f"📎 匹配域「{domain}」；建议速读摘要后决定是否精读。")
    return out


def _embed_images(images: List[str]) -> List[str]:
    lines = []
    for img in images[:3]:
        lines.append(f"![[{img}|600]]")
        lines.append("")
    return lines


def render_deep(p: Dict, idx: int, profiles: Dict) -> List[str]:
    label, arxiv, pdf = _link(p)
    title = p.get("title", "")
    aid = p.get("arxiv_id", "")
    prof = profiles.get(aid, {}) if aid else {}

    tag = prof.get("tag", "📎 待精读")
    one_liner = prof.get("one_liner", "")
    if not one_liner:
        one_liner = _generic_one_liner(p)

    findings = prof.get("findings") or _generic_findings(
        p.get("summary") or p.get("abstract") or ""
    )
    relevance = prof.get("relevance") or _generic_relevance(p)

    lines = [
        f"### {idx}. {title}",
        "",
        f"- **作者**：{_authors(p)}",
        f"- **链接**：[{label}]({arxiv}) | [PDF]({pdf})",
        f"- **评分**：{_scores_line(p)}",
        f"- **匹配领域**：{p.get('matched_domain', '')}",
        f"- **偏差关联**：{tag}",
        f"- **笔记**：{_note_link(p)}",
        "",
    ]
    lines.extend(_embed_images(p.get("_images") or []))

    lines.extend([
        f"**一句话总结**：{one_liner}",
        "",
        "**核心发现**（小白向：先懂背景 → 痛点 → 方法 → 结果）：",
    ])
    for f in findings:
        lines.append(f"- {f}")
    lines.extend(["", "**与你的研究关联**：", ""])
    for r in relevance:
        lines.append(f"- {r}")
    lines.append("")
    lines.append("---")
    lines.append("")
    return lines


def render_supplement(profiles: Dict) -> List[str]:
    prof = profiles.get(SUPPLEMENT_ARXIV)
    if not prof:
        return []
    from radar_images import ensure_images
    images = ensure_images(SUPPLEMENT_ARXIV)
    lines = [
        "## 📚 高影响力补课深读（1 篇）",
        "",
        f"### {prof.get('title', 'Robustly Improving LLM Fairness in Realistic Settings via Interpretability')}",
        "",
        "- **作者**：待从 arXiv 获取",
        f"- **链接**：[arXiv](https://arxiv.org/abs/{SUPPLEMENT_ARXIV}) | [PDF](https://arxiv.org/pdf/{SUPPLEMENT_ARXIV}v1)",
        f"- **偏差关联**：{prof.get('tag', '🔥 直接相关')}",
        "- **笔记**：[[Robustly_Improving_LLM_Fairness_in_Realistic_Settings_via_Interpretability]]",
        "",
    ]
    lines.extend(_embed_images(images))
    lines.append(f"**一句话总结**：{prof.get('one_liner', '')}")
    lines.append("")
    lines.append("**核心发现**：")
    for f in prof.get("findings", []):
        lines.append(f"- {f}")
    lines.append("")
    lines.append("**与你的研究关联**：")
    lines.append("")
    for r in prof.get("relevance", []):
        lines.append(f"- {r}")
    lines.append("")
    lines.append("---")
    lines.append("")
    return lines


def _zh_tool_intro(t: Dict) -> Dict[str, str]:
    """返回工具的中文：一句话 + 你怎么用。"""
    fn = (t.get("full_name") or "").lower()
    desc = (t.get("description") or "").lower()
    name = t.get("full_name", t.get("name", ""))

    catalog = {
        "thudm/agentbench": (
            "ICLR'24 经典 **Agent 评测基准**，在 8 类环境中测试 LLM 当 Agent 的真实能力。",
            "可当作你多智能体评分/去偏实验的 Agent 侧 baseline，对照「评委 Agent」设计。",
        ),
        "huggingface/transformers": (
            "Hugging Face **模型定义与推理框架**，几乎是一切 NLP/多模态实验的底座。",
            "快速加载 judge 模型、跑评测脚本；注意记录模型版本避免 judge 漂移。",
        ),
        "mlflow/mlflow": (
            "开源 **AI 实验追踪平台**，记录 prompt、参数、分数与模型版本。",
            "论文实验必备：每次 LLM-as-Judge 跑分都可追溯、可复现。",
        ),
        "promptfoo/promptfoo": (
            "**Prompt/Agent 红队与评测工具**，支持多模型对比与 CI 集成。",
            "用来批量测评分 prompt 的稳定性、偏差敏感性，OpenAI/Anthropic 也在用。",
        ),
        "comet-ml/opik": (
            "LLM 应用 **追踪 + 自动评测** 平台，带生产级 dashboard。",
            "适合把评分流水线接入 trace，观察哪一步引入偏差。",
        ),
        "openai/evals": (
            "OpenAI 开源的 **LLM 评测框架与 benchmark 注册表**。",
            "参考其评测协议设计你自己的「人类素养评分」benchmark。",
        ),
        "google/adk-python": (
            "Google **Agent 开发工具包**，强调构建、评测、部署一体化。",
            "学习其 Agent 评测接口设计，可借鉴到多评委 Agent 编排。",
        ),
        "explodinggradients/ragas": (
            "**RAG 评测框架**，量化检索质量与生成忠实度。",
            "若评分系统带检索证据链，可用 Ragas 评「理由是否忠实于材料」。",
        ),
        "open-compass/opencompass": (
            "国产开源 **大模型评测平台**，覆盖大量中文/英文 benchmark。",
            "横向对比不同 judge 模型在评测任务上的表现。",
        ),
        "deepset-ai/haystack": (
            "开源 **LLM 编排框架**，模块化构建 RAG / Agent 流水线。",
            "搭建「检索 → 评委 → 聚合」的可复现流水线时可直接参考。",
        ),
        "sgl-project/sglang": (
            "高性能 **LLM 推理服务框架**，适合批量评测降时延。",
            "大规模评分实验（上千条 OPVA/Prolific）时加速 judge 推理。",
        ),
        "cshaitao/awesome-llms-as-judges": (
            "**LLM-as-Judge 论文与工具精选列表**（持续更新）。",
            "related work 补课入口，快速定位 judge 偏差方向新论文。",
        ),
        "suryanox/judgelens": (
            "模型无关的 **LLM 评估偏差量化与纠正** 框架。",
            "与你自己「诊断+缓解评分偏差」路线高度同构，建议 clone 试跑。",
        ),
        "minnesotanlp/cobbler": (
            "ACL'24 **LLM 认知偏差基准**，测模型系统性推理偏见。",
            "可对照你的四类偏差框架，看是否遗漏认知层偏差类型。",
        ),
        "trycua/cua": (
            "Computer-Use Agent **沙箱 + benchmark**，测 GUI 操作能力。",
            "Agent 轨迹评估参考；与 TrajBias 方向相邻。",
        ),
    }

    if fn in catalog:
        one, use = catalog[fn]
        return {"one_liner": one, "how_to_use": use}

    # 规则化中文简介
    if "eval" in desc or "benchmark" in desc or "judge" in desc:
        return {
            "one_liner": f"**{name}**：面向 LLM/Agent 的评测或基准工具。",
            "how_to_use": "可用于扩展你的评分实验、对照 baseline 或评测协议设计。",
        }
    if "agent" in desc:
        return {
            "one_liner": f"**{name}**：Agent 开发或评测相关开源项目。",
            "how_to_use": "参考其 Agent 编排/评测接口，迁移到多智能体评分流水线。",
        }
    if "multimodal" in desc:
        return {
            "one_liner": f"**{name}**：多模态模型推理/训练基础设施。",
            "how_to_use": "若扩展到视频/语音面试评分，可作为模型服务底座。",
        }
    return {
        "one_liner": f"**{name}**：AI 相关开源工具（⭐{t.get('stars', 0)}）。",
        "how_to_use": "建议浏览 README 确认是否适配你当前的 judge/Agent 实验栈。",
    }


def _zh_news_flash(item: Dict) -> str:
    title = (item.get("title") or "").strip()
    summary_en = (item.get("summary_en") or "").strip()
    source = item.get("source", "")
    tier = item.get("tier", "official")
    tier_zh = {"official": "官方", "media": "权威媒体"}.get(tier, "资讯")
    blob = (title + " " + summary_en + " " + source).lower()

    # 预设：引人入胜的一句话 + 与你何干
    presets = [
        (
            lambda b: "heart" in b and "camera" in b,
            "用手机摄像头做被动心脏健康监测",
            "Google 想把手机变成「无感健康传感器」——消费级多模态感知的下一站。",
            "与面试主线弱相关，但体现**被动多模态信号**趋势，可作多模态评估边界参考。",
        ),
        (
            lambda b: "nemotron" in b and "safety" in b,
            "Nemotron 3.5 内容安全：企业可定制多模态护栏",
            "NVIDIA 在 Hugging Face 亮出企业级**多模态内容安全**方案——模型越强，护栏越不能省。",
            "LLM 评人/面试场景里，**输出安全与公平合规**是产品化前提，这篇值得扫一眼。",
        ),
        (
            lambda b: "endava" in b or ("agent" in b and "software delivery" in b),
            "Endava 用 AI Agent 重构软件交付",
            "咨询公司把 Agent 嵌进交付流水线——产业侧「多 Agent 协作」已从 PPT 走进现场。",
            "观察工程里如何做质检与协作，可类比你的**多评委评分流水线**落地。",
        ),
        (
            lambda b: "court" in b or "lawsuit" in b,
            "法院如何应对 AI 生成诉讼文书泛滥",
            "MIT 报道：法官正被 AI 生成的起诉材料「淹没」——高风险场景里，模型输出已进法庭。",
            "LLM 进入**高风险决策**时，可靠性与可审计性要求远高于普通 benchmark；对你做评人系统是直接警示。",
        ),
    ]

    title_zh, hook, why = title, "", ""
    for pred, tz, h, w in presets:
        if pred(blob):
            title_zh, hook, why = tz, h, w
            break

    if not hook:
        if summary_en:
            hook = f"权威源发布：{title[:80]}（详见原文）。"
        else:
            hook = f"{source} 发布新动态，建议点开原文确认是否影响你的 judge 基线或工具链。"
        why = "关注官方模型/工具更新，避免评测实验使用过期 judge 或遗漏新 benchmark。"

    return "\n".join([
        f"**{tier_zh} · {source}**",
        f"- **标题**：{title_zh}",
        f"- **一句话总结**：{hook}",
        f"- **与你何干**：{why}",
        f"- [阅读原文]({item.get('url', '#')})",
    ])


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
    stars = t.get("stars", 0)
    intro = _zh_tool_intro(t)
    return [
        f"### {idx}. [{t.get('full_name', t.get('name'))}]({t.get('url', '#')}) · ⭐{stars}",
        "",
        f"- **一句话**：{intro['one_liner']}",
        f"- **你怎么用**：{intro['how_to_use']}",
        "",
    ]


def generate(data: Dict, date_str: str, profiles: Dict) -> str:
    papers: List[Dict] = data.get("papers") or []
    tools: List[Dict] = data.get("tools") or []
    news: List[Dict] = data.get("news") or []
    alloc = data.get("allocation") or {}
    dedup_meta = (data.get("meta") or {}).get("dedup") or {}

    papers_sorted = sorted(
        papers,
        key=lambda x: (x.get("scores") or {}).get("recommendation", 0),
        reverse=True,
    )
    enrich_papers_with_images(papers_sorted, top_n=4)
    # 补课篇配图
    if SUPPLEMENT_ARXIV not in {p.get("arxiv_id") for p in papers_sorted[:4]}:
        from radar_images import ensure_images
        ensure_images(SUPPLEMENT_ARXIV)

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
        'tags: ["llm-generated", "domain-radar", "formal"]',
        f"date: {date_str}",
        "---",
        "",
        "## 今日概览",
        "",
        f"今日 **领域雷达** 共 **{alloc.get('total', 0)}** 条：论文 **{alloc.get('papers', len(papers))}**、"
        f"开源工具 **{alloc.get('tools', len(tools))}**、快讯 **{alloc.get('news', len(news))}**。",
        "",
    ]
    sp = (dedup_meta.get("papers") or {}).get("skipped_papers", 0)
    st = (dedup_meta.get("tools") or {}).get("skipped_tools", 0)
    sn = (dedup_meta.get("news") or {}).get("skipped_news", 0)
    if sp or st or sn:
        parts.append(
            f"- **去重**：近次已推送内容已跳过 — 论文 **{sp}** 篇、工具 **{st}** 个、快讯 **{sn}** 条。"
        )
        parts.append("")
    parts.extend([
        "- **深读格式**：6/3 标准（中文一句话 + 小白向核心发现 + 配图 + 研究关联）。",
        "- **工具/快讯**：全中文简介；工具仅 ⭐≥50；快讯含「引人入胜一句话」。",
        "- **阅读策略**：深读 4 篇 + 补课 1 篇 → 简读扫标题 → 工具/快讯。",
        "",
        "---",
        "",
        f"## 🔥 论文深读（{deep_n} 篇）",
        "",
    ])

    for i, p in enumerate(deep, 1):
        parts.extend(render_deep(p, i, profiles))

    # 补课深读（Fairness 等不在 top4 的高影响力文）
    if SUPPLEMENT_ARXIV not in {p.get("arxiv_id") for p in deep}:
        parts.extend(render_supplement(profiles))

    parts.extend([
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
        "> 仅展示 **⭐≥50** 的成熟开源项目；论文附带 0 star 代码库不进入工具榜。",
        "",
    ])
    for i, t in enumerate(tools, 1):
        parts.extend(render_tool(t, i))

    parts.extend([
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
        "- [[Robustly_Improving_LLM_Fairness_in_Realistic_Settings_via_Interpretability]] — 招聘公平性（补课）",
        "- [[Mitigating_Perceptual_Judgment_Bias_in_Multimodal_LLM-as-a-Judge]] — 6/2 知觉偏差",
        "- [[2026-06-04论文推荐]] — 昨日手写深度版",
    ])
    for p in deep[:2]:
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
    profiles = _load_profiles()
    md = generate(data, args.date, profiles)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")
    print(f"Wrote: {out}")
    print(f"Allocation: {data.get('allocation')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
