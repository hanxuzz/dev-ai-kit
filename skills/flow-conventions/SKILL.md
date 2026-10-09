---
name: flow-conventions
description: 收集和确认业务仓已有规范，区分分支策略与自动操作权限；只在规范缺失或变更时询问。
---

# 团队规范

读各代码仓 AGENTS.md、CONTRIBUTING、README 和规则，保留来源，写入 team/conventions.md，不改项目原文。
一次性展示已经读到的结论，重点问缺项与冲突；用户明确认可已有规范就采用，不要求复述固定口令。

按 `docs/conventions.md` 配置 project/current/feature。`auto_create` 与 mode 分开：禁止代建分支不等于允许在错误分支上开发。
只读当前分支与 Git 现状，不用远端默认分支猜开发基线。用户确认后记录确认人、时间、来源及 conventions.confirmed。
新增或变化的规则需重新确认相应部分；材料整理可以在规范确认前进行，业务修改必须符合已确认规范。

提交、推送、部署分别遵循用户授权。配置开关不能扩大本轮权限。
