# dev-ai-kit

仓库：https://github.com/hanxuzz/dev-ai-kit

把业务需求材料转成可追溯、可确认、可验证的 AI 开发任务。支持单仓、多仓、已有规格接管与跨对话恢复。

0.3 在统一状态与证据的基础上，提供开始、继续、变更、检查交付四种意图入口。明确小修复复用原始授权；范围变更展示差异并保留无关工作；恢复时说明未完成和未验证内容。

套件只维护通用流程与规范。Agent 必须主动收集、核实项目独有信息并应用到配置和任务，持续追踪来源变化；不预设项目技术栈、启动命令或测试框架。

- 项目发现与适配：[docs/project-context.md](docs/project-context.md)
- 开发行为与代码质量闭环：[docs/development-quality.md](docs/development-quality.md)
- 默认进度与下一步反馈：[docs/progress-feedback.md](docs/progress-feedback.md)
- 使用入口：[开始.md](开始.md)
- 开发者日常使用：[MANUAL.md](MANUAL.md)
- 安装、升级、恢复：[docs/runtime.md](docs/runtime.md)
- 配置、文件映射和状态：[docs/schema.md](docs/schema.md)
- 小修复与复杂需求：[docs/fit.md](docs/fit.md)
- 权限与资料依据：[docs/trust.md](docs/trust.md)
- 测试生成、任意原件规范化与本地/dev 执行：[docs/test-automation.md](docs/test-automation.md)
- 浏览器执行与录像取证：[docs/browser-testing.md](docs/browser-testing.md)
- 需求录屏解析：[docs/recording-analysis.md](docs/recording-analysis.md)
- 分层测试：[docs/testing.md](docs/testing.md)
- 本轮取舍与限制：[docs/decisions-0.3.md](docs/decisions-0.3.md)
- 已实现与后续验证：[PLAN.md](PLAN.md)

运行需要 Python 3.10+、Git 和 requirements.txt。PowerShell/shell 入口共用一个核心，首次安装依赖见运行文档。
套件不保存密码、不代建业务代码仓、不自动提交或部署；不要求每条任务都运行浏览器全链路 E2E。
