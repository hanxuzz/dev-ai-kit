# Agent 命令参考

命令前缀 `kit` 的替换方式见 [docs/runtime.md](runtime.md)。每次变更状态后使用返回的新 revision，不缓存旧值。

## 一条需求

```text
kit adopt --workspace <工作区> --id REQ-123 --profile standard
kit adopt --workspace <工作区> --id REQ-123 --profile standard --apply
kit prepare --workspace <工作区> --expect 0 --input <整理包.yaml>
kit validate --workspace <工作区> --ready
kit confirm --workspace <工作区> --expect <最新revision> --by <实际确认人> --note <确认依据>
kit next --workspace <工作区>
kit start --workspace <工作区> --target TASK-1 --expect <最新revision>
```

Agent 在明确授权内修改业务代码，然后：

```text
kit run --workspace <工作区> --check <配置的检查名> --expect <最新revision>
kit finish --workspace <工作区> --target TASK-1 --expect <最新revision>
kit next --workspace <工作区>
kit complete --workspace <工作区> --expect <最新revision> --by <实际验收人> --note <验收结论>
```

以上 revision 仅示例，实际使用命令返回值。完整示例见 `examples/workflow/`。

## 常用操作

| 情况 | 操作 |
|------|------|
| 切换已有需求 | select --id REQ-456 |
| 查看完整状态/交接 | status --full |
| 人工用例已实际执行 | manual --target case:T1 --result passed --by ... --note ... --expect N |
| 任务采用人工验收 | manual --target task:TASK-1 ... |
| 有阻塞/已解决 | block --note <原因或空字符串> --expect N |
| 范围变化 | change --by ... --note ... --expect N，再 prepare/confirm |
| 保存交接 | prepare 更新 state.handoff，保留当前 scope 确认 |
| 全项目检查 | validate --all；需要就绪检查再加 --ready |

不论通过 API 还是 CLI 记录，by/note 都必须对应真实发生的确认或观察；不能编造人名和结论。
需求问题 open 时先澄清；过期验证需重跑；没有自动命令可以走已约定的人工验收。

## 失败处理

错误有非零退出码和 JSON error，不包含配置原文或凭证。先理解原因，不为了通过而删用例、改验收或伪造确认。
run 失败保留结果摘要和退出码；原始输出未长期保存，需要排障时在授权范围内复现并脱敏查看。
安装失败恢复、并发冲突、旧版本迁移见 [运行文档](runtime.md)。

## 自然意图接口（0.3）

`assist resume --workspace <工作区> [--id ...]` 和 `assist review` 只读。前者返回已完成、进行中、代码变化和验证缺口；后者增加 delivery_ready（证据齐全可供用户验收，不等于已验收）。

```text
kit assist begin --workspace <工作区> --id REQ-copy --request "修改保存提示文案" --repo ui --file src/message.ts --check unit --acceptance "保存成功后显示已保存" --out-of-scope "不改变保存逻辑"
```

默认预览，加 `--apply` 才写入。`--profile` 默认 auto，也可显式 quick/standard/cross-system；`--file/--check/--risk` 可重复。无自动验证可用 `--manual-acceptance <具体步骤>`。
quick 且实际请求已经表达范围与执行授权时，可加 `--by <真实确认者> --authorization-note <原始请求依据>`，生成后复用该确认；不会改代码或自动 start。不要向没有执行意图的请求添加这些参数。standard/cross-system 只登记并转材料整理，避免猜测复杂需求。

```text
kit assist change --workspace <工作区> --expect <最新revision> --input <更新包.yaml>
```

先预览，再在已授权范围加 `--apply`。更新包沿用 prepare，可增加 `change_kind: editorial` 与 `reason`（仅经核对无业务含义变化的文字纠错）。普通结构化变更自动分析影响，不需要输入 scoped。`change_kind: broad` 可显式要求整体复核。应用后需确认的仅是新增决定；用真实依据调用 confirm。底层 `change` 仍保留全量重开语义。

`run --diagnostic-log` 显式保存最近 32 KiB 输出的脱敏版本到业务工作区 `.dev-ai-kit/diagnostics/`，路径只返回本机，不写入证据。默认不落原始日志；日志可能仍有未知敏感格式，分享前检查。JSON 错误附带 code、impact、next_action 和 needs_user_decision；不要求用户处理 revision 冲突等内部维护。

## 测试用例

生成基础种子用 cases draft；任意格式原件由 flow-testing 主动解析为统一 YAML，再用 cases import 预览与应用。原件追踪、审阅、JUnit 映射及本地/dev 环境详见 [测试自动化](test-automation.md)。

## 项目发现

`discover --workspace <工作区> --area testing` 只读列出资料候选、项目事实过期及配置绑定差异。详情见 [项目上下文协议](project-context.md)。它不是自动执行命令的许可，也不代替 Agent 阅读、核实和应用配置。
