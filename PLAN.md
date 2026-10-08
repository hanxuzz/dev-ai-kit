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

- 套件每台机器一份，放在用户文档目录。
- `skill.md` 只安装一次。之后靠 `.cursor/rules/dev-ai-kit.mdc`，技能从 `project.local.yaml` 的 `kit.path` 读取。
- 文档去处：工作区中的文档库 → OneDrive 共享目录 → 工作区 `docs/`（不提交）。
- `questions: open` 时 `stage` 必须是 `questions`，不写 `04`、`05`、`06`，不改业务代码。
- 启动项目、连接 DEV、只读库要先在 `project.yaml` 里写明。只读账号本身不能有写权限。
- 改代码、跑命令、开浏览器用 Cursor 自身的能力。套件负责目录、门禁和该读哪份技能。

## 还没做完

| 项 | 验收 |
|----|------|
| 安装演练 | 在含 frontend、backend 的父文件夹上跑通 `install.ps1`。`documents` 这类目录不会被当成文档库。已有 `project.yaml` 时，换 `-DocsMode` 会失败并提示改文件 |
| 真实录屏 | 一场会只产生 `01-meeting.md`，transcript 和帧留在 `asr-watch` 的过程目录 |
| 真实资料 | Figma、Confluence、PPT 的原件在共享目录，摘录在 `02-sources.md`，打不开时标未收集 |
| 问题门禁 | 故意留一条和代码矛盾的描述时，校验拒绝 `stage: impact` |
| 开发顺序和用例 | 确认后才有 `06-plan.md`。`runtime` 为空时不启动、不连库 |
| 提交 | 只在用户说提交时，进入具体代码仓。不覆盖该仓已有 git 规则。`rules/git.mdc` 先不自动复制到业务仓 |
| 技能接入 | 把 `skills/` 接到用户级技能目录。`kit.yaml` 的 `git` 填上远程后，别的机器才能克隆 |

## 现在不要做

- 训练录屏识别模型，或把 FunASR 权重、Chrome 扩展打进本仓库。
- 在套件里保存密码、Cookie、VPN 配置。
- 在没有 `project.yaml` 的情况下连接 DEV。
