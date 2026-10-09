"""Actionable failure classification; raw output is never persisted by default."""
import re


def summarize(output, code, timed_out=False, changed=False):
    tests = sorted(set(re.findall(r'^(?:FAIL|ERROR): (test_[A-Za-z0-9_]+)', output, re.M)))[:20]
    if timed_out:
        category, message, action = 'timeout', '检查超时，已终止进程', '先检查服务是否就绪或测试是否卡住；确认原因后再调整超时'
    elif changed:
        category, message, action = 'code-changed', '执行检查期间代码发生变化，本次不能作为通过证据', '检查生成文件是否应被忽略，或命令是否包含自动修复；稳定代码后重新验证'
    elif code == 0:
        category, message, action = 'passed', '本次命令通过', '继续当前任务或验收'
    elif 'ModuleNotFoundError' in output or 'command not found' in output or 'is not recognized' in output:
        category, message, action = 'missing-dependency', '命令或依赖不可用', '核对解释器、项目依赖和命令配置；不需要重新确认业务范围'
    elif 'AssertionError' in output or 'FAILED' in output:
        category, message, action = 'assertion', '存在失败的测试断言', '定位失败用例及本次修改，修复后重跑此检查；不要修改断言来绕过验收'
    elif 'PermissionError' in output or 'Permission denied' in output:
        category, message, action = 'permission', '运行环境拒绝访问', '核对本机文件权限或目标环境访问条件，不升级业务操作权限'
    else:
        category, message, action = 'command-failed', f'命令退出码为 {code}', '在本机查看受控诊断输出，判断环境故障还是代码问题后再重试'
    return {'category': category, 'message': message, 'failed_tests': tests, 'next_action': action}


def redact(text):
    text = re.sub(r'-----BEGIN [^-]*PRIVATE KEY-----[\s\S]*?-----END [^-]*PRIVATE KEY-----', '[REDACTED PRIVATE KEY]', text)
    text = re.sub(r'(?i)(bearer\s+)[^\s"\']+', r'\1[REDACTED]', text)
    text = re.sub(r'(?i)((?:password|passwd|secret|token|api[_-]?key|authorization|cookie)[\"\']?\s*[:=]\s*)[^\s,;]+', r'\1[REDACTED]', text)
    text = re.sub(r'(https?://)[^\s/@]+:[^\s/@]+@', r'\1[REDACTED]@', text)
    text = re.sub(r'\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b', '[REDACTED JWT]', text)
    return text
