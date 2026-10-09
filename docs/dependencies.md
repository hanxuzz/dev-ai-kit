# 按需能力检查

核心仅 Python 3.10+、PyYAML（requirements.txt）和 Git。`kit check` 检查核心，不检查所有可选工具。

| 当前任务 | 检查 | 缺少时 |
|----------|------|--------|
| 解析录像 | check --capability recording | 只停止转写；可用用户提供文字或其他已确认材料继续 |
| 浏览器验收 | check --capability browser，加实际调用本会话工具验证 | 改为有明确步骤的人工验收，不伪造通过 |
| 读取 Figma | check --capability figma，加文件访问检查 | 记录待收集；视觉还原受阻，其他无关任务可继续 |
| 读取凭证 | 本会话已连接的 Bitwarden 工具 | 只停止依赖凭证的操作，不索要主密码 |

浏览器和 Figma 检查报告的是还需交互验证，不因存在某个目录就宣称登录或 MCP 可用。
转写优先复用 asr-watch，过程文件留在工具工作目录。套件不下载模型、扩展，不复制个人 mcp.json。
Figma、Confluence 和其他来源打不开时记录状态与原因，不生成看似完整的摘录。
