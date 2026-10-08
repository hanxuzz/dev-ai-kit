# 分支和提交规范

项目里已经有规范时，先收集，再照着做。收集结果写在文档根的 `team/conventions.md`，原文仍在各仓库的 `AGENTS.md` 和 `.cursor/rules/`。套件不改那些文件。

`project.yaml` 里 `conventions.confirmed` 写成 `true` 之前，不要建分支，也不要改业务代码。确认之后，分支和提交以 `team/conventions.md` 为准。套件下表只用于项目没写到的事项。

## 项目没写时的默认

| 开关 | 建议 | 含义 |
|------|------|------|
| `branch.enabled` | 关掉 | 套件不建分支、不切分支 |
| `branch.base` | 留空 | 只有用户明确要求套件建分支时才填。远程默认分支显示 `main`，不等于开发从 `main` 拉 |
| `branch.pattern` | `feature/{id}` | 只有打开自动建分支时才用 |
| `commit.only_when_asked` | 打开 | 没有明确说提交，就不提交 |
| `commit.allow_on_base` | 关掉 | 不在主干上提交。要改主干必须在当次对话里点名 |
| `push.only_when_asked` | 打开 | 没有明确说推送，就不推送 |
| `trailer.coauthor` | 关掉 | 提交说明里不写 `Co-authored-by` |

不提供「允许 force push」。即使用户关掉别的开关，也不要 force push，不要改 git config，不要跳过钩子。

## 收集时看什么

对 `project.yaml` 里每个代码目录，以及工作区根：

- `AGENTS.md`、`CONTRIBUTING.md`、`README.md` 里的分支和提交章节
- `.cursor/rules/` 里的规则
- 当前分支，以及远程默认分支（只作参考，不拿来当开发主干）

用户确认后：

- 已经收集到分支做法时，`branch.enabled` 保持 `false`。例如从 `prod` 开 `feature/NBPEM-xxx`，再 cherry-pick，并且不代 push。
- 用户补充的新规矩写进 `team/conventions.md`，不改仓库原文。和原文冲突时，两份都留着，并注明以用户这次说的为准。
- `confirmed: true` 只表示这份收集和补充已经确认。套件按 `team/conventions.md` 执行，不另建分支。

安装之后由 Agent 在当轮收集，并用确认清单逐项问用户。不要把「请去收集规范」交给用户复述。还没确认时，不要建分支，不要改业务代码，也不要开始下一条需求。
