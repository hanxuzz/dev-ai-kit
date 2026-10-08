---
name: flow-impact
description: >-
  对照前后端代码整理冲突、最终需求和影响点。用户说理解需求、列影响点、和需求对一下时使用。
---

# 问题、最终需求、影响点

按 `docs/runtime.md` 做开始检查，并读 `docs/trust.md`。先读 `team/`（背景未确认要在产出文首注明）、已有的 `01-meeting.md` 和 `02-sources.md`，以及每个代码仓的 `AGENTS.md` 或 `README`。只读代码，这一阶段不改业务代码。

`current` 为空且需求目录多于一个时，先问做哪一条。

本机有 `codegraph` 命令时，可以先用它看相关调用链，再用读到的文件核对。没有就直接读代码。

两份资料都没有、也没有 `files.requirement` 指向的规格时停止，不要凭一句口头需求写出影响点。已有规格时，规格就是需求来源，不必先有会议纪要。

`files.impact` 若和 `files.requirement` 或 `files.plan` 是同一个文件，那不是影响点。清空这项，另写 `05-impact.md`。规格和按天计划都不要改名为影响点。

## 先写问题

写进 `03-questions.md`（没有就从模板创建）：

- 会议和 Confluence、Figma、PDF 互相矛盾
- 资料里的行为和代码里读到的现状不一致
- 术语对不上 `glossary.md`，而且会影响改哪些文件
- 声称要改的路径在仓库里不存在

每一行要写「资料怎么说」和「代码里实际是什么」，并带上读过的文件路径。没有读到文件，就不要写「代码里没有这个功能」。不要为了填满而编造冲突。

没有任何问题时：`questions` 设为 `none`，再写下面两份文件。

有问题时：`questions` 设为 `open`，`stage` 设为 `questions`。不要创建 `04-requirement.md`、`05-impact.md`、`06-plan.md`。配置了共享目录则把 `03-questions.md` 复制到 `<共享目录>/requirements/<需求号>/03-questions.md`，复制失败就写入 `blocker` 并告诉用户。然后跑 `validate.ps1`。告诉用户把清单给需求方，确认后再来说「按确认结果更新」。

## 确认之后

用户带来结论时，把结论写回问题表。仍有未确认行就保持 `open` 并停止。全部有结论后，`questions` 改为 `confirmed`，`blocker` 清空。然后：

- 从模板写 `04-requirement.md`。每条 `R` 只写一件已确认的事，并写上来源编号（`M` / `S` / `Q`）。验收用「给定 / 当 / 则」。写不出「则」的不要收进 `04`，留在问题清单。
- 从模板写 `05-impact.md`。每个 `C` 对应一条 `R`，并标明是「修改」还是「新增」。「修改」必须是仓库里真实存在的路径，「新增」可以还不存在。路径对不上的项移回 `03-questions.md`，重新把 `questions` 设为 `open`，删掉刚写的 `04` 和 `05`，停止
- 路径都存在时，`stage` 改为 `impact`，再跑 `validate.ps1`

已有人改过的段落不要整篇覆盖。背景文件只在用户要求更新项目背景时才改，并且只补变化的小节。
