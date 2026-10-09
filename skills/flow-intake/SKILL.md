---
name: flow-intake
description: 登记新需求或接管已有 Spec/计划，保留原件并建立状态；不实施业务代码。
---

# 登记与接管

先读 `docs/fit.md` 选择 quick/standard/cross-system；先确认当前工作区和文档落点，不要求未接管需求先通过就绪校验。

1. 有工单号用工单号，否则从用户描述提炼稳定短名。目录已有时接管，不另建同义需求。
2. `kit adopt --workspace <工作区> --id <需求号> --profile <级别>` 预览；授权登记或接管已明确时加 `--apply`。
3. 读取已有材料，为 files 建立映射；不要猜测旧文档的确认状态或已完成任务。已有历史保存在 legacy 和备份中。
4. 按实际来源登记 sources。没有录像、没有设计稿是正常情况；明确记录 skipped 和原因，下次不重复询问。
5. quick 可使用一份 brief。标准/跨系统沿用现有文件，结构化 R/TASK/T 由 Agent 提取，用户只确认业务含义，不要求用户手填 YAML。
6. 用 prepare 写入整理内容，再读取 next。只报告当前缺口；不能因为 next 给出开发动作就自行执行。

current 只在状态建立后更新。切换已登记需求使用 select；不因为目录多就忽略明确的 current。
