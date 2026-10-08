---
name: flow-test
description: >-
  整理 07-testcases.md，并在 project.yaml 已配置时交给 Cursor 执行。
  用户说写测试用例、自测、执行测试用例时使用。
---

# 用例与执行

按 `docs/runtime.md` 做开始检查。`04-requirement.md` 不存在时只停止，不编造用例。

## 整理

把需求里每条 `R` 的验收、测试人员给的步骤、以及影响点里可以核对的行为，写进 `07-testcases.md`（没有就从模板复制）。每条用例写上对应的 `R`。同一条 `R` 没有用例时，写进「未覆盖」并说明原因。每条标 `auto` 或 `manual`。

`auto` 只对应项目里已经存在的测试命令，或 `project.yaml` 的 `runtime.test`。命令写不出来就标 `manual`。不要新造一套测试框架。

## 执行前看配置

读 `project.yaml` 的 `runtime`。

| 字段 | 为空或不是 true 时 |
|------|---------------------|
| `backend.start` / `frontend.start` | 不启动。告诉用户要填的命令 |
| `database.readonly` | 不是 `true` 就不连接数据库。说明需要一个没有写权限的账号，并把 Bitwarden 条目名填进 `runtime.database.bitwarden` |
| `test` | 不跑测试命令。指出要填哪个字段 |

口令只从用户本机的密钥管理读取，不写进需求文档，也不写进命令输出粘贴。连接失败时把现象写入用例文末，并把 `blocker` 设为该现象，不反复重试登录。

页面操作类用例：先按 `docs/dependencies.md` 检查 `agent-browser`。前置不齐就停，并指出技能和扩展所在目录。齐了再按该技能操作浏览器。

只有拿到本轮命令的退出码和输出之后，才能把一条 `auto` 用例写成通过或失败。以前跑过的结果不算。没有退出码就保持未执行。失败时不改断言。同一条命令连续失败 3 次就停止，把现象写入 `blocker`。用户确认这轮自测结束后，把 `stage` 改为 `test` 并跑 `validate.ps1`。
