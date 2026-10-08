---
name: flow-conventions
description: >-
  先收集项目已有的分支和提交规范，写进 team/conventions.md，再决定套件开关。
  用户说确认规范、分支规范，或 conventions.confirmed 还不是 true 时使用。
---

# 先收集项目已有规范

读套件 `docs/conventions.md` 和 `docs/trust.md`。改代码或建分支之前做完这里。起草背景、接上已有需求可以先做。

项目里已经有规范时，以项目的为准。套件的开关只补项目没写的部分，不另起一套分支做法。

## 收集

对工作区根和 `project.yaml` 里每个代码目录，读这些文件（有哪个读哪个，没有就跳过）：

- `AGENTS.md`
- `README.md` 里写分支、提交、环境的章节
- `CONTRIBUTING.md`
- `.cursor/rules/` 下的规则

用 git 只看现状，不据此发明规范：

```text
git -C <目录> rev-parse --abbrev-ref HEAD
git -C <目录> symbolic-ref --short refs/remotes/origin/HEAD
```

`origin/HEAD` 是 `main` 只说明远程默认分支，不是开发要从 `main` 开分支。

把读到的规矩整理进文档根的 `team/conventions.md`（没有就从套件 `templates/team/conventions.md` 复制后再填）。每条写清来自哪个文件。文件已有人改过的「确认」内容不要整篇覆盖，只补来源和还没写上的规矩。不要改写各仓库原来的 `AGENTS.md` 和规则文件。

一份都没有时，在 `team/conventions.md` 写「未找到」，确认清单里改成向用户提问，不要替用户填套件默认。

## 确认清单

收集写完后，在本轮对话里按顺序问。读到了就写出文件路径和原话，问「是这样吗」。没读到就直接问用户定。不要把这些问题收成一句让用户复制。问完就停，不要接需求、不要改代码。

1. 功能分支从哪条分支拉出？远程默认分支只作参考，不要当成答案。
2. 分支名叫什么？需求号怎么嵌进去？
3. 做完后怎么进后续环境？例如只在功能分支提交，再 cherry-pick，还是由人合并。
4. 套件能不能自己建分支、能不能自己 push？
5. 什么时候允许提交？提交说明要写成什么样？
6. 哪些文件不能提交？提交说明里要不要禁止 `Co-authored-by`？

六项都得到用户的肯定或修改之后，才按下面「开关怎么填」把 `confirmed` 写成 `true`。某一项用户说「以仓库原文为准」，就按收集到的那句，不要再改成套件默认。

## 开关怎么填

先把收集结果告诉用户，请用户确认或补充。这是安装之后的第一件事，先于项目背景和具体需求。用户没说「规范已确认」之前，不要把 `confirmed` 写成 `true`，也不要建分支、不要改业务代码。

用户明确同意后，才改 `project.yaml` 的 `conventions`：

- 收集里已经有分支做法：`branch.enabled` 写成 `false`，`branch.base` 留空。开发、提交、推送按 `team/conventions.md` 和仓库原文。
- 只有用户明确说「项目没有分支规范，由套件从某条主干建分支」时，才把 `branch.enabled` 写成 `true`，`branch.base` 用用户说的那条。
- 项目已经写了「不代 push」「禁止 Co-authored-by」「不在某条主干上提交」时，对应开关按更严的那一边：`push.only_when_asked: true`，`trailer.coauthor: false`，`commit.allow_on_base: false`。
- `confirmed` 写成 `true`，表示收集结果已经确认。这不表示套件开始建分支。

不要替用户把 `confirmed` 写成 `true`。确认后跑 `scripts/next.ps1`，把下一句告诉用户。

## 用户补充

用户提出新的规矩，或要改掉收集到的某一条时：

1. 写进 `team/conventions.md`，不要改仓库里的 `AGENTS.md`、`README`、`.cursor/rules`。
2. 在「来源」表加一行：仓库写「用户」，文件写「对话」，管什么写这一条。
3. 按内容补进「分支」「提交」或「套件不要覆盖的红线」。和已收集的原文冲突时，两句都留着，并写明以用户这次说的为准。
4. 同步 `project.yaml` 的开关，且不得松于套件硬限制：不 force push，不改 git config，不跳过钩子，口令不进文件。用户没要求套件建分支时，`branch.enabled` 保持 `false`。
5. 改完把更新后的那几句念给用户。用户再说「规范已确认」后，才把 `confirmed` 写成 `true`。
