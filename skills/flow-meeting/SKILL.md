---
name: flow-meeting
description: >-
  用本机 asr-watch 解析需求会录像，写成 01-meeting.md。用户说解析录屏、识别需求、整理会议时使用。
---

# 解析录屏

按 `docs/runtime.md` 做开始检查。`validate.ps1` 失败就停止。再读 `docs/dependencies.md` 和本机 `asr-watch` 技能，过程目录以那个技能为准。

## 检查

1. `current` 指向的需求目录要存在，且其中有 `status.yaml`。没有则先按 `flow-intake` 建，不要在文档根外写纪要。
2. 录像路径来自用户，或来自共享目录 `index.md` 里这条需求的登记。索引没有就停，请用户把路径补进 `index.md`。不要搜索整个 OneDrive。
3. 索引有路径但文件本地不存在：把 `blocker` 写成「录像未同步：<路径>」，停止。不要写 `01-meeting.md`。
4. 本机要有 `asr-watch` 命令和 `ffmpeg`。缺则按 `docs/dependencies.md` 告诉用户，把缺什么写入 `blocker`，停止。

## 执行

1. 对整段录像只运行一次 `asr-watch`。不要为了分类再转写一遍。
2. 过程文件必须留在 `%USERPROFILE%\.local\share\asr-funasr\runs\<视频名>\`。按 `asr-watch` 技能确定 `<视频名>`。该目录里没有非空的 `transcript.txt`，或命令退出码不是 0：把 `blocker` 写成失败原因，不要根据记忆写会议结论。
3. 读 `transcript.txt` 的开头判断类型：需求澄清、方案评审、设计走查、验收演示、缺陷复盘。再读全文填写模板。设计走查记下页面；缺陷复盘记下复现步骤。用 `team/glossary.md` 纠正术语。对不上的句子放进「低置信度原话」，保留时间戳。已定和未定按 `docs/practices.md` 每条一个 `M` 编号；一句话里有两件事就拆开；不能判断做对没有的，放进未定。
4. 从模板复制出 `01-meeting.md` 再填。写完把 `blocker` 清空，`stage` 改为 `meeting`。
5. 再跑 `validate.ps1`。失败则不要把 `stage` 留在 `meeting`，把 `FAIL` 告诉用户。
6. 告诉用户过程目录、`01-meeting.md` 的路径，以及过程文件不要提交。

没有用户确认时，不要据此改业务代码。
