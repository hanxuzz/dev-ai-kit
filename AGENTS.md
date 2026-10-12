# dev-ai-kit Agent 约定

## 在本套件仓库开发时

这里是流程套件源码，不是已安装的业务工作区。先读 README.md、docs/schema.md 和 docs/testing.md；不要求本仓有 project.yaml，不运行业务安装门禁。
修改核心后运行 `python -m unittest discover -s tests -v`；解释性文档和技能必须与命令行为一致。
不要把任何同事的机器目录写入可提交文件。本机路径仅放业务工作区不提交的 project.local.yaml。

## 在已安装的业务工作区使用时

先读 project.yaml、project.local.yaml 和 kit.path 指向的 docs/runtime.md、docs/trust.md。
状态/文件约定以 docs/schema.md 为准；每个技能的 `kit` 指该套件的 scripts/kit.sh 或 scripts/kit.ps1。
找不到安装配置时先确认工作区，按 bootstrap/SKILL.md 安装，不复制 skill.md。

- 查看进度只读 next/status，不构成执行授权。
- 登记/接管用 adopt，可在缺 status 时恢复，不先要求就绪校验。
- 开发前检查当前版本确认、任务依赖、团队规范和分支。questions=open 或 blocker 未解决不修改对应业务范围。
- 需求范围、不做事项、验收必须能追溯到原件和 R/TASK/T 映射。视觉还原看设计，普通文字改动允许已确认文字来源。
- 明确要求浏览器操作测试时，按 docs/test-automation.md 调用适用技能并实际打开可见浏览器操作页面；其他层次测试不能替代，缺能力必须说明。
- 测试发现 Bug 先暂停推进，按 docs/test-automation.md 修复与续测协议遵循全部开发规则修复，本地重启就绪后复测和回归，再继续测试；不得跳过失败或沿用旧证据。
- 完成依赖实际证据；旧版本结果不能当本次通过。任务做完不会自动提交、推送或部署。
- 单步授权做完就停，连续执行仅在明确授权的范围内推进。
- 每轮结束必须按 docs/progress-feedback.md 主动反馈本轮结果、当前阶段与任务/有效验证进度、停点原因、下一步和责任方；不等用户追问。历史完成不等于本轮成果，任务完成不等于已验收、提交或发布。完整看板按需展示。

## 技能路由

套件只提供通用流程和规范；项目事实必须通过 flow-project-context 主动收集、核实并应用，不能将模板示例当项目默认配置。
开发请求先经 flow-entry 将开始、继续、变更、检查交付映射为操作；不要让用户选技能或填写状态。明确请求已包含范围与执行授权时记录原始依据，不重复询问。
登记与接管→flow-intake；来源→flow-meeting/flow-sources；范围与影响→flow-impact；任务→flow-plan；实施→flow-implement；代码实施前必须有需求行为、实际参考实现、复用/影响与回归依据；完成前必须用 flow-code-review 审查真实差异，不能只凭测试通过。
验证→flow-test；生成/导入任意格式测试原件及本地/dev 自动化→flow-testing；进度→flow-next；变更→flow-change；交接→flow-handoff；规范→flow-conventions；提交→flow-git；凭证→flow-bitwarden。
只解释代码或回答问题时直接处理，不强迫创建需求。

## 凭证和外部操作

凭证只用已授权的本机工具，文件仅记 Bitwarden 条目名。套件不代为登录、部署或改外部数据。
缺少录像、浏览器或数据库能力只阻挡依赖它的步骤；不能因此伪造资料、验证或确认。
