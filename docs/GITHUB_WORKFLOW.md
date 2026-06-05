# GitHub 开发流程（paper-research-system）

> 本仓库协作、提交、推送、发布的完整流程。  
> Agent 执行 Git 操作前必须读本文件 + [COMMIT_CONVENTION.md](./COMMIT_CONVENTION.md)。

---

## 1. 仓库信息

| 项 | 值 |
|----|-----|
| 远程 | `https://github.com/XiaoYuanKLQUEEN/paper-research-system` |
| 默认分支 | `main` |
| 本地路径 | `E:\paper-research-system` |
| Obsidian Vault | `D:/Obsidian` |

---

## 2. 分支策略

- **日常开发**：直接在 `main` 上小步提交（个人项目，无长期 feature 分支要求）
- **较大功能**：可开 `feat/xxx` 分支，完成后 PR 合并到 `main`（可选）
- **禁止**：未经用户明确要求，不得 `git push --force` 到 `main`

---

## 3. 标准开发循环

```
改代码 → 本地验证 → 拟 commit message → 用户确认「最终版」→ commit → push → 更新 CHANGELOG
```

### 3.1 改代码

- 功能脚本：项目根目录 `*.py`
- 配置：`config/*.yaml`
- 深读档案：`config/deep_analysis_profiles.yaml`
- 一键入口：`推送今日领域雷达.bat`、`push-to-github.bat`

### 3.2 本地验证（必做）

```powershell
cd E:\paper-research-system

# 领域雷达全流程
python push_today_radar.py --no-open

# 或仅重生成日报（已有 merged json）
python generate_radar_daily.py --input radar_merged_YYYYMMDD.json `
  --output "D:\Obsidian\10_Daily\YYYY-MM-DD领域雷达.md" --date YYYY-MM-DD
```

确认：Obsidian 输出正常、无 Python  traceback、去重/配额符合预期。

### 3.3 用户确认「最终版」

**Agent 在 commit 之前必须：**

1. 列出本次变更摘要（改了哪些文件、解决什么问题）
2. 给出**完整的拟用 commit title + body（bullet）**
3. 等待用户回复「可以 / 最终版 / 推送吧」后再执行 git 命令

用户未确认时：**只改文件，不 commit、不 push**。

---

## 4. 提交规范（精确、可检索）

详见 [COMMIT_CONVENTION.md](./COMMIT_CONVENTION.md)。

### 标题

```
<类型>(<模块>): <一句话说清具体功能>
```

### 正文（2–6 条 bullet）

每条 = 一个可验证变更点，禁止「更新了一下」「fix bug」。

### 拆分原则

| 场景 | 做法 |
|------|------|
| 新脚本 + 配置 + 文档 | **至少 2 个 commit**（功能 / 文档分开） |
| 仅改 yaml 阈值 | `配置(模块): ...` 单独 commit |
| README + CHANGELOG | `文档(...): ...` 可同 commit |

### 历史模糊 commit

`66c0b05` 等 message 不准确时，以 [CHANGELOG.md](../CHANGELOG.md) 为准；**新提交不得再犯**。

---

## 5. Windows 提交命令（UTF-8 防乱码）

```powershell
cd E:\paper-research-system
chcp 65001 | Out-Null

@"
功能(模块): 标题一句话

- bullet 1
- bullet 2
"@ | Out-File -FilePath .git/COMMIT_MSG_UTF8.txt -Encoding utf8

git add <文件列表>
git commit -F .git/COMMIT_MSG_UTF8.txt
```

**不要**修改 `git config`（user.name / user.email / i18n 等）。

---

## 6. 推送到 GitHub

### 6.1 网络环境

直连 `github.com:443` 常超时；本机代理 **127.0.0.1:7897** 可用。

### 6.2 推荐方式：双击 bat

```
push-to-github.bat
```

### 6.3 命令行（单次代理，不改全局 config）

```powershell
git -c http.https://github.com.proxy=http://127.0.0.1:7897 `
    -c https.https://github.com.proxy=http://127.0.0.1:7897 `
    push origin main
```

### 6.4 推送前检查

```powershell
git status                    # 无遗漏未提交文件
git log origin/main..HEAD     # 确认待推送 commits
git log -1 --format=%B        # 确认 message 精确
```

### 6.5 推送后

- 浏览器打开 GitHub 仓库确认 commit 与 message
- 大功能在 [CHANGELOG.md](../CHANGELOG.md) 对应日期下补条目

---

## 7. Pull Request 流程（可选）

需要 Code Review 或功能分支时使用：

```powershell
git checkout -b feat/radar-dedup
# ... commits ...
git -c http.https://github.com.proxy=http://127.0.0.1:7897 push -u origin HEAD

gh pr create --title "功能(去重): ..." --body "$( @'
## Summary
- ...

## Test plan
- [ ] python push_today_radar.py --no-open
'@ )"
```

需安装 [GitHub CLI](https://cli.github.com/) 且 `gh auth login`。

---

## 8. 变更记录

| 文件 | 用途 |
|------|------|
| [CHANGELOG.md](../CHANGELOG.md) | 按日期/版本记录**实际功能**（含历史 message 纠正） |
| `git log --grep="模块名"` | 按 commit message 检索 |

大功能发布时在 CHANGELOG 增加 `## [YYYY-MM-DD] 标题` 小节。

---

## 9. 不提交的文件

已在 `.gitignore`：

- `data/radar_delivered.json` — 去重本地历史
- （建议后续加入）`__pycache__/`、`*.pyc`、本地 `arxiv_filtered_*.json` 缓存

**勿提交**：密钥、`.env`、含 token 的配置。

---

## 10. Agent 检查清单（每次 Git 操作）

- [ ] 用户已确认「最终版」
- [ ] commit message 符合 `类型(模块): 功能点` + body bullets
- [ ] 已本地跑通相关脚本
- [ ] 大功能已更新 CHANGELOG
- [ ] 使用 `push-to-github.bat` 或带 proxy 的单次 push
- [ ] 推送后回报 commit hash 与 GitHub 链接
- [ ] 未执行 force push / 未改 git config

---

## 11. 常用检索命令

```powershell
git log --oneline -20
git log --grep="去重" --oneline
git log --grep="深读" --stat
git show <hash> --stat
git diff origin/main..HEAD
```

---

## 12. 与本项目功能的对应关系

| 用户操作 | 脚本 | 是否 commit |
|---------|------|------------|
| 每日推 Obsidian 雷达 | `推送今日领域雷达.bat` | 否（生成内容在 Vault） |
| 改雷达逻辑/深读 | 改 `*.py` / `config/` | 是 |
| 推代码到 GitHub | `push-to-github.bat` | 推送已有 commits |

**区分**：Obsidian 日报是**产出物**（在 Vault）；GitHub 存**源代码与配置**。
