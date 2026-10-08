# 密钥放 Bitwarden

密码、API Key、连接串放在 Bitwarden。套件和业务仓库里只写文件夹名和条目名。

本机如果已经在 Cursor 里接过 Bitwarden MCP，就不用再装一套。套件只约定怎么用，不保存登录会话。

## 第一次

1. 安装 [Bitwarden](https://bitwarden.com) 客户端，并安装官方命令行（可选，MCP 会用到）：

```powershell
npm install -g @bitwarden/cli
```

2. 在用户目录的 Cursor 配置里启用官方 MCP。文件是 `%USERPROFILE%\.cursor\mcp.json`，不要提交这个文件。其中 Bitwarden 一段应类似：

```json
{
  "mcpServers": {
    "bitwarden": {
      "command": "npx",
      "args": ["-y", "@bitwarden/mcp-server"]
    }
  }
}
```

3. 改完后重开 Cursor。在 Settings → Tools & MCP 里确认 `bitwarden` 已连接。
4. 在对话里说：`用 Bitwarden 看一下锁没锁。` 锁着时会弹出系统密码框。主密码不要发到聊天里。

## 条目怎么命名

在 `project.yaml` 里写文件夹名，例如 `个人/psl` 或 `工作/psl`。

条目名用 `{环境} · {用途}`，例如 `DEV · MySQL 只读`。这个名字写到 `runtime.database.bitwarden`。自定义字段里可以放主机、端口、库名。密码放在登录项的密码栏。

## 不要做的事

- 不要把口令、`BW_SESSION`、主密码写进 git、`project.yaml`、需求文档或共享目录。
- 不要把 `mcp.json` 复制进套件仓库。
- 数据库账号要能写数据时，不要配进 `runtime.database.bitwarden`。那里只放没有写权限的账号。
