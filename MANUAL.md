# 日常手册

命令前缀 `kit` 的替换方式见 [docs/runtime.md](docs/runtime.md)。每次变更状态后使用返回的新 revision，不缓存旧值。

## 一条需求

```text
kit adopt --workspace <工作区> --id REQ-123 --profile standard
kit adopt --workspace <工作区> --id REQ-123 --profile standard --apply
kit prepare --workspace <工作区> --expect 0 --input <整理包.yaml>
kit validate --workspace <工作区> --ready
kit confirm --workspace <工作区> --expect 1 --by <实际确认人> --note <确认依据>
kit next --workspace <工作区>
kit start --workspace <工作区> --target TASK-1 --expect 2
```

Agent 在明确授权内修改业务代码，然后：

```text
kit run --workspace <工作区> --check <配置的检查名> --expect 3
kit finish --workspace <工作区> --target TASK-1 --expect 4
kit next --workspace <工作区>
kit complete --workspace <工作区> --expect 5 --by <实际验收人> --note <验收结论>
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
安装失败恢复、并发冲突、旧版本迁移见 [运行文档](docs/runtime.md)。
