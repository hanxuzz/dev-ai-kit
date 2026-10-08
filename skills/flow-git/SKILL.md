---
name: flow-git
description: >-
  按业务仓已有规则提交。没有规则时用套件默认。用户明确说提交或 commit 时使用。
---

# 提交

用户没有明确说「提交」或「commit」时，不要执行 `git commit` 或 `git push`。

按 `docs/runtime.md` 做开始检查，并读 `project.yaml` 的 `conventions`。正在处理的需求 `questions` 为 `open` 时，不要提交这条需求对应的业务改动。

`conventions.confirmed` 不是 `true` 时停止，先走 `skills/flow-conventions/SKILL.md`。

该任务在 `06-plan.md` 里写了验证命令时，本轮要先看到这个命令的退出码，再提交。没跑过就停，不要把「应该能过」写进提交说明。

`commit.only_when_asked` 为 `true` 时，用户没有明确说「提交」或「commit」，不要提交。`push.only_when_asked` 为 `true` 时，用户没有明确说推送，不要推送。`commit.allow_on_base` 不是 `true` 时，不要在 `branch.base`、`main`、`master` 上提交，除非用户在这句话里点名了该分支。`trailer.coauthor` 不是 `true` 时，提交说明里不要写 `Co-authored-by`。

这些开关不覆盖该代码仓 `.cursor/rules` 里已有的 git 规则。仓库规则更严时，按仓库规则。

## 哪个仓库

工作区根通常不是 git 仓库。进入用户点名的那个代码目录（`project.yaml` 的 `repos`）再执行 git。该目录没有 `.git` 就停止。不要在父文件夹里提交。

不要加入：`project.local.yaml`、`skill.md`、录屏、转写过程、`docs.mode` 为 `local` 时的文档根、任何密钥文件。提交前用 `git status` 核对路径，发现这些路径就拿掉。

## 规则优先级

1. 该代码仓 `.cursor/rules` 里已有的提交规则全部照做，不要修改那些文件。
2. 没有项目规则时才用默认：

- 只加入本次相关文件，不要 `git add .`
- 提交说明写清楚为什么改
- 不写 `Co-authored-by`
- 不执行 `git push`。用户没有明确说 push，就不要推

提交完成后告诉用户：哪个目录、提交说明、有没有推送。
