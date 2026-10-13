---
name: flow-entry
description: 将开发者开始、继续、变更和检查交付的自然语言请求接入已安装的 dev-ai-kit；维护状态，不要求用户记命令或任务编号。
---

# 从开发意图开始

开始前按 [flow-project-context](../flow-project-context/SKILL.md) 主动核对本步骤依赖的项目事实，将核实结果应用到项目配置与材料；来源变化只复核受影响部分，不拿套件示例代替实际项目约定。

先读取 project.yaml/project.local.yaml，命令入口见套件 [运行文档](../../docs/runtime.md)。用户无需调用技能名字或选择流程级别；只解释代码时直接回答。

- **开始**：先看代码与已有工单/规格。`assist begin` 预览；Agent 提炼稳定 id、真实文件范围、验收、不做事项和现有检查，已授权时 `--apply`。与已确认需求不冲突的首次简单请求可由原话同时表达范围确认和执行授权，用实际 `--by`、`--authorization-note` 记录，不再询问同一决定。缺少执行意图时不要补造授权。quick 生成最小 brief 与映射；standard/cross-system 转 [登记](../flow-intake/SKILL.md) 和 [计划](../flow-plan/SKILL.md)，沿用已有材料。
- **继续**：`assist resume` 读取已完成、doing、代码变化、过期验证及交接。仅询问进度时只报告；明确要求继续时按原授权接续 [实施](../flow-implement/SKILL.md)。doing 不再 start；revision 由 Agent 读取、更新，不让用户填写。
- **变更**：按 [变更](../flow-change/SKILL.md) 用 `assist change` 预览差异，展示旧要求及来源、新要求、影响与保留部分；按 docs/trust.md 等用户针对差异二次明确确认后才应用和修改。首次新请求即使明确也不能充当二次确认，不重新确认无关部分。
- **检查交付**：`assist review` 只读诊断，再按 [验证](../flow-test/SKILL.md) 处理缺口。review 不自动执行检查或表示用户已验收。

命令参数见 [Agent 参考](../../docs/cli-reference.md)。profile 自动推荐只是启发式，必须核对实际业务风险和检查覆盖，不能用关键词代替判断。默认回复当前结果、缺口和下一步，不输出内部状态表。

生成/导入测试用例、启动本地或连接 dev 测试时，转 [flow-testing](../flow-testing/SKILL.md)：主动解析用户原件并按统一规范导入，不要求用户先转格式。

开发实施必须走 flow-plan/flow-implement 的行为与项目实现依据，并在 finish 前执行 [flow-code-review](../flow-code-review/SKILL.md)。quick 也需要实际参考及回归依据，但记录可简短；不要让用户为内部步骤反复确认。

每轮结束必须按 [进度反馈协议](../../docs/progress-feedback.md) 主动说明本轮结果、当前进度和下一步责任方。状态更新返回的 progress 可直接作为事实依据；需要用户决定时读实际问题/差异并具体提问，不让用户猜下一步。

明确要求浏览器操作测试时，转 flow-testing 的浏览器操作协议：发现并调用当前环境适用技能，实际打开浏览器操作验收场景，不以其他层次测试替代。

套件反馈须有可辨认的作用：开始时说明本轮使用的流程；阶段变化或遇到问题主动同步；每轮结束按 docs/progress-feedback.md 简短说明“dev-ai-kit 本轮实际做了什么 / 当前阶段与真实进度 / 下一步和责任方”。只报实际执行和记录，不虚构检查、不把历史结果当本轮成果；普通问答未调用套件不强行贴标签。
