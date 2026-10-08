# 依赖技能

这些能力已经在用。本套件只检查它们在不在，并按它们的用法调用。不要把源码复制进 `dev-ai-kit`。

## asr-watch

解析需求会录像时用。口播转写加抽帧。过程文件不进文档根。

| 项 | 位置 |
|----|------|
| 技能 | `%USERPROFILE%\.cursor\skills\asr-watch\SKILL.md` |
| Windows 命令 | `asr-watch.cmd <视频路径>` |
| 过程目录 | `%USERPROFILE%\.local\share\asr-funasr\runs\<视频名>\` |

没有命令或没有技能文件时：停止录屏技能，把上表告诉用户，请用户按本机已有的 ASR 安装说明装好后再说「继续解析」。不要改用云端转写，也不要在文档根里临时写一份转写脚本。

抽帧需要本机有 `ffmpeg`，并且 `ffmpeg` 在 PATH 里。

## agent-browser

执行要操作页面的用例时用。走已经登录的 Chrome，不使用 Cursor 自带浏览器去点需要登录的环境。

| 项 | 位置 |
|----|------|
| 技能 | `%USERPROFILE%\.cursor\skills\agent-browser\SKILL.md` |
| 源码与扩展说明 | `%USERPROFILE%\.cursor\aifred-agent-browser\` |
| MCP | 用户级 `mcp.json` 里的 `playwright` 与 `fubo-browser-presence` |

第一次使用需要安装 Chrome 扩展（占用条 / Bridge）。扩展不放进本套件仓库。检查失败时，打开上面的源码目录，按其中的说明安装，然后新开一条对话再执行用例。

## Figma 与 Confluence

收资料时：

- Figma 链接用当前 Cursor 已启用的 Figma MCP。未登录或没有 MCP 时，在 `02-sources.md` 记下链接，标成未收集，并告诉用户要启用 Figma MCP。
- Confluence 优先用用户已配置的方式打开（已登录浏览器或 API）。打不开则同样标成未收集，不要编造正文。

令牌和 cookie 不写进套件、不写进需求文档。

## Bitwarden

密码和连接串用本机已有的 Bitwarden MCP，用法见 `docs/secrets.md` 和 `skills/flow-bitwarden/SKILL.md`。套件不保存会话，也不复制 `mcp.json`。

## 本套件不附带的东西

- FunASR 模型权重
- Chrome 扩展安装包
- 某个项目的 VPN、证书、数据库口令
