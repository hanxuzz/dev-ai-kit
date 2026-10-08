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

一份都没有时，在 `team/conventions.md` 写「未找到」，并说明接下来用套件默认。

## 开关怎么填

先把收集结果告诉用户。用户明确同意后，才改 `project.yaml` 的 `conventions`：

- 收集里已经有分支做法：`branch.enabled` 写成 `false`，`branch.base` 留空。开发、提交、推送按 `team/conventions.md` 和仓库原文。
- 只有用户明确说「项目没有分支规范，由套件从某条主干建分支」时，才把 `branch.enabled` 写成 `true`，`branch.base` 用用户说的那条。
- 项目已经写了「不代 push」「禁止 Co-authored-by」「不在某条主干上提交」时，对应开关按更严的那一边：`push.only_when_asked: true`，`trailer.coauthor: false`，`commit.allow_on_base: false`。
- `confirmed` 写成 `true`，表示收集结果已经确认。这不表示套件开始建分支。

不要替用户把 `confirmed` 写成 `true`。确认后跑 `scripts/next.ps1`，把下一句告诉用户。
