---
name: kit-bootstrap
description: >-
  一次性安装 dev-ai-kit。用户把本文件复制为业务工作区根目录的 skill.md 并要求执行时使用。
  决定文档去处，运行安装脚本，起草未确认的项目背景，并告知新开对话。
disable-model-invocation: true
---

# 安装 dev-ai-kit（只执行一次）

用户把本文件放在业务工作区根目录（例如 `psl/skill.md`）并要求执行时，按下面顺序做。做完告诉用户新开一条对话。不要把套件克隆进工作区内部。

## 1. 找到套件

仓库地址（写在这里，因为本文件会被复制到业务项目里，那时旁边还没有套件）：

https://github.com/hanxuzz/dev-ai-kit

按顺序查找，找到即停：

1. 环境变量 `DEV_AI_KIT`
2. 用户在这次对话里给出的克隆目录
3. 该目录必须有 `kit.yaml`、`AGENTS.md`、`scripts/install.ps1`

都没有：请用户把上面的仓库克隆到自己电脑上的任意目录，把路径发过来。禁止克隆到当前业务项目里面。禁止假设某位同事的用户名或磁盘路径。

## 2. 确认工作区

Cursor 打开的必须是包含前后端的父文件夹，不能是某一个代码仓本身。父文件夹里要有带 `.git` 或构建文件的子目录。没有就停，请用户先克隆代码。

列出这些子目录，请用户确认哪个是前端、哪个是后端。名字已经是 `frontend` / `backend` 时可以直接采用。

## 3. 决定文档去处

按顺序，用户已经表态的不要再问：

1. 工作区里有名为 `docs` 的 git 仓库：`-DocsMode repo`。文档库文件夹不叫 `docs` 时，加上 `-DocsRepo <文件夹名>`。不要把名字里只是含有 doc 的目录当成文档库。
2. 没有文档库：询问 OneDrive 共享目录的本机路径。有则 `-DocsMode share -SharePath <路径>`。说明共享目录用来同步录屏、架构图和给需求方看的问题清单。
3. 都没有：`-DocsMode local`。告诉用户整理结果在工作区的 `docs/`，不提交；只克隆前后端时拿不到这些文件。
4. `project.yaml` 已经存在时，安装脚本不会改 `docs.mode`。用户要换去处就编辑该文件，不要靠再跑一次安装来改。

## 4. 运行安装脚本

Windows：

```powershell
powershell -NoProfile -File <套件>\scripts\install.ps1 -Workspace <工作区> -Kit <套件> -DocsMode <local|share|repo> -DocsRepo <文件夹名> -SharePath <路径>
```

macOS / Linux 用 `scripts/install.sh`，参数相同。

脚本失败就停，把 `FAIL` 那一行告诉用户。不要手工改出一套平行配置。脚本不会覆盖已有的 `project.yaml`、`project.local.yaml` 和改过的规则。

## 5. 起草项目背景

安装只复制空模板。接着读前后端 README 和一级目录，补全文档根 `team/background.md` 和 `team/map.md`。保留文首的「未确认」。看不懂的章节留空并列出要用户补的点。已经没有「未确认」的背景文件不要整篇重写。

`runtime` 留空。不要发明启动命令。以后要本地启动或连接只读库时，按 `skills/flow-test/SKILL.md` 填写 `project.yaml`。

## 6. 检查依赖

运行 `scripts/check.ps1` 或 `scripts/check.sh`。把缺项告诉用户，并指向 `docs/dependencies.md`。不要在这次安装里下载模型或浏览器扩展。

## 7. 结束语

向用户说明：

- 文档现在是哪一档
- 原件以后放到共享目录的 `requirements/<需求号>/`，并写进 `index.md`
- 目录和状态看 `docs/layout.md`，日常说法看 `MANUAL.md`
- 请新开一条对话。当前这条对话不会自动带上刚写好的常驻规则
