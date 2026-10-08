---
name: flow-conventions
description: >-
  安装后对照各代码仓的现有分支，确认套件自带的分支和提交规范要打开还是关掉。
  用户说确认规范、分支规范，或 conventions.confirmed 还不是 true 时使用。
---

# 确认分支和提交规范

读 `docs/conventions.md` 和 `docs/trust.md` 里的「严和松」。`project.yaml` 里没有 `conventions`，或 `confirmed` 不是 `true` 时，改代码和建分支之前做完这里。起草背景、接上已有需求、整理材料可以先做。

## 看现状

对 `project.yaml` 的 `repos` 里每一个目录：

```text
git -C <目录> rev-parse --abbrev-ref HEAD
git -C <目录> symbolic-ref --short refs/remotes/origin/HEAD
```

第二条没有输出就说明远程默认分支还不知道，问用户主干叫什么。再看工作区根的 `AGENTS.md`，以及该目录 `.cursor/rules/` 里有没有提交或分支规则。有的话列出来，建议关掉 `branch.enabled`，并说明这些规则优先，套件开关不覆盖它们。

## 请用户逐项确认

按 `docs/conventions.md` 的表，说出建议值和仓库里看到的主干。问哪些打开、哪些关掉。不要替用户把 `confirmed` 写成 `true`。

用户明确同意后，只改 `project.yaml` 的 `conventions`：

- `branch.base` 用用户确认的主干名
- 关掉的项写成 `false`，打开的写成 `true`
- `confirmed` 写成 `true`

然后跑 `scripts/next.ps1`，把下一句告诉用户。
