---
name: flow-intake
description: >-
  在 dev-ai-kit 文档根下新建一条需求目录。用户说新建需求、登记需求、建需求文件夹时使用。
---

# 新建需求目录

按 `docs/runtime.md` 做开始检查。`validate.ps1` 失败就停止。`docs.mode` 为 `local` 时不要提交新建的文件。

1. 需求号：用户给了工单号就用；否则 `REQ-当天日期-短名`。短名向用户要，或从用户那句话里取一个英文连字符短名。需求目录在 `<文档根>/<docs.requirements_dir>/<需求号>/`。`requirements_dir` 为空时用 `requirements`。
2. 目录已经存在：不要删除、不要改名、不要覆盖里面的文件。没有 `status.yaml` 就只补这一份，`stage` 为 `intake`，`questions` 为 `none`，`blocker` 为空。不要复制 `01` 到 `07`。
3. 目录不存在才新建，并且只放 `status.yaml`。不要复制 `01` 到 `07`。
4. 把 `project.local.yaml` 的 `current` 写成这个需求号。
5. 若 `share.path` 非空，在 `<共享目录>/requirements/<需求号>/` 建空目录，并提醒用户把录像、PPT、PDF 放这里，同时在共享目录 `index.md` 加一行。没有共享目录就说明原件还没有落点。已经在需求目录里的文件不要搬出去。
6. 再跑一次 `validate.ps1`。失败则只删除这次新建且仍为空的目录；原来就有的目录不要删。把 `FAIL` 告诉用户。成功则运行 `scripts/next.ps1`，把「下一步就做这一句」告诉用户。

需求号一旦写进 `status.yaml` 就不要另起一个意思相同的目录。后面的 `M`、`R`、`T` 都挂在这个号上。编号规则见 `docs/practices.md`。
