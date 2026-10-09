"""Developer-facing intent entrypoints; execution and confirmation remain explicit."""
import copy
import re
from .storage import KitError, read, inside, digest, atomic
from .workspace import load
from .workflow import (adopt, prepare, mutate, next_step, context, definitions, code_snapshot,
                       latest_evidence, fingerprint, approval_current, state_lock, persist)
from .changes import analyze
from .testing import environment


def recommend_profile(request, files, risks):
    if risks or re.search(r'迁移|权限|跨系统|接口契约|schema|migration', request, re.I):
        return 'cross-system', '涉及接口、数据、权限或显式风险'
    if files and len(files) <= 3 and re.search(r'文案|错别字|提示文字|提示语|typo|copy text|label', request, re.I):
        return 'quick', '少量明确文件的文字修复，无已知业务规则变化'
    return 'standard', '范围复杂度尚不足以确定为轻量修改'


def resume(workspace, req_id=None):
    flow = next_step(workspace, req_id)
    result = {'summary': flow.get('action'), 'phase': flow.get('phase'), 'mutates': False,
              'needs_decision': [], 'next_action': flow.get('action'), 'details': flow.get('details', [])}
    if flow.get('phase') in ('select', 'adopt'):
        result['requirements'] = flow.get('requirements', [])
        return result
    w, p, local, docs, d, s = context(workspace, req_id)
    result.update(id=s['id'], title=s.get('title'), revision=s.get('revision'), handoff=s.get('handoff', {}))
    tasks = definitions(d, 'tasks')
    result['completed'] = [t['title'] for t in tasks if s.get('tasks', {}).get(t['id'], {}).get('status') == 'done']
    result['in_progress'] = []
    for task in tasks:
        entry = s.get('tasks', {}).get(task['id'], {})
        if entry.get('status') == 'doing':
            current = code_snapshot(w, p, docs, task['repo'])
            result['in_progress'].append({'id': task['id'], 'title': task['title'], 'code_changed_since_start': current['tree'] != entry.get('code_before', {}).get('tree'), 'resume_without_restart': True})
    result['verification'] = []
    for check in sorted({c for t in tasks for c in t.get('checks', [])} | {c['check'] for c in definitions(d, 'cases') if c.get('kind') == 'auto' and c.get('check')}):
        e = latest_evidence(d, 'check', check)
        spec = p.get('runtime', {}).get('checks', {}).get(check)
        reason = 'not-run'
        if e and isinstance(spec, dict):
            if e.get('check_hash') != digest(spec):
                reason = 'command-changed'
            elif e.get('environment') != environment(p, spec)[0]:
                reason = 'environment-changed'
            elif e.get('code', {}).get('tree') != code_snapshot(w, p, docs, spec['repo'], spec.get('inputs'))['tree']:
                reason = 'code-changed'
            else:
                from .workflow import valid_evidence
                if e.get('result') != 'passed':
                    reason = 'failed'
                else:
                    reason = 'current' if valid_evidence(w, p, docs, d, s, 'check', check, spec['repo']) else 'scope-changed'
        result['verification'].append({'check': check, 'state': reason, 'diagnostic': e.get('diagnostic') if e else None,
                                       'next_action': '无需重跑' if reason == 'current' else f'诊断后运行检查 {check}' if reason == 'failed' else f'运行检查 {check}'})
    result['cases'] = []
    for case in definitions(d, 'cases'):
        e = latest_evidence(d, 'check', case.get('check')) if case.get('kind') == 'auto' else latest_evidence(d, 'case', case['id'])
        result['cases'].append({'id': case['id'], 'review_status': case.get('review_status', 'reviewed'),
                                'kind': case['kind'], 'last_result': (e.get('case_results', {}).get(case['id'], 'not-mapped') if case.get('test_name') else e.get('result')) if e else 'not-run'})
    delta = s.get('pending_change')
    if flow['phase'] == 'confirm':
        result['needs_decision'] = [{'question': '确认以下变化是否纳入本次范围', 'changes': delta or {'reason': '尚无当前版本的范围确认'}, 'preserved_tasks': delta.get('preserved_tasks', []) if delta else []}]
    elif flow['phase'] in ('questions', 'blocked', 'conventions', 'accept'):
        result['needs_decision'] = [{'question': flow['action'], 'details': flow.get('details', [])}]
    elif flow['phase'] == 'build':
        result['needs_decision'] = []  # Whether to execute follows the user's request, not another ritual confirmation.
    authorization = copy.deepcopy(s.get('execution_authorization', {}))
    if authorization:
        authorization['valid_for_current_scope'] = authorization.get('fingerprint') == fingerprint(d, s) and approval_current(d, s)
    result['authorization'] = authorization
    return result


