# dev-ai-kit 开发计划

版本 0.1.0。业务项目里的开发顺序写在该需求的 `06-plan.md`，不写在这里。

## 已落地

- 目录和状态：`docs/layout.md`（`stage`、`questions`、`blocker`）
- 安装和校验：`scripts/install.ps1`、`scripts/validate.ps1`
- 技能正文：`skills/flow-intake`、`flow-meeting`、`flow-sources`、`flow-impact`、`flow-plan`、`flow-implement`、`flow-test`、`flow-git`
- 文档信任顺序：`docs/trust.md`
- 每条需求要能验收、编号能追到用例：`docs/practices.md`
- 一次性入口：`bootstrap/SKILL.md`
- 依赖说明：`docs/dependencies.md`（`asr-watch`、`agent-browser` 不复制进本仓库）

## 已定原则

- 套件每台机器一份，由 Cursor 克隆到业务文件夹外面。路径只记在 `project.local.yaml`。
- 安装入口是仓库地址，不复制 `skill.md`。装好后靠 `.cursor/rules/dev-ai-kit.mdc`，技能从 `kit.path` 读取。
- 文档去处：工作区中的文档库 → OneDrive 共享目录 → 工作区 `docs/`（不提交）。
- `questions: open` 时 `stage` 必须是 `questions`，不写 `04`、`05`、`06`，不改业务代码。
- 启动项目、连接 DEV、只读库要先在 `project.yaml` 里写明。只读账号本身不能有写权限。
- 改代码、跑命令、开浏览器用 Cursor 自身的能力。套件负责目录、门禁和该读哪份技能。

## 还没用真实需求走过

功能已经可以安装。下面这些要等一条真实需求走完才算验证过，不代表脚本或技能还没写：

| 项 | 怎样算走过 |
|----|------------|
| 安装 | 父文件夹里有前后端，用仓库地址安装，新开对话后能读到 `.cursor/next-step.txt` |
| 规范 | 对照现有分支确认开关后，`conventions.confirmed` 为 `true` |
| 录屏 | 一场会只产生 `01-meeting.md`，过程文件留在 `asr-watch` 目录 |
| 资料 | Figma、Confluence、PPT 原件在共享目录，摘录在 `02-sources.md`，打不开标未收集 |
| 问题门禁 | 和代码矛盾时，校验拒绝离开 `stage: questions` |
| 分支和开发 | 计划确认后才建 `feature/<需求号>`，一次只做一步 |
| 用例 | `runtime` 为空时不启动、不连库 |

## 现在不要做

- 训练录屏识别模型，或把 FunASR 权重、Chrome 扩展打进本仓库。
- 在套件里保存密码、Cookie、VPN 配置。
- 在没有 `project.yaml` 的情况下连接 DEV。
