# AGENTS.md

给在业务工作区里工作的 Agent。套件仓库还差什么看 [PLAN.md](PLAN.md)。

## 写套件文档时

这是给同事用的仓库，不是某一个人的本机工具。说明、模板、技能里只出现仓库地址 https://github.com/hanxuzz/dev-ai-kit 。不要写入任何同事的用户目录、磁盘路径或「我这台电脑上的位置」。每人克隆到哪里，只记在该项目不提交的 `project.local.yaml`。

## 先读什么

1. 工作区根的 `project.yaml` 和 `project.local.yaml`。套件路径是 `kit.path`，当前需求号是 `current`。机器路径只放在 `project.local.yaml`。
2. `<kit.path>/docs/layout.md`、`docs/runtime.md`、`docs/trust.md`、`docs/conventions.md`。`project.yaml` 里 `conventions.confirmed` 不是 `true` 时，先按 `skills/flow-conventions/SKILL.md` 确认开关，不要建分支，不要改业务代码。
3. 文档根里的 `team/background.md`，以及 `current` 指向的 `status.yaml`。

找不到 `kit.path` 就停止。请用户在当前对话发送 https://github.com/hanxuzz/dev-ai-kit ，并按 `bootstrap/SKILL.md` 安装。不要要求把 `skill.md` 复制进业务项目。

写需求文件之前运行 `<kit.path>/scripts/validate.ps1 -Workspace <工作区>`。失败就停，把 `FAIL` 那一行告诉用户。

用户不知道下一步，或本阶段做完时，运行 `<kit.path>/scripts/next.ps1 -Workspace <工作区>`，只把「下一步就做这一句」当作当前建议。

## 什么时候用套件

用户在办安装、项目背景、录屏、需求资料、需求整理、影响点、开发顺序、测试、提交时，按 `docs/layout.md` 的技能表去读 `<kit.path>/skills/` 里对应的 `SKILL.md`。

问实现、改一个函数、查一段代码时，直接做。

## 门禁

`questions: open` 时，`stage` 必须是 `questions`。

- 可以改 `03-questions.md`，并复制到共享目录里该需求的文件夹。
- 禁止创建 `04-requirement.md`、`05-impact.md`、`06-plan.md`。
- 禁止修改前后端业务代码，也禁止提交这些改动。

用户没有明确说需求方已确认时，不要把 `questions` 改成 `confirmed`，不要写最终需求和影响点。

`blocker` 非空时，先把这句话告诉用户。转写失败或文件还没同步时，不要写一份看起来完整的结论。

## 文件怎么分工

- 整理后的 Markdown 写到 `project.yaml` 的 `docs.mode` 所决定的文档根。算法见 `docs/runtime.md`。
- 录屏、PPT、PDF、架构图原件放在共享目录的 `requirements/<需求号>/`，并登记在 `index.md`。
- `asr-watch` 的 transcript、帧、wav 留在本机 `~/.local/share/asr-funasr/runs/<视频名>/`。
- 密码和连接串不写进任何文件。只写 Bitwarden 条目名。

## 能力边界

- 转写只调用本机已安装的 `asr-watch`。
- 浏览器操作只调用本机已安装的 `agent-browser`。缺插件或 MCP 时打开 `docs/dependencies.md`，停止。
- `runtime.database.readonly` 不是 `true`，或启动命令、测试命令为空时，按 `skills/flow-test/SKILL.md` 告诉用户怎么填。不要启动项目，不要连数据库。
