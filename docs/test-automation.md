# 自动化测试接入

开发者说“根据需求补测试”或“导入测试人员的文件，在本地/dev 执行”，Agent 应进入 flow-testing，主动解析原件、规范化、选择执行层次并运行验证。用户不必先转换文件。

执行前先按 [项目上下文协议](project-context.md) 发现真实启动方式、测试框架、报告和环境，以下示例不是默认项目配置。

## 任意格式原件与统一格式

任意格式是 Agent 的接入责任，不代表 Python 核心内置全部解析器。Agent 使用当前可用的文档、表格、PDF、OCR 等能力，遇到无法读取内容必须报告缺口。原件不覆盖；从每个原件生成规范化 YAML，逐条保留 source_location。多个原件分别导入。

```yaml
cases:
  - id: QA-ORDER-001
    external_id: TC-001
    title: 订单列表仅显示所选状态
    requirements: [R1]
    repo: frontend
    source_location: QA.xlsx / 订单 / 第 5 行
    preconditions: 测试账号可访问订单列表
    test_data: 独立测试租户，已有两种状态的订单
    steps:
      - 打开订单列表
      - 选择已完成状态
      - 检查列表中每条记录的状态
    expected: 只显示已完成订单，无结果时显示空态
    kind: auto
    check: order-api-local
    test_name: orders::filters_completed
```

必需字段：id/title/requirements/repo/steps/expected/kind。转换任意原件时 source_location 必需。前置与数据不适用可写明，不编造。测试数据使用合成数据或变量引用，原件中的凭证及客户隐私不能复制进共享用例。`external_id` 保留原始编号；合并多文件发生 id 冲突时使用命名空间。manual 无需 check/test_name；auto 必须关联同仓库 report: junit 的实际检查与精确 classname::name。

导入会记录原件及规范化文件摘要、来源 qa/ai、实际审阅者。只有 `--reviewed-by` 才标记 reviewed，否则 draft。审阅是实际业务/测试判断，参数不是身份认证。原件数量、导入数量、重复和解析失败由 Agent 对账；核心不证明原件被完整解析。

## Agent 命令

```text
kit cases draft --workspace <工作区> --repo frontend
kit cases import --workspace <工作区> --input <规范化.yaml> --original <原件任意格式> --source qa
kit cases import --workspace <工作区> --input <规范化.yaml> --original <原件> --source qa --reviewed-by <实际审阅者> --expect <最新revision> --apply
```

draft 只返回验收种子，不保存、不运行；Agent 必须细化可执行步骤与场景。导入默认预览；已有 id 必须显式 --replace，未涉及用例保留。导入按既有变更流程使对应确认失效，核对新增验收后使用真实依据 confirm。CSV/YAML 是核心支持的交换格式，不是对用户上传文件的限制。

## 本地与 dev 环境

项目配置示例（名称、路径、命令由 Agent 按实际项目调整）：

```yaml
runtime:
  environments:
    local:
      kind: local
      base_url: http://127.0.0.1:3000
    dev:
      kind: dev
      base_url: https://dev.example.test
      deployment_id: verified-build-123
      required_env: [TEST_API_TOKEN]
  checks:
    order-api-local:
      repo: frontend
      argv: [npm, run, test:api]
      environment: local
      report: junit
      timeout_seconds: 180
      requires: []
    order-api-dev:
      repo: frontend
      argv: [npm, run, test:api]
      environment: dev
      report: junit
      timeout_seconds: 180
      requires: []
```

每个检查固定一个环境，避免运行时静默切目标。同一业务用例需要两环境验收时，分别建立稳定用例 id、check，保留相同 external_id。dev 检查用于部署验收用例，不能配置在本地实施任务的 checks 中替代本地验证。

运行时注入 KIT_BASE_URL、KIT_ENVIRONMENT、KIT_ENVIRONMENT_KIND、KIT_JUNIT_PATH；账号只通过现有进程环境传入，配置仅写变量名。脚本必须实际读取这些值；套件无法限制任意子进程忽略配置或访问其他地址。审核测试脚本与目标是 Agent 的责任。

本地服务由项目测试框架管理生命周期。Playwright 示例见 [配置模板](../examples/testing/playwright.config.ts)，利用 [webServer](https://playwright.dev/docs/test-webserver) 启动并等待服务；已有服务须确认身份，不能仅因端口开放就复用。dev 不执行本地启动命令。API 用例可以使用 [request fixture](https://playwright.dev/docs/api-testing)，不必启动浏览器。其他项目复用 pytest/JUnit 等框架，不强制换技术栈。

```text
kit run --workspace <工作区> --check order-api-local --expect <最新revision>
kit run --workspace <工作区> --check order-api-dev --ready environment:dev --expect <最新revision>
```

dev readiness 是实际核实目标、部署版本、访问权限与数据边界后由 Agent 记录的事实；不能把配置的 deployment_id 当自动探测结果。远端重新部署后需更新版本并重跑。当前不自动部署、登录、启动 VPN 或清理远端数据。

## 逐条结果与证据

测试框架必须在 KIT_JUNIT_PATH 写入本次新 UTF-8 JUnit XML，套件每次分配唯一临时路径。配置方式参考 [Playwright reporters](https://playwright.dev/docs/test-reporters)。只匹配精确 classname::name；首次接入检查真实报告命名，不猜测。

零测试、报告缺失/无效、失败、映射缺失、跳过或重复名称都不能产生整项通过证据。整项报告中的跳过或重复名称即使没有用例映射，也不能让任务级检查通过。重复名字（包括重试或多个浏览器）需要拆分检查或唯一命名，不选择最后一次成功掩盖失败。任一测试 failure/error 使该检查失败，即使命令退出码为零。

证据仅保留映射结果、数量、报告摘要、代码及环境摘要和部署版本，解析后删除临时原始 XML。截图、trace、测试框架自行生成的文件仍由项目配置忽略并管理；不得把原始响应、密码或截图内容复制进共享证据。命令原始输出默认不落盘。

旧版没有 JUnit 映射的检查仍按命令级验证兼容；新导入的自动化用例强制使用逐条报告，不能声称旧检查已有逐条覆盖。
