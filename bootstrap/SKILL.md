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

## 5. 收集规范并请用户确认

这一步在起草背景之前做，也是安装后要对用户说的第一件事。

按 `skills/flow-conventions/SKILL.md` 在本轮收集，写入文档根 `team/conventions.md`，然后用确认清单问用户。不要把「请收集规范」这句话交给用户去发。

用户没说「规范已确认」之前，不要把 `confirmed` 写成 `true`。用户要改或补充时，按该技能的「用户补充」更新 `team/conventions.md` 和 `project.yaml` 的开关，不要改仓库里的 `AGENTS.md` 或 `.cursor/rules`。问完清单就停，不要接着做背景或某条需求。

## 6. 起草项目背景

安装只复制空模板。接着读前后端 README 和一级目录，补全文档根 `team/background.md` 和 `team/map.md`。保留文首的「未确认」。看不懂的章节留空并列出要用户补的点。已经没有「未确认」的背景文件不要整篇重写。`runtime` 留空。不要发明启动命令。

## 7. 检查技能是否装上

运行 `scripts/check.ps1` 或 `scripts/check.sh`。不要在这次安装里下载模型或浏览器扩展。

把脚本最后三行原意告诉用户，用这三行标题，不要省略：

- 技能安装：通过，或列出缺的名字。解析录像缺 `asr-watch`、自动点页面缺 `agent-browser` 时，写明不挡住当前整理需求。
- 请你确认：当前需要用户点头的事。安装刚完成时就是规范清单。没有就写「无」。
- 请你做：只有用户本人才能做的事，例如补本机依赖、在对话里给结论。没有就写「无」。

## 8. 结束语

向用户说明，并且每次停下来问用户时都保留上面三行：

- 技能安装
- 请你确认
- 请你做
- 收集到的规范是什么。没确认之前不要改业务代码
- 文档现在是哪一档
- 请新开一条对话。当前这条对话不会自动带上刚写好的常驻规则
