---
name: flow-intake
description: >-
  在 dev-ai-kit 文档根下新建一条需求目录。用户说新建需求、登记需求、建需求文件夹时使用。
---

# 新建需求目录

按 `docs/runtime.md` 做开始检查。`validate.ps1` 失败就停止。`docs.mode` 为 `local` 时不要提交新建的文件。

1. 需求号：用户给了工单号就用；否则 `REQ-当天日期-短名`。短名向用户要，或从用户那句话里取一个英文连字符短名。目录已存在就停止，不要再建一个同义目录。
2. 只创建 `<文档根>/requirements/<需求号>/status.yaml`，从 `templates/requirements/status.yaml` 复制后填 `id`、`title`。`stage` 为 `intake`，`questions` 为 `none`，`blocker` 为空。不要复制 `01` 到 `07`。
3. 把 `project.local.yaml` 的 `current` 写成这个需求号。
4. 若 `share.path` 非空，在 `<共享目录>/requirements/<需求号>/` 建空目录，并提醒用户把录像、PPT、PDF 放这里，同时在共享目录 `index.md` 加一行。没有共享目录就说明原件还没有落点。
5. 再跑一次 `validate.ps1`。失败则删除这次新建的目录，把 `FAIL` 告诉用户。成功则运行 `scripts/next.ps1`，把「下一步就做这一句」告诉用户。

需求号一旦写进 `status.yaml` 就不要另起一个意思相同的目录。后面的 `M`、`R`、`T` 都挂在这个号上。编号规则见 `docs/practices.md`。
