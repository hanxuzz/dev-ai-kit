# 运行、安装与升级

0.2 使用一个 Python 核心；PowerShell 和 shell 只传递参数，不再各自维护状态逻辑。
最低 Python 3.10，Git。依赖固定在根目录 `requirements.txt`，不在运行命令时偷偷安装。

## 准备运行时

在套件克隆目录执行一次：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Windows：

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

下文 `kit` 代表 `sh <套件>/scripts/kit.sh`，或 Windows 的 `& <套件>/scripts/kit.ps1`。
入口优先使用套件 `.venv`，可用 `DEV_AI_KIT_PYTHON` 指定已准备好的解释器。路径包含空格时按 shell 语法加引号。
兼容入口 `install/next/validate/check.ps1` 和 `.sh` 仍在；新操作统一使用 `kit`。

## 首次安装

```text
kit install --workspace <工作区>
kit install --workspace <工作区> --apply
kit validate --workspace <工作区> --config-only
```

用户已要求安装时，Agent 看过预览即可应用，不额外反复索要授权；有不明确的文档去处才问。
工作区可以是单仓，也可以包含多个代码仓。套件必须在业务工作区外。
默认发现独立 `docs` 仓时用 repo；工作区本身为 Git 仓时用 tracked；提供共享目录时可指定 share；其他情况用 local。

| 模式 | 约束 |
|------|------|
| local | 文档位于工作区，不能属于 Git 仓 |
| tracked | 文档属于工作区 Git 仓；不会加入忽略 |
| repo | 文档根本身是独立 Git 仓；使用 `--docs-repo` 指定名字 |
| share | 使用本机 `share.path`；共享目录必须已可访问，不创建冒牌离线目录 |

安装不覆盖项目配置和已有业务材料。空的背景模板只是待填写，不是已完成。

## 升级与回退

```text
kit upgrade --workspace <工作区>
kit upgrade --workspace <工作区> --apply
kit rollback --workspace <工作区> --backup <安装输出的备份号>
```

升级保留用户配置；仅自动替换与上次安装摘要一致的规则。修改过的规则保留，候选写入 `.dev-ai-kit/dev-ai-kit.mdc.proposed`，Agent 展示差异后按已授权范围合并。
每次变更前备份，写入失败自动恢复；回退会拒绝覆盖安装后再次修改过的文件。
旧版 `project.yaml` 可以读取，但执行前需要按 [schema.md](schema.md) 补 `runtime.checks` 和分支策略；不要把旧 shell 字符串猜成新命令。
旧需求用 `adopt` 预览并迁移，备份原状态，不继承未经核验的确认和完成。

## 校验与恢复

- `validate --config-only`：只检查安装，适合还没有需求时。
- `validate`：当前需求的基础结构；别的需求受阻不连带阻断。
- `validate --ready`：检查开工所需材料、覆盖关系和依赖。
- `validate --all`：显式检查全部需求，适合项目整理。
- `adopt` 不先要求需求通过完整校验，避免“先有状态才能补状态”的循环。

状态操作需要 `--expect <revision>`。本机工作区和共享需求目录均使用排他锁；冲突后重新读取，不自动覆盖、不自动抢锁。
锁遗留时先确认执行进程已结束，再由维护者删除对应 `.dev-ai-kit.lock`。OneDrive 等异步同步盘不能提供跨离线设备的强一致性；同一需求同一时间只允许一位写入者。

`prepare` 先使确认失效，再写材料；中断后是未确认草稿，已存在材料的备份在该需求 `.kit/edits/`。重新检查备份和现有内容，再提交一次更新，不自动重跑业务命令。

需要将旧配置结构写成 v2 时，先预览 `upgrade --migrate-config`，再加 `--apply`。它保留旧字段，新增 checks 和独立分支策略，并清除旧规范确认；不自动把旧命令字符串转成可执行 argv。迁移同样有备份可回退。YAML 重写会规范化格式并丢失注释，原文保存在备份里。

## 0.3 日常入口与诊断

日常由 Agent 使用 assist begin/resume/change/review，参数细节在 [命令参考](cli-reference.md)。升级到 0.3 后保留 schema v2、旧命令及旧证据兼容；升级安装规则后才能让已有项目获得新的意图路由。

检查默认仅记录分类诊断。显式 `run --diagnostic-log` 写入工作区忽略目录 `.dev-ai-kit/diagnostics/`，不会同步进需求证据。仅保留输出尾部并尽力脱敏，人工检查后再分享；不再需要时可删除该目录中的日志，不影响验证记录。
