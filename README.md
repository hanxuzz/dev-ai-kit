# dev-ai-kit

仓库：https://github.com/hanxuzz/dev-ai-kit

把业务需求材料转成可追溯、可确认、可验证的 AI 开发任务。支持单仓、多仓、已有规格接管与跨对话恢复。

0.2 的核心是统一状态和证据：查看下一步不会自动执行；修改范围需确认；每条需求都有任务和验收；代码或材料变化后旧证据失效。

- 使用入口：[开始.md](开始.md)
- 日常流程和命令：[MANUAL.md](MANUAL.md)
- 安装、升级、恢复：[docs/runtime.md](docs/runtime.md)
- 配置、文件映射和状态：[docs/schema.md](docs/schema.md)
- 小修复与复杂需求：[docs/fit.md](docs/fit.md)
- 权限与资料依据：[docs/trust.md](docs/trust.md)
- 分层测试：[docs/testing.md](docs/testing.md)
- 本轮取舍与限制：[docs/decisions-0.2.md](docs/decisions-0.2.md)
- 已实现与后续验证：[PLAN.md](PLAN.md)

运行需要 Python 3.10+、Git 和 requirements.txt。PowerShell/shell 入口共用一个核心，首次安装依赖见运行文档。
套件不保存密码、不代建业务代码仓、不自动提交或部署；不要求每条任务都运行浏览器全链路 E2E。