def begin(workspace, req_id, request='', repo='', files=(), checks=(), acceptance='', out_of_scope='', profile='auto', risks=(), by='', authorization_note='', manual_acceptance='', apply=False):
    if not req_id:
        raise KitError('Agent 应从工单或用户描述生成稳定需求号，不要求用户手填状态')
    w, p, local, docs, root = load(workspace)
    target = inside(root, req_id)
    if (target / 'status.yaml').exists():
        return resume(workspace, req_id)
    chosen, reason = recommend_profile(request, files, risks) if profile == 'auto' else (profile, 'Agent 按实际范围选择；不能因此忽略已知风险')
    detected, _ = recommend_profile(request, files, risks)
    if chosen == 'quick' and detected == 'cross-system':
        chosen, reason = 'cross-system', '已声明风险，升级材料深度'
    summary = {'id': req_id, 'profile': chosen, 'reason': reason, 'request': request, 'files': list(files), 'checks': list(checks), 'mutates': apply}
    if not apply:
        return summary
    if chosen != 'quick':
        result = adopt(w, req_id, chosen, apply=True)
        return {**summary, **result, 'next_action': '接上已有材料并整理差异；不自动确认或实施'}
    if not request.strip() or repo not in p['repos'] or not files or not acceptance.strip() or not out_of_scope.strip():
        raise KitError('轻量任务仍需明确请求、仓库、文件、验收和不做事项；缺项由 Agent 先检查，业务歧义才询问')
    if not checks and not manual_acceptance.strip():
        raise KitError('缺少验证方式；Agent 应选择已有检查或具体人工验收步骤，不要求搭建完整 E2E')
    for check in checks:
        spec = p.get('runtime', {}).get('checks', {}).get(check)
        if not isinstance(spec, dict) or spec.get('repo') != repo:
            raise KitError('选择项目已有、能覆盖本次验收的检查，不能编造命令')
    for file in files:
        value = p['repos'][repo]
        inside(inside(w, value['path'] if isinstance(value, dict) else value), file)
    if target.exists() and any(target.iterdir()):
        raise KitError('目录已有材料；请按接管流程处理，不使用快速生成覆盖原件')
    adopt(w, req_id, 'quick', apply=True)
    state = read(target / 'status.yaml')
    bundle = {'state': {'title': request, 'sources': {'S1': {'type': 'text', 'status': 'collected', 'summary': request, 'version': '本轮明确请求'}}},
              'artifacts': {'brief.md': f'# 本次修改\n\n## 范围\n{request}\n\n## 明确不做\n{out_of_scope}\n\n## 验收\n{acceptance}\n\n## 修改范围\n' + '\n'.join(f'- {file}' for file in files),
                            'requirements.yaml': {'requirements': [{'id': 'R1', 'title': request, 'acceptance': acceptance, 'sources': ['S1']}], 'out_of_scope': [out_of_scope]},
                            'tasks.yaml': {'tasks': [{'id': 'TASK-1', 'title': request, 'repo': repo, 'requirements': ['R1'], 'files': list(files), 'checks': list(checks), 'depends_on': []}]},
                            'cases.yaml': {'cases': [{'id': f'T{i+1}', 'requirements': ['R1'], 'repo': repo, 'kind': 'auto', 'check': c, 'expected': acceptance} for i, c in enumerate(checks)]}}}
    if manual_acceptance:
        bundle['artifacts']['tasks.yaml']['tasks'][0]['manual_acceptance'] = manual_acceptance
        bundle['artifacts']['cases.yaml']['cases'].append({'id': 'T-manual', 'requirements': ['R1'], 'repo': repo, 'kind': 'manual', 'expected': manual_acceptance})
    prepare(w, req_id, state['revision'], bundle)
    if by and authorization_note:
        current = read(target / 'status.yaml')
        mutate(w, req_id, current['revision'], 'confirm', by=by, note=authorization_note)
        with state_lock(w):
            current = read(target / 'status.yaml')
            current['execution_authorization'] = {'by': by, 'note': authorization_note, 'fingerprint': fingerprint(target, current), 'tasks': ['TASK-1']}
            persist(target, current, current['revision'], 'execution-authorization', {'by': by, 'note': authorization_note})
    return {**summary, 'result': resume(w, req_id), 'next_action': 'Agent 在已有执行授权范围内开始任务；没有执行授权时仅汇报准备结果'}


def change(workspace, req_id, expected, bundle, apply=False):
    w, p, local, docs, directory, state = context(workspace, req_id)
    if state['revision'] != expected:
        raise KitError('revision 冲突；读取最新状态后重新比较')
    delta = analyze(directory, state, bundle)
    result = {'id': state['id'], 'revision': expected, 'delta': delta, 'mutates': apply,
              'question': '只需确认新增或改变的范围，不重复确认已保留工作' if delta['confirmation_required'] else None}
    if apply:
        result['update'] = prepare(w, state['id'], expected, bundle)
        result['next'] = resume(w, state['id'])
    return result


def error_response(message):
    if 'revision' in message:
        code, impact, action, needs_user = 'concurrent-update', '本次写入未应用，其他人的状态保留', 'Agent 重新读取状态，比较变化后重试；不要覆盖新版本', False
    elif '分支' in message:
        code, impact, action, needs_user = 'branch-policy', '暂不开始业务修改', '对照已确认策略检查当前分支；按已有授权切换，只有选择不明确时问用户', True
    elif '证据' in message or '通过' in message:
        code, impact, action, needs_user = 'verification-needed', '当前任务或交付尚未完成', '运行 assist review 查看是未运行、失败、代码变化还是命令变化，再处理对应检查', False
    elif '重新确认' in message or '确认已过期' in message:
        code, impact, action, needs_user = 'scope-changed', '旧确认不能覆盖新范围', '展示发生变化的部分和保留工作，只确认新增决定', True
    else:
        code, impact, action, needs_user = 'workflow-blocked', '本次操作未能完成；现有内容未自动回滚', 'Agent 根据错误定位缺项；可从已有配置恢复的先处理，业务歧义再询问用户', False
    return {'ok': False, 'error': message, 'code': code, 'impact': impact, 'next_action': action, 'needs_user_decision': needs_user}
