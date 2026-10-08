---
name: flow-sources
description: >-
  把 Figma、Confluence、网址、PPT、PDF 收成 02-sources.md，原件留在共享目录。
  用户说收资料、保存 Figma、整理 Confluence 或 PDF 时使用。
---

# 收集资料

按 `docs/runtime.md` 做开始检查。目标是当前需求的 `02-sources.md`。文件不存在就从模板复制后再追加，不要改掉已有行。

## 原件

PPT、PDF、图片只放到 `<共享目录>/requirements/<需求号>/`。`share.path` 为空：不要把二进制拷进代码仓。在 `02-sources.md` 记录用户给出的路径，并说明要先填写 `share.path`。复制失败或路径不存在时写入 `blocker`，状态标「未收集」，停止。

## 摘录

- 链接打不开、Figma MCP 不可用、Confluence 没有权限：状态写「未收集」，摘录留空，对话里说明缺什么。不要编造正文。
- 能读到正文：每条一个 `S` 编号，摘录规则、范围、约束、界面状态和文案。不要把整页原文贴进文件。和会议某条 `M` 矛盾时，写上两边的编号。
- 和 `01-meeting.md` 矛盾的句子，追加到 `03-questions.md`（没有就从模板创建），`questions` 改为 `open`，`stage` 改为 `questions`。不要创建 `04`、`05`、`06`。

没有新的冲突、且 `questions` 不是 `open` 时，把 `stage` 改为 `sources`。然后跑 `validate.ps1`，失败就把 `stage` 改回原来的值并告诉用户。
