# 分支和提交规范

套件自带一套常见做法，安装时先对照这个项目里仓库的现状，由同事决定打开或关掉。`project.yaml` 里 `conventions.confirmed` 写成 `true` 之前，这些只是建议，不会自动建分支，也不会改代码。

代码仓自己的 `.cursor/rules` 里已有提交或分支规则时，以那个仓库为准，并在确认时说明套件的对应开关不覆盖它。

## 默认建议

| 开关 | 建议 | 含义 |
|------|------|------|
| `branch.enabled` | 打开 | 一条需求一个分支。计划写好后、改代码前，在要动的那个仓库上建立或切换 |
| `branch.base` | 留空，确认时填 | 从哪条分支拉出。填这个仓库实际在用的开发主干，不要猜 |
| `branch.pattern` | `feature/{id}` | `{id}` 换成需求号。分支名里不用空格 |
| `commit.only_when_asked` | 打开 | 没有明确说提交，就不提交 |
| `commit.allow_on_base` | 关掉 | 不在主干上提交。要改主干必须在当次对话里点名 |
| `push.only_when_asked` | 打开 | 没有明确说推送，就不推送 |
| `trailer.coauthor` | 关掉 | 提交说明里不写 `Co-authored-by` |

不提供「允许 force push」。即使用户关掉别的开关，也不要 force push，不要改 git config，不要跳过钩子。

## 确认时看什么

对 `project.yaml` 里每个代码目录执行：

- 当前分支
- 远程默认分支（有 `origin/HEAD` 就用它）
- 是否已有 `.cursor/rules` 里的 git 规则

把看到的结果讲给用户，再问每一项开还是关。用户确认后：

- 前后端主干名字不一样时，关掉 `branch.enabled`，改代码时按各仓库自己的规则。名字一样才把 `branch.base` 写成那一个主干名。
- `conventions.confirmed` 写成 `true`

还没确认时，下一步只做这件事，不新建需求、不改代码。
