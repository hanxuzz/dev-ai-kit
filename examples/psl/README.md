# 安装完成后的工作区（示例）

`psl/` 本身可以不是 git 仓库。前后端各自有远程。套件不放在里面。

```text
psl/
  skill.md                     # 由 bootstrap/SKILL.md 复制，只用于安装一次
  project.yaml
  project.local.yaml           # 不提交
  .cursor/rules/dev-ai-kit.mdc
  frontend/                    # 业务仓库
  backend/                     # 业务仓库
  docs/                        # 仅 docs.mode=local 时出现，不提交
```

`docs.mode=repo` 时，`team/` 和 `requirements/` 在名为 `docs` 的文档库里，或在 `-DocsRepo` 指定的那个库里。`docs.mode=share` 时，它们在 OneDrive 共享目录的 `docs/` 下。原件在共享目录的 `requirements/<需求号>/`。
