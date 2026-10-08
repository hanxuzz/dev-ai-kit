# 使用手册

业务项目要已经有代码，并用 Cursor 打开包住前端和后端的那一层。什么项目适合，见 [docs/fit.md](docs/fit.md)。这套工具是做什么的、能做哪些事，见 [开始.md](开始.md)。写代码和注释时，项目仓库里的规范优先，没有则见 [docs/code-style.md](docs/code-style.md)。分支和提交的默认开关见 [docs/conventions.md](docs/conventions.md)，安装后先确认再开始做需求。

## 1. 安装一次

照着 [开始.md](开始.md) 打开业务文件夹，把仓库地址发到对话里，再新开对话。不必复制 `skill.md`。本节不再重复那段话。

装好之后：

- 文档在本地 `docs/` 时不提交。已有名为 `docs` 的文档库，或有 OneDrive 共享目录时，以安装时的选择为准。
- 已经生成过 `project.yaml` 之后，再跑安装不会改文档放哪。要换就直接改这个文件。
- 机器路径在 `project.local.yaml`，不要提交。
- 依赖没装好时看 [docs/dependencies.md](docs/dependencies.md)。

## 2. 共享目录

```text
psl-share/
  index.md
  requirements/
    <需求号>/
      （录屏、PPT、PDF、图片）
      03-questions.md
```

`docs.mode` 为 `share` 时，整理后的 Markdown 在这个共享目录的 `docs/` 里。每人电脑上的 OneDrive 路径不同，只写进 `share.path`。

## 3. 一条需求

需求号在开会前就定。没有工单号时用 `REQ-20261008-new-page` 这种英文短名。

新建时只有 `status.yaml`：

```yaml
id: REQ-20261008-new-page
title: ""
stage: intake
questions: none
blocker: ""
```

`01` 到 `07` 走到对应阶段才出现。字段含义、技能和文件的对应关系见 [docs/layout.md](docs/layout.md)。

`questions: open` 时阶段必须是 `questions`。需求方确认之前，没有最终需求、影响点和开发顺序，也不改代码。问题清单会复制到共享目录，方便需求方直接看。

## 4. 你可以怎么说

- 「根据当前前后端起草项目背景。」文首保持未确认。
- 「新建需求 REQ-…。」
- 「解析这个需求的录屏。」
- 「把这些链接和共享目录里的 PPT 收进这个需求。」
- 「对照代码整理需求；有问题先列出来。」
- 「需求方已确认，更新需求和影响点。」
- 「写出开发顺序。」
- 「做计划第 2 步。」规范里打开了分支时，会先在要改的仓库建好或切到 `feature/<需求号>`，再改这一步。改完必须跑任务里的验证命令，通过与否以这次输出为准。
- 「整理并执行这个需求里标了 auto 的用例。」

每一步写完文件后都会再跑 `scripts/validate.ps1`。失败就停在 `FAIL` 那一行。

## 5. 本机启动、DEV、只读库

这些不是默认能力。`project.yaml` 的 `runtime.backend.start`、`runtime.frontend.start`、`runtime.test` 为空时不执行。`runtime.database.readonly` 不是 `true` 时不连库。只读指数据库账号没有写权限。条目名写在 `runtime.database.bitwarden`，口令留在 Bitwarden。

浏览器上的操作走本机的 `agent-browser`。扩展不在这个仓库里，第一次按 [docs/dependencies.md](docs/dependencies.md) 安装。

## 6. 提交

你没有明确说提交时，不会提交，也不会推送。进入 `project.yaml` 里点名的那个代码目录再执行 git。该仓库已有的提交规则优先。`conventions.confirmed` 还不是 `true` 时不建分支、不改代码。确认之后，只有 `branch.enabled` 为 `true` 才建分支；默认是关掉的，避免和「从 `prod` 开功能分支再 cherry-pick、不代 push」冲突。`runtime` 留空时不启动、不连库。`project.local.yaml`、录屏和转写过程不提交。
