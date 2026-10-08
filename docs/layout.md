# 目录规范

所有技能都读写这里列出的文件名。不要另起 `notes.md`、`需求.md`、`asr-out/` 之类的并行目录。编号和「一条需求要能判断做对没有」见 [`practices.md`](practices.md)。谁说了算见 [`trust.md`](trust.md)。安装、校验和失败时怎么停，见 [`runtime.md`](runtime.md)。脚本不通过，就还没安装好或这条需求不能往下走。

## 工作区根（Cursor 打开的那一层）

| 文件 | 谁产生 | 是否提交 |
|------|--------|----------|
| `skill.md` | 人从套件 `bootstrap/SKILL.md` 复制 | 否，安装完可留在本地 |
| `project.yaml` | 安装技能 | 若工作区不是 git 仓库，则无所谓；不要把本机绝对路径写进来 |
| `project.local.yaml` | 安装技能 | 否。本机套件路径、OneDrive 路径只放这里 |
| `.cursor/rules/dev-ai-kit.mdc` | 安装技能，来自套件 `rules/dev-ai-kit.mdc` | 随团队约定。建议提交，里面没有本机路径 |

## 文档根

由 `project.yaml` 的 `docs.path` 决定，记为 `<文档根>`。

```text
<文档根>/
  README.md                 # 写明 mode，以及 local 时不要提交
  team/
    README.md
    background.md
    glossary.md
    map.md
    roles.md
    decisions.md
  requirements/
    <需求号>/
      status.yaml
      01-meeting.md
      02-sources.md
      03-questions.md
      04-requirement.md
      05-impact.md
      06-plan.md
      07-testcases.md
```

需求号：有工单号用工单号；否则 `REQ-YYYYMMDD-短名`。短名用小写英文和连字符。

## status.yaml

```yaml
id: REQ-20261008-new-page
title: ""
stage: intake
questions: none
blocker: ""
```

`stage` 只用：`intake`、`meeting`、`sources`、`questions`、`requirement`、`impact`、`plan`、`build`、`test`、`done`。

`questions` 只用：`open`、`none`、`confirmed`。

`questions: open` 时，`stage` 必须是 `questions`，并且目录里不得出现 `04-requirement.md`、`05-impact.md`、`06-plan.md`。`scripts/validate.ps1` 会检查这件事。

`blocker` 为空表示没有工具故障。转写失败、录像未同步这类原因写在这里，不要写成会议结论。

文件按阶段出现，新建需求时只有 `status.yaml`：

| stage 到达 | 必须已经有 |
|------------|------------|
| meeting | `01-meeting.md` |
| sources | `02-sources.md` |
| questions | `03-questions.md` |
| requirement | `04-requirement.md` |
| impact | `05-impact.md` |
| plan / build | `06-plan.md` |
| test / done | `07-testcases.md` |

## 共享目录

`project.local.yaml` 的 `share.path`。没有配置则跳过同步，并在对话里说明问题清单只有本地一份。

```text
<共享目录>/
  index.md
  docs/                          # 仅当 docs.mode=share 时，文档根就是这里
  requirements/
    <需求号>/
      （录像、PPT、PDF、图片原件）
      03-questions.md            # 给需求方看的副本
```

`index.md` 用相对共享目录的路径。技能不遍历共享目录全盘。

## 不写进文档根的过程文件

| 内容 | 位置 |
|------|------|
| 转写全文、抽帧、wav、run.log | `%USERPROFILE%\.local\share\asr-funasr\runs\<视频名>\` |
| 数据库口令 | Bitwarden。`project.yaml` 只写文件夹和条目名 |

## 技能读写关系

| 技能 | 读 | 写 |
|------|----|----|
| flow-intake | `project.yaml`、`team/` | 只建需求目录和 `status.yaml`，并更新 `current` |
| flow-meeting | 共享目录索引、`glossary.md`、录像、转写文件 | `01-meeting.md`；失败时只写 `blocker` |
| flow-sources | 用户给的链接和原件 | `02-sources.md`；冲突则追加 `03-questions.md` |
| flow-impact | `01`、`02`、`team/`、前后端代码 | 有冲突则只写 `03-questions.md`；确认后才写 `04` 与 `05` |
| flow-plan | `04`、`05`，且 questions 不是 open | `06-plan.md` |
| flow-implement | `06-plan.md`、代码仓 `AGENTS.md` | 只改当前任务点名的代码，并勾选该任务 |
| flow-test | `04`、`06`、`project.yaml` 的 runtime | `07-testcases.md`；命令为空则只写配置说明 |
| flow-git | 业务仓现有规则、`06-plan.md` | 按用户当次要求提交，不写新的需求文档 |
