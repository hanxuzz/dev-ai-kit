# 团队规范与分支策略

先收集各仓 AGENTS.md、CONTRIBUTING、README 和规则，记录到 team/conventions.md；现有明确规则一次性确认，重点询问缺项与冲突，不机械重复六个问题。
规范未确认时允许整理材料，业务修改前必须确认。

| branch.mode | 判断 |
|-------------|------|
| project | 用团队确认的 allowed_pattern 检查当前分支；不推断默认分支就是开发基线 |
| current | 用户明确同意使用当前分支，不强制需求分支 |
| feature | 必须符合已确认 base 和 pattern，pattern 支持 `{id}` |

`auto_create` 只表示允许 Agent 按团队规则处理分支；false 不表示可以在错误分支上改代码。核心不会代建/切换分支；发现不符合时，Agent 按会话授权处理或请用户选择。
旧版 branch.enabled 不再决定业务正确性；升级时保留原值供人工核对，补充明确的 mode。

`conventions.confirmed` 需要真实用户确认。记录确认人、时间、规则来源；规则变化后重新确认。配置不是权限系统，不能验证实际操作者身份。
提交和推送均按用户明确要求，保留项目更严格的限制，不 force push、不绕过钩子，不写未要求的 Co-authored-by。

推送权限按 [明确要求即可执行](trust.md#明确要求即可提交或推送) 解读：`push.only_when_asked: true` 不禁止代 push；明确请求已提供授权，不另设“允许套件代操作”的重复门槛。真实分支保护和目标限制仍需遵守。
