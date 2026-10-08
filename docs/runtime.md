# 运行约定

安装和校验以脚本的退出码为准。脚本失败时，技能停止，不用对话里的临时文件顶上。

| 脚本 | 作用 | 成功 |
|------|------|------|
| `scripts/install.ps1` | 写工作区配置、规则、`team/` 骨架。已有的 `project.yaml`、`project.local.yaml` 和改过的规则不覆盖 | 退出码 0，末行 `OK install` |
| `scripts/validate.ps1` | 检查文档落点、需求状态、问题门禁 | 退出码 0，末行 `OK validate` |
| `scripts/next.ps1` | 根据已有文件给出下一句该说什么，并写入工作区 `.cursor/next-step.txt` | 退出码 0。以该文件里的「下一步就做这一句」为准 |
| `scripts/check.ps1` | 检查 `asr-watch`、`ffmpeg`、`agent-browser` 是否存在 | 只打印 OK / MISSING，不安装 |

Windows：

```text
<套件克隆目录>\scripts\install.ps1 -Workspace <业务项目文件夹> -Kit <套件克隆目录>
<套件克隆目录>\scripts\validate.ps1 -Workspace <业务项目文件夹>
```

`install.ps1` 会在结束时自己再跑一次 `validate.ps1`。

## 路径怎么算

`project.yaml` 不写本机绝对路径。

| `docs.mode` | 文档根 |
|-------------|--------|
| `local` | `<工作区>/<docs.path>`，且不能落在任何一个代码仓的 git 目录里面 |
| `share` | `<project.local.yaml 的 share.path>/<docs.path>` |
| `repo` | `<工作区>/<docs.path>`，并且这里本身是 git 仓库 |

工作区根如果自己就是一个代码仓（里面有 `.git`），安装直接失败。要打开的是同时包含前后端的父文件夹。

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
