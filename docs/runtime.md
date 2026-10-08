# 运行约定

安装和校验以脚本的退出码为准。脚本失败时，技能停止，不用对话里的临时文件顶上。

| 脚本 | 作用 | 成功 |
|------|------|------|
| `scripts/install.ps1` | 写工作区配置、规则、`team/` 骨架。已有的 `project.yaml`、`project.local.yaml` 和改过的规则不覆盖 | 退出码 0，末行 `OK install` |
| `scripts/validate.ps1` | 检查文档落点、需求状态、问题门禁 | 退出码 0，末行 `OK validate` |
| `scripts/next.ps1` | 决定当前这一步由 Agent 做，还是有一个问题必须问用户 | 退出码 0。认 `下一步由你来做` 和 `下一步请用户定` |
| `scripts/check.ps1` | 检查 `asr-watch`、`ffmpeg`、`agent-browser` 是否存在 | 只打印 OK / MISSING，不安装 |

Windows：

```text
<套件克隆目录>\scripts\install.ps1 -Workspace <业务项目文件夹> -Kit <套件克隆目录>
<套件克隆目录>\scripts\validate.ps1 -Workspace <业务项目文件夹>
```

`install.ps1` 会在结束时自己再跑一次 `validate.ps1`。

`runtime` 里启动命令、测试命令或 `database.readonly` 为空，是正常状态。套件不为此启动服务，也不连接数据库。本地怎么跑、DEV 只读库以业务仓已有规则为准。口令不写进 `project.yaml` 或需求文档。只有用户这次明确要跑测试或连库，并且对应字段已经填好，才执行。

`project.yaml` 不写本机绝对路径。

| `docs.mode` | 文档根 |
|-------------|--------|
| `local` | `<工作区>/<docs.path>`，且不能落在任何一个 git 目录里面。只用于工作区本身不是 git 仓库 |
| `tracked` | `<工作区>/<docs.path>`，跟这个工作区一起提交。父仓库自己有 `.git`，文档本来就在里面时用这个 |
| `share` | `<project.local.yaml 的 share.path>/<docs.path>` |
| `repo` | `<工作区>/<docs.path>`，并且这里本身是另一个 git 仓库 |

工作区自己有 `.git`，同时下面还有代码目录时，可以安装。只打开某一个代码仓、下面没有代码目录时，安装失败。

需求目录是 `<文档根>/<docs.requirements_dir>/<需求号>/`。已经有 `requirement` 而没有 `requirements` 时，安装把 `requirements_dir` 记成 `requirement`，不另建空目录。

## 当前需求

`project.local.yaml` 的 `current` 是当前需求号。用户点名了别的号，先改 `current` 再写文件。`current` 指向的目录不存在时，校验失败。

## 状态机

只允许 `docs/layout.md` 里的 `stage` 和 `questions`。校验会拒绝：

- `questions: open` 同时又处于 `plan` / `build` / `test` / `done`
- `questions: open` 时目录里已经有 `04-requirement.md`、`05-impact.md` 或 `06-plan.md`
- `stage` 已经走到某一步，但对应文件不存在
- 文档落在代码仓内部，而 `docs.mode` 仍是 `local`

`blocker` 非空不会让校验失败（下一条需求还能用），但规则要求先把这句话告诉用户并停在这条需求上。工具失败（转写命令失败、录像还没同步）时写入 `blocker`，不要写一份看起来完整的结论。

## 文件什么时候才创建

新建需求时只创建 `status.yaml`。`01` 到 `07` 由对应技能在那一步从 `templates/requirements/` 复制后再填。不要一次把后面的空文件都建出来，否则门禁无法区分「还没做」和「已经做了」。
