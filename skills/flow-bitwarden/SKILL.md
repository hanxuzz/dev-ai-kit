---
name: flow-bitwarden
description: >-
  用 Bitwarden 存放和读取密码、连接串。用户提到密码、密钥、数据库账号，或要配置 runtime 时使用。
---

# Bitwarden

密码的存放处是用户本机已经接好的 Bitwarden MCP（`@bitwarden/mcp-server`）。没有这项 MCP 时，停下来，让用户按套件 `docs/secrets.md` 配好后重开 Cursor。不要改用别的文件里的明文，也不要让用户把主密码发到聊天里。

## 取已有条目

1. 调用 Bitwarden 的 `status`。状态是锁定时，只调用 `unlock`，等系统密码框。不要在对话里索要主密码。
2. 文件夹用 `project.yaml` 的 `secrets.bitwarden_folder`。为空就问用户文件夹名，写入该字段，不要写口令。
3. 用 `list` 按文件夹找条目。条目名是 `{环境} · {用途}`。
4. 需要内容时再 `get`。只在当前任务里使用。
5. 用完不要把口令写入需求文档、`project.yaml`、`project.local.yaml`、日志或提交说明。`project.yaml` 里只保留条目名，例如 `runtime.database.bitwarden`。

## 用户要存新密码

1. 仍先 `status` / `unlock`。
2. 用 `create_item` 写到 `secrets.bitwarden_folder`。没有文件夹就先说明需要在 Bitwarden 里建好这个文件夹。
3. 告诉用户文件夹和条目名。口令不要再复述进仓库文件。

## 和测试的关系

`runtime.database.readonly` 不是 `true` 时，不要用取出的数据库口令去连接。是 `true` 时，也只做读取，用来核对数据或准备用例。不要用 Vault 里的口令去 SSH、部署或改远程系统。
