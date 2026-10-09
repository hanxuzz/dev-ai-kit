# 配置与状态协议 v2

YAML 使用安全解析器，拒绝重复键；不使用字符串真假值。`true/false` 是布尔值。
可提交配置只使用相对路径，分隔符 `/`；禁止 `..` 越界和逃逸符号链接。本机路径只在 `project.local.yaml`。

## 项目配置

完整格式见 `templates/project.yaml`。`repos` 支持目录字符串，或 `{path: ui}`。单仓可以 `{app: .}`。
分支 `mode` 为 project/current/feature；策略与自动操作权限分离，见 [conventions.md](conventions.md)。

```yaml
runtime:
  checks:
    ui-unit:
      repo: frontend
      argv: [npm, run, test, --, --run]
      cwd: .
      timeout_seconds: 120
      requires: []
    api-integration:
      repo: backend
      argv: [python, -m, unittest, discover, -s, tests/integration]
      cwd: .
      timeout_seconds: 300
      requires: [database, 'service:api']
  database:
    readonly: false
    bitwarden: ''
  services:
    api:
      description: 使用项目已有启动方式，由用户授权启动并确认健康
```

`argv` 不经过隐式 shell。确需 shell 语法时明确配置 `sh -c` 或 `powershell -Command`，审核完整命令。
服务配置用于说明前置，核心不自动启动后台服务，也不代连数据库。`run --ready database --ready service:api` 只能在用户授权且实际验证前置后传入。
`readonly: true` 是要求，不是权限证明；应使用真正没有写权限的账号。

## 一条需求

`status.yaml` 由 `adopt` 创建，不手工伪造 approval/tasks/history。主要字段：

| 字段 | 含义 |
|------|------|
| schema_version | 固定 2 |
| revision | 每次状态修改递增，调用者使用 --expect 做并发检查 |
| scope_revision | 范围变更/重新确认的代次，证据适用性见下文 0.3 规则 |
| profile | quick、standard、cross-system |
| files | requirement/impact/plan/testcases → 既有文件名，空值才回退到默认名 |
| sources | 来源编号 → 类型、收集状态、版本、相对快照路径或链接 |
| approval | 实际确认人、说明、时间、当前材料摘要 |
| tasks | TASK 编号 → pending/doing/done，机器维护 |
| blocker | 当前阻塞原因；清除后保留历史 |
| handoff | 当前未验证修改、环境情况、下一动作的人类说明 |

```yaml
sources:
  S1:
    type: text
    status: collected
    version: 工单第2版
    summary: 用户确认的范围
  S2:
    type: recording
    status: skipped
    required: false
    reason: 本需求没有会议录像
  S3:
    type: design
    status: collected
    url: '<已授权设计链接>'
    version: '本次读取的版本或更新时间'
    path: sources/design.png
```

来源 `path` 相对需求目录；已有二进制不搬移，外部路径不方便快照时记录链接、版本和摘要。可变远端材料是否更新需要 Agent 再读取确认，脚本不会自动联网监控。

## 结构化定义与文档

- `requirements.yaml`：`requirements` 列表，每项有 `id/title/sources/acceptance`；`out_of_scope` 必须明确。
- `tasks.yaml`：任务 `id/title/repo/requirements/depends_on/files/checks`；无自动检查时填 `manual_acceptance`。每条范围内需求都必须有任务承接。
- `cases.yaml`：用例 `id/requirements/repo/kind/expected`；auto 还需 `check`。每条需求必须覆盖。
- Markdown 保存原文、业务解释、分析及方案；YAML 是机器可检查的映射，不能靠文件存在推断完成。
- cross-system 还要求 requirements.yaml 的 `assessments` 填写 interfaces/data/permissions/failure_modes/async_cache/delivery_order/rollback；不适用写理由。
- quick 可将三个文档角色映射到同一 `brief.md`，仍保留需求、任务和用例的最小映射。脚本校验结构，语义正确性仍需阅读代码和人工确认。

## 材料更新接口

Agent 将拟更新内容放入一个临时 YAML，再调用：

```text
kit prepare --workspace <工作区> --expect <revision> --input <更新包.yaml>
```

更新包格式：

```yaml
state:
  files:
    requirement: Existing-Spec.md
  sources:
    S1: {type: text, status: collected, version: '1', summary: 已确认的工单内容}
artifacts:
  03-questions.md: |
    # 问题
    Q1：待确认事项。
  requirements.yaml:
    requirements: []
    out_of_scope: [明确排除的内容]
```

这是结构示例，空 requirements 不满足就绪条件。`state` 中的映射整体替换，调用前读旧值并保留无关项。
允许更新的状态字段：title/profile/files/sources/questions/blocker/handoff。不能用 prepare 写审批、证据或完成记录。
问题 open 时禁止更新最终规格和任务；先记录需求方答复，已全部澄清才将 questions 改成 confirmed。

## 验证证据

自动证据在 `.kit/evidence/`：代码内容指纹、HEAD、材料代次、检查配置摘要、退出码、时间、超时标记、输出字节数和摘要。默认不保留原始输出，避免命令意外打印凭证。
人工证据必须由真实执行者提供实际观察；Agent 不能替未执行的人填写通过。
同一检查只使用最新结果，代码或命令配置变化会使旧证据失效。检查执行期间改了代码也不能记为通过。
源码指纹基于 Git 跟踪及未忽略文件，排除套件元数据和文档根；需要影响验证的构建配置不要放在 Git 忽略列表里。

## 0.3 增量字段与失效规则

schema_version 仍为 2，旧状态无需重建。新增可选状态字段由核心维护：

- `evidence_epoch`：整体范围变化时增加，使此前全部验证失效。
- `pending_change`：差异、受影响及保留任务、建议重跑检查、候选指纹。确认必须匹配此指纹才能保留无关工作。
- `execution_authorization`：明确轻量请求的真实确认者、原话、范围指纹及任务；只用作恢复依据，不是身份认证或扩权机制。
- `approval.snapshot`：确认时结构化材料快照；`editorial_note` 记录经审阅的文字纠错理由。
- 证据 `subject_fingerprint`：关联需求、任务依赖、用例、来源与全局约束的摘要。局部变更仅使关联证据失效；旧版无此字段的证据仍使用整体材料摘要。
- 证据 `diagnostic`：失败分类、可识别的 unittest 用例名与下一步，不包含原始错误正文。

`assist change` 和 prepare 都按映射及任务传递依赖分析。来源、全局约束、未映射正文变化和过期旧确认采取整体复核。`editorial` 必须有 reason 且不改变结构化定义，由操作者核对自然语言含义；不能作为自动语义等价证明。正文伴随结构化变化时，操作者还须确认两者范围一致。

`runtime.checks.<name>.inputs` 可选，为相对仓库的非空 glob 列表，使用大小写敏感 fnmatch 匹配（`*` 可匹配路径分隔符，不是 Git pathspec）。默认省略，覆盖全部未忽略代码。仅在已核实完整依赖后收窄，包含被测代码、测试、共享代码、构建配置和依赖锁文件；配置不完整可能漏报过期验证。

内容不变的 Git commit 不要求重新验证；命令配置变化仍失效。检查运行时仍监测整个仓库，写入输入集外代码也不会获得通过证据。`scope_revision` 只标记范围代次，0.3 的局部验证适用性以 subject_fingerprint 和 evidence_epoch 为准。

prepare 写材料前使确认失效，写完再保存新摘要；一次命令可能递增 revision 多次，必须使用返回值，不自行加一。
