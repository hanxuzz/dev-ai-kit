# 一条纯文字需求的本地演练

目的：演示已有 Spec、没有录像、无外部服务时的最小流程。不要将示例结果当作真实业务验证。

1. 创建临时工作区，下面有名为 `app` 的 Git 代码目录，包含 `app.py`。套件留在外部。
2. 按运行文档安装，将 repos 配成 `{app: app}`；确认示例允许当前分支后设 conventions.confirmed=true、branch.mode=current。
3. runtime.checks 配置 `unit: {repo: app, argv: [python, -m, unittest, discover, -s, tests], cwd: ., timeout_seconds: 30, requires: []}`。实际使用可用 Python 解释器命令名，但不要提交机器绝对路径。
4. adopt --id REQ-demo --apply，然后 prepare --input 指向本目录 bundle.yaml。
5. validate --ready，实际确认示例范围后 confirm；start TASK-1。
6. 完成 app.py 以及 tests/test_app.py，run unit，finish TASK-1。用户实际验收后 complete。

`tests/test_workflow.py` 自动使用临时目录覆盖这个旅程及失败分支，不需要手工建真实业务项目。
