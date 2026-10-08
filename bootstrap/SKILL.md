---
name: kit-bootstrap
description: >-
  一次性安装 dev-ai-kit。用户在业务项目里给出仓库地址并要求安装时使用。
  先把套件克隆到业务文件夹外面，再决定文档去处、运行安装脚本、起草未确认的项目背景，并告知新开对话。
disable-model-invocation: true
---

# 安装 dev-ai-kit（只执行一次）

用户在业务项目的对话里给出仓库地址并要求安装时，按下面顺序做。不要把 `skill.md` 复制进业务项目。做完告诉用户新开一条对话。不要把套件克隆进工作区内部。

## 1. 找到或克隆套件

仓库地址：https://github.com/hanxuzz/dev-ai-kit

按顺序查找，找到即停。目录里要有 `kit.yaml`、`AGENTS.md`、`scripts/install.ps1` 才算找到。

1. 环境变量 `DEV_AI_KIT`
2. 当前工作区 `project.local.yaml` 里已有的 `kit.path`
3. 用户在这次对话里给出的克隆目录
4. 工作区的上一级目录里、名为 `dev-ai-kit` 的文件夹

都没有：在工作区的上一级执行 `git clone https://github.com/hanxuzz/dev-ai-kit`。上一级里已经有同名文件夹但不是这个套件时，停下来问克隆到哪，不要覆盖。禁止克隆到当前业务项目里面。禁止假设某位同事的用户名或磁盘路径。

克隆因权限失败时，请用户在本机登录能访问该私有仓库的 GitHub 账号后重试。不要让用户把令牌或密码发到对话里。

## 2. 确认工作区

Cursor 打开的是包含前后端的那一层。这一层自己可以是 git 仓库，只要下面还有 `service/`、`ui/` 或其他代码目录。只打开其中某一个代码仓、里面没有下一层代码目录时，安装会停。

列出这些子目录，请用户确认哪个是前端、哪个是后端。名字已经是 `frontend` / `backend`，或 `ui` / `service` 时可以直接采用。不要改写工作区已有的 `AGENTS.md`。

## 3. 决定文档去处

按顺序，用户已经表态的不要再问：

1. 工作区里有名为 `docs` 的 git 仓库：`-DocsMode repo`。文档库文件夹不叫 `docs` 时，加上 `-DocsRepo <文件夹名>`。不要把名字里只是含有 doc 的目录当成文档库。
2. 没有单独的文档库，但工作区自己是 git 仓库，文档就在里面：`-DocsMode tracked`。已有 `docs/requirement/` 这类目录时，安装会记成 `requirements_dir`，不会另建 `docs/requirements/`，也不会把 `/docs/` 写进 `.gitignore`。
3. 工作区不是 git 仓库：询问 OneDrive 共享目录的本机路径。有则 `-DocsMode share -SharePath <路径>`。
4. 都没有：`-DocsMode local`。整理结果在工作区的 `docs/`，不提交。
5. `project.yaml` 已经存在时，安装脚本不会改 `docs.mode`。用户要换去处就编辑该文件，不要靠再跑一次安装来改。

## 4. 运行安装脚本

Windows：

```powershell
powershell -NoProfile -File <套件>\scripts\install.ps1 -Workspace <工作区> -Kit <套件> -DocsMode <local|share|repo> -DocsRepo <文件夹名> -SharePath <路径>
```

macOS / Linux 用 `scripts/install.sh`，参数相同。

脚本失败就停，把 `FAIL` 那一行告诉用户。不要手工改出一套平行配置。脚本不会覆盖已有的 `project.yaml`、`project.local.yaml` 和改过的规则。

## 5. 起草项目背景

安装只复制空模板。接着读前后端 README 和一级目录，补全文档根 `team/background.md` 和 `team/map.md`。保留文首的「未确认」。看不懂的章节留空并列出要用户补的点。已经没有「未确认」的背景文件不要整篇重写。`runtime` 留空。不要发明启动命令。

## 6. 确认规范

`project.yaml` 里的 `conventions` 此时只是建议，`confirmed` 仍是 `false`。按 `skills/flow-conventions/SKILL.md` 看各仓库当前分支和已有的 `AGENTS.md`，请用户逐项打开或关掉。仓库已有分支规则时，建议关掉套件的自动建分支。用户没确认前，不要把 `confirmed` 写成 `true`。确认前可以整理已有材料，不要建分支，不要改业务代码。

## 7. 检查依赖

运行 `scripts/check.ps1` 或 `scripts/check.sh`。把缺项告诉用户，并指向 `docs/dependencies.md`。不要在这次安装里下载模型或浏览器扩展。

## 8. 结束语

向用户说明：

- 文档现在是哪一档
- 原件以后放到共享目录的 `requirements/<需求号>/`，并写进 `index.md`
- 目录和状态看 `docs/layout.md`，日常说法看 `MANUAL.md`
- 请新开一条对话。当前这条对话不会自动带上刚写好的常驻规则
