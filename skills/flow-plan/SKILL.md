---
name: flow-plan
description: >-
  在需求已确认后写开发顺序 06-plan.md。用户说写开发计划、排开发顺序时使用。
---

# 开发顺序

按 `docs/runtime.md` 做开始检查，并读 `docs/trust.md`。`questions` 为 `open` 时停止，不要创建 `06-plan.md`。

需求正文和影响点先看 `status.yaml` 的 `files.requirement`、`files.impact`。这两项为空才看 `04-requirement.md`、`05-impact.md`。指向的文件不存在，或正文过短、仍是空模板时，停止。不要凭会议记录补任务，也不要另建一份空的 `06` 盖住已有计划。`files.plan` 已指向一份现有计划时，补进那份文件，不要再复制模板。

从模板写 `06-plan.md`。对照 `docs/practices.md`：有 `R` 写不出「则」，或 `questions` 仍是 `open`，就不要创建这份文件。

- 约束一节抄 `04` 的「不做」，以及代码仓 `AGENTS.md` 里和这次改动有关的红线。
- 每个 Task 只对应一侧，并写上 `R` 和 `C` 编号。
- 「修改」的路径必须在 `05` 或仓库里存在。「新增」的路径标明即可。
- 每步有 `- [ ]`，最后一步是验证命令和期望结果。命令用项目已有的；没有就写「未配置，见 flow-test」，不要发明测试框架。
- 落在「不做」里、或仍然写不出验收的内容放进「不执行」。
- 写完把 `stage` 改为 `plan`，跑 `validate.ps1`。失败则把 `stage` 改回 `impact`，并告诉用户 `FAIL` 内容。

用户没有说「做第 N 步」时，写完顺序就停，不要改业务代码，也不要建分支。分支在开始做某一步时，按 `project.yaml` 的 `conventions` 处理。
