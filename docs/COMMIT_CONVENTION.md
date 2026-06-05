# Git 提交规范（本项目）

每次 push 必须能**单独检索出本次做了什么**。禁止模糊 message（如「加上了工具」「更新一下」「fix bug」）。

---

## 标题格式

```
<类型>(<模块>): <一句话说清具体功能>
```

### 类型

| 类型 | 用途 |
|------|------|
| `功能` | 新能力、新脚本、新配置项 |
| `优化` | 性能、排序、文案质量、体验改进 |
| `修复` | Bug、合并冲突、崩溃、错误逻辑 |
| `配置` | 参数、阈值、yaml 默认值 |
| `文档` | README、CHANGELOG、注释 |
| `构建` | 依赖、bat/ps1、CI |

### 模块（常用）

`雷达` `arxiv` `日报` `深读` `去重` `工具` `新闻` `合并` `配图` `顶会` `推送` `文档`

---

## 正文（必填，2–6 条 bullet）

每条对应**一个可验证的变更点**，写清「改了什么 / 为什么」：

```
功能(推送): 新增 push_today_radar 一键推送到 Obsidian

- 串联 arxiv → news → tools → merge → generate_radar_daily
- 集成 radar_dedup 跨日去重（论文14d/工具7d/快讯3d）
- 完成后 os.startfile 打开 10_Daily/YYYY-MM-DD领域雷达.md
- 新增 推送今日领域雷达.bat 双击入口
```

---

## 单次 push 原则

1. **一个逻辑功能 = 一个 commit**（能拆就拆，方便 `git log --grep`）
2. push 前在 CHANGELOG 对应日期下补一行（大功能时）
3. Agent 流程：**先给出拟用 title + body → 你确认「最终版」→ 再 commit & push**

完整流程见 **[GITHUB_WORKFLOW.md](./GITHUB_WORKFLOW.md)**；Agent 自动加载 **`.cursor/rules/github-workflow.mdc`**。

---

## 检索示例

```bash
git log --oneline --grep="去重"
git log --oneline --grep="深读"
git log --grep="tools_scan" --stat
```

---

## 反面示例 → 正例

| ❌ 模糊 | ✅ 精确 |
|--------|--------|
| 加上了工具和新闻 | `功能(雷达): 新增 news_digest RSS 与 tools_scan GitHub 扫描` |
| 更新 README | `文档(雷达): README 补充一键推送与去重配置说明` |
| fix | `修复(配图): radar_images 超时 120s 不再阻断日报生成` |
| 改进了深读 | `优化(深读): Top4 增加 DataCOPE/MLEvolve 小白向 profile` |
