---
name: flow-bitwarden
description: 在用户明确授权的凭证任务中使用已配置的 Bitwarden 能力，只保存条目指针，不保存凭证正文。
---

# 凭证操作

先读 docs/secrets.md，核对当前环境实际提供的工具 schema，不假设固定的 status/unlock/get 方法或包名。
只访问本次任务相关条目。缺少连接、权限或解锁时说明缺什么；不索要主密码到聊天，不用其他明文文件绕过限制。

项目配置只留 secrets.bitwarden_folder 和 runtime.database.bitwarden 等指针，不写令牌、口令或会话。
用户明确要求新建条目时，按实际工具完成；不将条目正文重复输出或写入日志。
取到凭证不等于获得登录、部署或修改远端系统的授权。数据库验证还需实际只读权限及本轮连接授权。
