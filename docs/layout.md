# 目录与状态

配置和字段见 [schema.md](schema.md)，运行命令见 [runtime.md](runtime.md)。

```text
工作区/
  project.yaml                  # 团队配置
  project.local.yaml            # 本机路径、当前需求，不提交
  .cursor/rules/dev-ai-kit.mdc  # 常驻路由
  .dev-ai-kit/                 # 安装清单、备份和升级候选，不提交
  <代码目录>/
文档根/
  team/                        # 背景、规范、术语和决定
  requirements/<需求号>/       # 目录名可使用已有 requirement
    status.yaml                # 状态、历史、确认、交接
    requirements.yaml          # R 编号、来源、验收、不做事项
    tasks.yaml                 # TASK 编号、依赖、代码范围和验证
    cases.yaml                 # T 编号、R 映射、自动或人工验收
    <原有规格和计划>.md         # files 映射，不要求改名
    .kit/evidence/             # 脱敏验证元数据
    .kit/edits/                # 材料修改前备份
```

新建/接管只创建状态，不预建后续空文件。无录像、无外部资料可持久化 skipped。
quick 用一份 brief；standard 用规格、影响和计划；cross-system 额外评估接口、数据、权限及交付回退。

`stage` 是持久阶段：intake/meeting/sources/questions/requirement/impact/plan/build/test/done。
`next` 的 `phase` 是当前动作：select/adopt/prepare/questions/blocked/confirm/conventions/build/test/accept/done。
例如 stage=done 但代码已改变，phase=test 会要求重新验证；不会继续宣称证据有效。

任务状态只由 start/finish/change/prepare 等命令维护。只有通过当前版本验证的任务才能 finish；所有任务、用例通过后，经用户验收 complete。

共享目录可保存允许共享的原件和问题清单；默认不自动复制敏感材料。索引只记录来源，不递归扫描共享盘。
