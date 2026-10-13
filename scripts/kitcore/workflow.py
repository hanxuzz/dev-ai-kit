"""Workflow state, approval snapshots, task dependencies and verification evidence."""
import copy
from contextvars import ContextVar
from contextlib import contextmanager
import fnmatch
import os
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import uuid
from . import SCHEMA
from .storage import KitError, read, atomic, inside, identifier, digest, lock, now
from .workspace import load, config_issues, git
from .changes import analyze, material_snapshot, subject_fingerprint
from .diagnostics import summarize, redact
from .testing import environment, junit_results
from .quality import contract_issues, review_issues, verification_issues

ROLES = {'requirement': '04-requirement.md', 'impact': '05-impact.md', 'plan': '06-plan.md', 'testcases': '07-testcases.md'}
STAGES = ('intake', 'meeting', 'sources', 'questions', 'requirement', 'impact', 'plan', 'build', 'test', 'done')


@contextmanager
def state_lock(workspace):
    w, project, local, docs, root = load(workspace)
    with lock(w):
        root.mkdir(parents=True, exist_ok=True)
        # Different local workspaces can point to the same shared requirements directory.
        with lock(root):
            yield


def role_file(directory, status, role):
    return inside(directory, status.get('files', {}).get(role) or ROLES[role])


def validate_state_shape(state):
    if state.get('schema_version') != SCHEMA:
        return
    for key in ('revision', 'scope_revision'):
        value = state.get(key, 0)
        if type(value) is not int or value < 0:
            raise KitError(f'{key} 必须是非负整数')
    for key in ('id', 'title', 'stage', 'questions', 'blocker', 'profile'):
        if not isinstance(state.get(key), str):
            raise KitError(f'status.{key} 必须是字符串')
    for key in ('files', 'sources', 'approval', 'tasks'):
        if not isinstance(state.get(key, {}), dict):
            raise KitError(f'status.{key} 必须是映射')
    if set(state.get('files', {})) - set(ROLES):
        raise KitError('files 包含未知角色')
    if any(value is not None and not isinstance(value, str) for value in state.get('files', {}).values()):
        raise KitError('files 的值必须是文件名字符串或空值')
    for source in state.get('sources', {}).values():
        if not isinstance(source, dict):
            raise KitError('每个 source 必须是对象')
        if 'required' in source and type(source['required']) is not bool:
            raise KitError('source.required 必须是布尔值')
        for key in ('path', 'status', 'reason', 'summary', 'url'):
            if key in source and not isinstance(source[key], str):
                raise KitError(f'source.{key} 必须是字符串')
    for task in state.get('tasks', {}).values():
        if not isinstance(task, dict) or task.get('status') not in ('pending', 'doing', 'done'):
            raise KitError('任务状态必须是 pending/doing/done')
    if not isinstance(state.get('history', []), list):
        raise KitError('history 必须是列表')


def context(workspace, req_id=None):
    w, project, local, docs, reqroot = load(workspace)
    req_id = identifier(req_id or local.get('current', ''))
    directory = inside(reqroot, req_id)
    state = read(directory / 'status.yaml')
    validate_state_shape(state)
    if state.get('schema_version') == SCHEMA and state.get('id') != req_id:
        raise KitError('status.id 与需求目录不一致')
    return w, project, local, docs, directory, state


def definitions(directory, name):
    obj = read(directory / f'{name}.yaml', {name: []})
    items = obj.get(name)
    if not isinstance(items, list) or any(not isinstance(x, dict) for x in items):
        raise KitError(f'{name}.yaml 的 {name} 必须是对象列表')
    ids = [x.get('id') for x in items]
    if any(not isinstance(x, str) or not x.strip() for x in ids) or len(set(ids)) != len(ids):
        raise KitError(f'{name} 编号缺失或重复')
    list_fields = {'requirements': ('sources',), 'tasks': ('requirements', 'depends_on', 'files', 'checks'), 'cases': ('requirements',)}
    text_fields = {'requirements': ('title', 'acceptance'), 'tasks': ('title', 'repo', 'manual_acceptance'), 'cases': ('repo', 'kind', 'expected', 'check')}
    for item in items:
        for field in list_fields[name]:
            value = item.get(field, [])
            if not isinstance(value, list) or any(not isinstance(x, str) or not x.strip() for x in value):
                raise KitError(f'{name}.{field} 必须是字符串列表')
        for field in text_fields[name]:
            if field in item and not isinstance(item[field], str):
                raise KitError(f'{name}.{field} 必须是字符串')
    return items


def source_snapshot(directory, state):
    sources = copy.deepcopy(state.get('sources', {}))
    for source in sources.values():
        if source.get('path'):
            path = inside(directory, source['path'])
            source['sha256'] = digest(path) if path.is_file() else 'missing'
    return sources


def fingerprint(directory, state):
    files = {}
    for role in ('requirement', 'impact', 'plan'):
        path = role_file(directory, state, role)
        files[role] = {'path': str(path.relative_to(directory)), 'sha256': digest(path) if path.is_file() else 'missing'}
    for name in ('requirements', 'tasks', 'cases'):
        path = directory / f'{name}.yaml'
        files[name] = digest(path) if path.is_file() else 'missing'
    return digest({'id': state.get('id'), 'files': files, 'sources': source_snapshot(directory, state), 'profile': state.get('profile'), 'questions': state.get('questions'), 'scope_revision': state.get('scope_revision', 0)})


def repo_path(w, project, name):
    value = project.get('repos', {}).get(name)
    if value is None:
        raise KitError(f'未知仓库：{name}')
    return inside(w, value['path'] if isinstance(value, dict) else value)


_snapshot_cache = ContextVar('readonly_snapshot_cache', default=None)


@contextmanager
def snapshot_observation():
    """One read-only observation; never wrap mutations or test execution."""
    cache = {'snapshots': {}, 'hits': 0, 'misses': 0}
    token = _snapshot_cache.set(cache)
    try:
        yield cache
    finally:
        _snapshot_cache.reset(token)


def code_files(w, project, docs, repo, inputs=None):
    path = repo_path(w, project, repo)
    try:
        proc = subprocess.run(['git', '-C', str(path), 'ls-files', '-co', '--exclude-standard', '-z', '--', '.'], capture_output=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise KitError('无法读取代码快照；验证需要 Git') from error
    if proc.returncode != 0:
        raise KitError('验证证据需要代码目录属于 Git 仓库')
    files = {}
    for raw in set(proc.stdout.split(b'\0')):
        if not raw:
            continue
        name = os.fsdecode(raw)
        if inputs is not None and not any(fnmatch.fnmatchcase(name, pattern) for pattern in inputs):
            continue
        target = path / name
        resolved = target.resolve()
        if docs == resolved or docs in resolved.parents or any(x in name.split('/') for x in ('.dev-ai-kit', '.git', '__pycache__', '.venv')) or name in ('project.yaml', 'project.local.yaml', '.dev-ai-kit.lock', '.cursor/next-step.txt'):
            continue
        if target.is_symlink():
            files[name] = 'symlink:' + os.readlink(target)
        else:
            files[name] = digest(target) if target.is_file() else 'missing'
    return files


def code_snapshot(w, project, docs, repo, inputs=None):
    if inputs is not None:
        if not isinstance(inputs, list) or not inputs or any(not isinstance(x, str) or not x or x.startswith('/') or '..' in x.split('/') for x in inputs):
            raise KitError('inputs 必须是非空相对路径/glob 列表；遗漏依赖会降低验证可信度')
    cache = _snapshot_cache.get()
    key = (str(repo_path(w, project, repo).resolve()), str(docs.resolve()), tuple(inputs) if inputs is not None else None)
    if cache is not None and key in cache['snapshots']:
        cache['hits'] += 1
        return dict(cache['snapshots'][key])
    files = code_files(w, project, docs, repo, inputs)
    result = {'head': git(repo_path(w, project, repo), 'rev-parse', 'HEAD'), 'tree': digest(files)}
    if cache is not None:
        cache['misses'] += 1
        cache['snapshots'][key] = result
    return dict(result)


def definition_issues(w, project, directory, state):
    issues = []
    requirements = definitions(directory, 'requirements')
    tasks = definitions(directory, 'tasks')
    cases = definitions(directory, 'cases')
    req_ids = {x['id'] for x in requirements}
    scope = read(directory / 'requirements.yaml', {'requirements': []})
    excluded = scope.get('out_of_scope')
    if not isinstance(excluded, list) or not excluded or any(not isinstance(x, str) or not x.strip() for x in excluded):
        issues.append('requirements.yaml 必须明确 out_of_scope（无排除项也须明确说明）')
    if state.get('profile') == 'cross-system':
        assessments = scope.get('assessments', {})
        for name in ('interfaces', 'data', 'permissions', 'failure_modes', 'async_cache', 'delivery_order', 'rollback'):
            if not isinstance(assessments, dict) or not isinstance(assessments.get(name), str) or not assessments[name].strip():
                issues.append(f'跨系统需求缺少影响评估 {name}（不适用需说明原因）')
    task_ids = {x['id'] for x in tasks}
    if not requirements:
        issues.append('缺少结构化验收 requirements.yaml')
    for r in requirements:
        if not r.get('title') or not r.get('acceptance') or not r.get('sources'):
            issues.append(f"{r['id']} 缺少标题、验收条件或来源编号")
        for source in r.get('sources', []):
            if source not in state.get('sources', {}):
                issues.append(f"{r['id']} 引用未知来源 {source}")
            elif state['sources'][source].get('status') != 'collected':
                issues.append(f"{r['id']} 引用的来源 {source} 尚未实际收集")
    if not tasks:
        issues.append('缺少结构化任务 tasks.yaml；已有 Markdown 清单应经确认后映射，不能猜测已完成')
    graph = {}
    assigned = set()
    checks = project.get('runtime', {}).get('checks', {})
    used_checks = {name for task in tasks for name in task.get('checks', [])}
    used_checks.update(case.get('check') for case in cases if case.get('kind') == 'auto')
    for name in used_checks:
        spec = checks.get(name)
        if not isinstance(spec, dict):
            issues.append(f'检查 {name} 未配置')
            continue
        try:
            environment(project, spec)
        except KitError as error:
            issues.append(str(error))
        if spec.get('report') not in (None, 'junit'):
            issues.append('检查 report 仅支持 junit')
        argv = spec.get('argv')
        if not isinstance(argv, list) or not argv or any(not isinstance(x, str) or not x for x in argv):
            issues.append(f'检查 {name} 的 argv 必须是非空字符串数组')
        if spec.get('repo') in project['repos']:
            inside(repo_path(w, project, spec['repo']), spec.get('cwd') or '.')
        else:
            issues.append(f'检查 {name} 的仓库不存在')
    for task in tasks:
        tid = task['id']
        issues.extend(contract_issues(w, project, directory, task))
        assigned.update(task.get('requirements', []))
        graph[tid] = task.get('depends_on', [])
        if not isinstance(graph[tid], list) or any(x not in task_ids or x == tid for x in graph[tid]):
            issues.append(f'{tid} 的任务依赖无效')
            graph[tid] = []
        if task.get('repo') not in project['repos']:
            issues.append(f'{tid} 的仓库未配置')
        if not task.get('requirements') or any(x not in req_ids for x in task.get('requirements', [])):
            issues.append(f'{tid} 的需求映射无效')
        if not task.get('title') or not task.get('files'):
            issues.append(f'{tid} 缺少目标或文件范围')
        elif task.get('repo') in project['repos']:
            for file in task['files']:
                inside(repo_path(w, project, task['repo']), file)
        if not task.get('checks') and not task.get('manual_acceptance'):
            issues.append(f'{tid} 缺少验证命令或人工验收条件')
        for check in task.get('checks', []):
            spec = checks.get(check) if isinstance(checks.get(check), dict) else {}
            env = project.get('runtime', {}).get('environments', {}).get(spec.get('environment'), {})
            if env.get('kind') == 'dev':
                issues.append(f'{tid} 不能用 dev 部署的检查证明本地代码完成；将 dev 检查映射到验收用例')
            if not isinstance(checks.get(check), dict) or checks[check].get('repo') != task.get('repo'):
                issues.append(f'{tid} 的检查 {check} 未配置或属于其他仓库')
    if req_ids - assigned:
        issues.append('需求没有任务承接：' + ', '.join(sorted(req_ids - assigned)))
    def visit(node, active, done):
        if node in active:
            raise KitError('任务依赖存在循环')
        if node in done:
            return
        for child in graph[node]:
            visit(child, active | {node}, done)
        done.add(node)
    done = set()
    for node in graph:
        visit(node, set(), done)
    covered = set()
    for case in cases:
        cid = case['id']
        if case.get('review_status', 'reviewed') != 'reviewed':
            issues.append(f'{cid} 是未审阅用例草稿，先核对步骤、预期和覆盖')
        if not case.get('requirements') or any(x not in req_ids for x in case.get('requirements', [])):
            issues.append(f'{cid} 的验收映射无效')
        if not case.get('expected'):
            issues.append(f'{cid} 缺少预期结果')
        if case.get('kind') not in ('auto', 'manual'):
            issues.append(f'{cid} 的类型必须为 auto/manual')
        if case.get('repo') not in project['repos']:
            issues.append(f'{cid} 的仓库未配置')
        if case.get('kind') == 'auto':
            check = case.get('check')
            if not isinstance(checks.get(check), dict) or checks[check].get('repo') != case.get('repo'):
                issues.append(f'{cid} 的自动检查未配置或仓库不匹配')
            spec = checks.get(check) if isinstance(checks.get(check), dict) else {}
            if case.get('test_name') and spec.get('report') != 'junit':
                issues.append(f'{cid} 的逐条自动结果需要 report: junit')
            if spec.get('report') == 'junit' and (not isinstance(case.get('test_name'), str) or '::' not in case['test_name']):
                issues.append(f'{cid} 需要精确 test_name: classname::name')
        covered.update(case.get('requirements', []))
    if req_ids - covered:
        issues.append('验收未覆盖：' + ', '.join(sorted(req_ids - covered)))
    if not cases:
        issues.append('缺少 cases.yaml；每条需求必须有自动或人工验收')
    return issues


def approval_current(directory, state):
    approval = state.get('approval', {})
    return bool(approval.get('by') and approval.get('note') and approval.get('fingerprint') == fingerprint(directory, state))


def issues_for(workspace, req_id=None, ready=False):
    problems = config_issues(workspace)
    w, p, local, docs, d, s = context(workspace, req_id)
    if s.get('schema_version') != SCHEMA:
        return problems + ['旧版需求状态：请执行 adopt --apply 迁移；不自动继承完成和确认']
    if s.get('stage') not in STAGES or s.get('questions') not in ('none', 'open', 'confirmed'):
        problems.append('stage/questions 状态无效')
    if s.get('questions') == 'open' and s.get('stage') != 'questions':
        problems.append('未决问题必须停在 questions')
    if s.get('blocker'):
        problems.append('当前需求受阻：' + s['blocker'])
    if s.get('profile') not in ('quick', 'standard', 'cross-system'):
        problems.append('profile 无效')
    for role in ROLES:
        role_file(d, s, role)
    if ready:
        if s.get('questions') == 'open':
            problems.append('仍有未决问题')
        for role in ('requirement', 'impact', 'plan'):
            path = role_file(d, s, role)
            if not path.is_file() or len(path.read_text(encoding='utf-8').strip()) < 20:
                problems.append(f'{role} 缺少有效正文')
        if s.get('profile') != 'quick' and role_file(d, s, 'impact') in (role_file(d, s, 'requirement'), role_file(d, s, 'plan')):
            problems.append('影响分析不能复用规格或计划本身')
        for sid, source in s.get('sources', {}).items():
            if source.get('required', True) and source.get('status') not in ('collected', 'skipped'):
                problems.append(f'必需来源 {sid} 尚未收集')
            if source.get('status') == 'skipped' and not source.get('reason'):
                problems.append(f'来源 {sid} 跳过原因为空')
            if source.get('status') not in ('pending', 'collected', 'skipped'):
                problems.append(f'来源 {sid} 的状态无效')
            if source.get('status') == 'collected' and source.get('path') and not inside(d, source['path']).is_file():
                problems.append(f'来源 {sid} 本地快照不存在')
        problems += definition_issues(w, p, d, s)
    return problems


def persist(directory, state, expected, event, detail):
    current = read(directory / 'status.yaml')
    if current.get('revision', 0) != expected:
        raise KitError('revision 冲突；请重新读取状态再决定，不能覆盖另一位开发者的更新')
    state['revision'] = expected + 1
    state.setdefault('history', []).append({'at': now(), 'event': event, 'detail': detail})
    atomic(directory / 'status.yaml', state)


def adopt(workspace, req_id, profile='standard', apply=False):
    w, p, local, docs, root = load(workspace)
    identifier(req_id)
    d = inside(root, req_id)
    old = read(d / 'status.yaml', {})
    if old.get('schema_version') == SCHEMA:
        return {'action': 'select', 'id': req_id, 'revision': old['revision'], 'hint': '使用 select 切换 current；无需重复 adopt'}
    files = dict(old.get('files') or {})
    if profile == 'quick' and not files:
        files = {role: 'brief.md' for role in ('requirement', 'impact', 'plan')}
    material = [x.name for x in d.iterdir() if x.is_file()] if d.exists() else []
    state = {'schema_version': SCHEMA, 'id': req_id, 'title': old.get('title') or req_id,
             'revision': 0, 'scope_revision': 0, 'profile': profile, 'stage': 'intake', 'questions': 'none', 'blocker': '',
             'files': files, 'sources': {}, 'approval': {}, 'tasks': {}, 'history': []}
    if old.get('questions') == 'open':
        state.update(questions='open', stage='questions')
    state['blocker'] = old.get('blocker') or ''
    if old:
        state['legacy'] = old
    result = {'id': req_id, 'apply': apply, 'existing_materials': material, 'next': '登记来源、files 映射和结构化任务；保留原件，已有完成状态必须重新核验'}
    if not apply:
        return result
    with state_lock(w):
        # A second install/adopt must not replace an already established state.
        latest = read(d / 'status.yaml', {})
        if latest != old:
            raise KitError('接管期间需求状态发生变化，请重试预览')
        d.mkdir(parents=True, exist_ok=True)
        if old:
            atomic(d / '.kit/legacy-status.yaml', (d / 'status.yaml').read_bytes())
        state['history'].append({'at': now(), 'event': 'adopt', 'detail': '保留既有材料，不推断确认或完成'})
        atomic(d / 'status.yaml', state)
        local['current'] = req_id
        atomic(w / 'project.local.yaml', local)
    return result


def branch_issues(w, p, repo, req_id):
    conv = p.get('conventions', {})
    if conv.get('confirmed') is not True:
        return ['项目规范尚未确认；仅禁止业务修改，不阻挡材料整理']
    policy = conv.get('branch', {})
    mode = policy.get('mode', 'project')
    if mode not in ('project', 'current', 'feature'):
        return ['branch.mode 无效']
    name = git(repo_path(w, p, repo), 'branch', '--show-current')
    if not name:
        return ['无法确认当前 Git 分支（可能为 detached HEAD）']
    if mode == 'feature':
        pattern = policy.get('pattern')
        if not pattern or not policy.get('base'):
            return ['feature 策略缺少已确认 base/pattern']
        if name != pattern.replace('{id}', req_id):
            return ['当前分支不符合需求分支规范；是否允许创建由 auto_create 单独决定']
    if mode == 'project':
        allowed = policy.get('allowed_pattern')
        if not allowed:
            return ['请根据团队规范配置 allowed_pattern，或明确选择 current 模式；不能猜测开发分支']
        try:
            if not re.fullmatch(allowed, name):
                return ['当前分支不符合团队 allowed_pattern']
        except re.error:
            return ['allowed_pattern 不是有效正则表达式']
    return []


def latest_evidence(directory, target_type, target):
    records = []
    for path in (directory / '.kit/evidence').glob('*.yaml'):
        e = read(path)
        if e.get('target_type') == target_type and e.get('target') == target:
            records.append(e)
    return max(records, key=lambda e: e['at']) if records else None


def valid_evidence(w, project, docs, directory, state, kind, target, repo):
    e = latest_evidence(directory, kind, target)
    if not e or e.get('result') != 'passed':
        return False
    if e.get('subject_fingerprint'):
        if e['subject_fingerprint'] != subject_fingerprint(directory, state, kind, target):
            return False
    elif e.get('fingerprint') != fingerprint(directory, state):
        return False
    if kind == 'check' and e.get('check_hash') != digest(project.get('runtime', {}).get('checks', {}).get(target, {})):
        return False
    if kind == 'check':
        env, _ = environment(project, project.get('runtime', {}).get('checks', {}).get(target, {}))
        if e.get('environment') != env:
            return False
    inputs = project.get('runtime', {}).get('checks', {}).get(target, {}).get('inputs') if kind == 'check' else None
    return e.get('code', {}).get('tree') == code_snapshot(w, project, docs, repo, inputs)['tree']


def completion_issues(w, p, docs, d, s):
    problems = []
    for task in definitions(d, 'tasks'):
        tid = task['id']
        problems.extend(review_issues(w, p, docs, d, s, task))
        if s.get('tasks', {}).get(tid, {}).get('status') != 'done':
            problems.append(f'任务 {tid} 未完成')
        for check in task.get('checks', []):
            if not valid_evidence(w, p, docs, d, s, 'check', check, task['repo']):
                problems.append(f'{tid} 的检查 {check} 缺少当前代码的通过证据')
        if task.get('manual_acceptance') and not valid_evidence(w, p, docs, d, s, 'task', tid, task['repo']):
            problems.append(f'{tid} 缺少当前代码的人工验收')
    for case in definitions(d, 'cases'):
        kind = 'check' if case['kind'] == 'auto' else 'case'
        target = case['check'] if kind == 'check' else case['id']
        passed = valid_evidence(w, p, docs, d, s, kind, target, case['repo'])
        if kind == 'check' and case.get('test_name'):
            evidence = latest_evidence(d, kind, target) or {}
            passed = passed and evidence.get('case_results', {}).get(case['id']) == 'passed'
        if not passed:
            problems.append(f"用例 {case['id']} 尚未在当前代码上通过")
    return problems


def mutate(workspace, req_id, expected, action, by='', note='', target='', value=''):
    w = Path(workspace).resolve()
    with state_lock(w):
        w, p, local, docs, d, s = context(workspace, req_id)
        if s.get('schema_version') != SCHEMA or s.get('revision') != expected:
            raise KitError('状态版本不兼容或 revision 冲突；请重新读取')
        if action in ('confirm', 'complete', 'change', 'manual') and (not by.strip() or not note.strip()):
            raise KitError('此操作需要 by 和 note，必须对应真实确认或变更记录')
        if action in ('confirm', 'start', 'finish', 'complete', 'manual'):
            problems = issues_for(w, req_id, ready=True)
            if problems:
                raise KitError('；'.join(problems))
        if action == 'confirm':
            if not approval_current(d, s):
                delta = s.get('pending_change', {})
                preserve = delta.get('fingerprint') == fingerprint(d, s) and delta.get('kind') == 'scoped'
                s['scope_revision'] = s.get('scope_revision', 0) + 1
                if not preserve:
                    s['evidence_epoch'] = s.get('evidence_epoch', 0) + 1
                    for task in s.get('tasks', {}).values():
                        task['status'] = 'pending'
            s['approval'] = {'by': by, 'note': note, 'at': now(), 'fingerprint': fingerprint(d, s), 'snapshot': material_snapshot(d, s)}
            s.pop('pending_change', None)
            s['stage'] = 'plan'
        elif action == 'change':
            s['evidence_epoch'] = s.get('evidence_epoch', 0) + 1
            s['scope_revision'] = s.get('scope_revision', 0) + 1
            s['approval'] = {}
            s['stage'] = 'questions' if s.get('questions') == 'open' else 'impact'
            for task in s.get('tasks', {}).values():
                task['status'] = 'pending'
            s['change'] = {'by': by, 'reason': note, 'at': now()}
        elif action == 'block':
            s['blocker'] = note
        elif action in ('start', 'finish'):
            if not approval_current(d, s):
                raise KitError('范围或任务发生变化；需要重新确认当前版本')
            task = next((t for t in definitions(d, 'tasks') if t['id'] == target), None)
            if not task:
                raise KitError('任务不存在')
            problems = branch_issues(w, p, task['repo'], s['id'])
            if problems:
                raise KitError('；'.join(problems))
            if any(s.get('tasks', {}).get(x, {}).get('status') != 'done' for x in task.get('depends_on', [])):
                raise KitError('前置任务未完成')
            entry = s.setdefault('tasks', {}).setdefault(target, {'status': 'pending'})
            if action == 'start':
                problems = contract_issues(w, p, d, task, check_references=True)
                if problems:
                    raise KitError('；'.join(problems))
                if entry['status'] == 'doing':
                    raise KitError('任务已在进行中；直接续接，不重置修改前快照')
                if entry['status'] == 'done':
                    raise KitError('已完成任务不能重复开始；先记录变更')
                if any(x != target and e.get('status') == 'doing' for x, e in s['tasks'].items()):
                    raise KitError('已有进行中任务；先完成或记录交接')
                entry.update(status='doing', started_at=now(), code_before=code_snapshot(w, p, docs, task['repo']), files_before=code_files(w, p, docs, task['repo']))
                s['stage'] = 'build'
            else:
                if entry['status'] != 'doing':
                    raise KitError('任务必须先 start')
                before_files = entry.get('files_before', {})
                after_files = code_files(w, p, docs, task['repo'])
                changed = [name for name in set(before_files) | set(after_files) if before_files.get(name) != after_files.get(name)]
                unexpected = [name for name in changed if not any(fnmatch.fnmatchcase(name, pattern) for pattern in task['files'])]
                if unexpected:
                    raise KitError('任务范围外文件发生变化；先核对是否属于其他人的修改，不回滚：' + ', '.join(sorted(unexpected)))
                for check in task.get('checks', []):
                    if not valid_evidence(w, p, docs, d, s, 'check', check, task['repo']):
                        raise KitError(f'检查 {check} 缺少当前代码的通过证据')
                if task.get('manual_acceptance') and not valid_evidence(w, p, docs, d, s, 'task', target, task['repo']):
                    raise KitError('缺少本次人工验收证据')
                problems = review_issues(w, p, docs, d, s, task) + verification_issues(w, p, docs, d, s, task)
                if problems:
                    raise KitError('；'.join(problems))
                entry.update(status='done', finished_at=now())
                if all(s['tasks'].get(t['id'], {}).get('status') == 'done' for t in definitions(d, 'tasks')):
                    s['stage'] = 'test'
        elif action == 'manual':
            if not approval_current(d, s):
                raise KitError('先确认当前需求版本')
            kind, _, item_id = target.partition(':')
            collection = 'tasks' if kind == 'task' else 'cases'
            item = next((x for x in definitions(d, collection) if x['id'] == item_id), None)
            if kind not in ('task', 'case') or not item or (kind == 'case' and item.get('kind') != 'manual') or (kind == 'task' and not item.get('manual_acceptance')):
                raise KitError('只能记录配置了人工验收的 task:id 或 case:id')
            if value not in ('passed', 'failed', 'blocked'):
                raise KitError('人工结果必须为 passed/failed/blocked')
            evidence = {'id': uuid.uuid4().hex, 'at': now(), 'target_type': kind, 'target': item_id, 'by': by, 'note': note, 'result': value, 'fingerprint': fingerprint(d, s), 'subject_fingerprint': subject_fingerprint(d, s, kind, item_id), 'code': code_snapshot(w, p, docs, item['repo'])}
            atomic(d / '.kit/evidence' / (evidence['id'] + '.yaml'), evidence)
        elif action == 'complete':
            if not approval_current(d, s):
                raise KitError('需求确认已过期')
            problems = completion_issues(w, p, docs, d, s)
            if problems:
                raise KitError('；'.join(problems))
            s['stage'] = 'done'
            s['completion'] = {'by': by, 'note': note, 'at': now()}
        else:
            raise KitError('未知状态操作')
        persist(d, s, expected, action, {'target': target, 'by': by, 'note': note})
        return {'id': s['id'], 'revision': s['revision'], 'stage': s['stage'], 'action': action}


def run_check(workspace, req_id, check_id, expected, ready=(), diagnostic_log=False):
    w, p, local, docs, d, s = context(workspace, req_id)
    req_id = s['id']  # Pin selection: switching current during a check must not write to another requirement.
    if s.get('revision') != expected:
        raise KitError('revision 冲突')
    problems = issues_for(w, req_id, ready=True)
    if problems or not approval_current(d, s):
        raise KitError('；'.join(problems) or '当前需求未确认')
    check = p.get('runtime', {}).get('checks', {}).get(check_id)
    if not isinstance(check, dict):
        raise KitError('检查命令未配置')
    argv = check.get('argv')
    if not isinstance(argv, list) or not argv or any(not isinstance(x, str) or not x for x in argv):
        raise KitError('argv 必须是非空字符串数组；不能使用隐式 shell 命令')
    timeout = check.get('timeout_seconds', 120)
    if type(timeout) not in (int, float) or not 0 < timeout <= 3600:
        raise KitError('timeout_seconds 必须在 1..3600')
    requires = check.get('requires', [])
    if not isinstance(requires, list) or any(not isinstance(x, str) for x in requires):
        raise KitError('requires 必须是字符串列表')
    if set(requires) - set(ready):
        raise KitError('前置条件未确认：' + ', '.join(sorted(set(requires) - set(ready))))
    if 'database' in requires and p.get('runtime', {}).get('database', {}).get('readonly') is not True:
        raise KitError('数据库检查需要已配置的只读账号；配置声明不能替代数据库实际权限')
    env_snapshot, injected = environment(p, check, require_secrets=True)
    if env_snapshot and env_snapshot['kind'] == 'dev' and f"environment:{env_snapshot['name']}" not in ready:
        raise KitError('dev 环境执行前需核实目标、部署版本、账号和数据范围，再传 --ready environment:<名称>')
    path = repo_path(w, p, check['repo'])
    cwd = inside(path, check.get('cwd') or '.')
    before = code_snapshot(w, p, docs, check['repo'], check.get('inputs'))
    all_before = code_snapshot(w, p, docs, check['repo'])
    fp = fingerprint(d, s)
    report_path = None
    if check.get('report') == 'junit':
        report_path = inside(w, '.dev-ai-kit/reports/' + uuid.uuid4().hex + '.xml')
        report_path.parent.mkdir(parents=True, exist_ok=True)
        injected['KIT_JUNIT_PATH'] = str(report_path)
    child_env = {k: v for k, v in os.environ.items() if k not in ('KIT_BASE_URL', 'KIT_ENVIRONMENT', 'KIT_ENVIRONMENT_KIND', 'KIT_JUNIT_PATH')}
    child_env.update(injected)
    # Raw output stays temporary by default; optional local logs receive best-effort redaction.
    with tempfile.TemporaryFile() as output:
        try:
            proc = subprocess.Popen(argv, cwd=cwd, env=child_env, stdout=output, stderr=subprocess.STDOUT, start_new_session=os.name != 'nt')
        except OSError as error:
            raise KitError('检查命令无法启动，请核对执行文件和目录') from error
        timed_out = False
        try:
            code = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            if os.name == 'nt':
                subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'], capture_output=True)
            else:
                os.killpg(proc.pid, signal.SIGKILL)
            code = proc.wait()
        except BaseException:
            if os.name == 'nt':
                subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'], capture_output=True)
            else:
                os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            raise
        output.seek(0)
        import hashlib
        output_hash = hashlib.sha256()
        byte_count = 0
        for chunk in iter(lambda: output.read(65536), b''):
            output_hash.update(chunk)
            byte_count += len(chunk)
        output.seek(max(0, byte_count - 32768))
        excerpt = output.read().decode('utf-8', errors='replace')
    after = code_snapshot(w, p, docs, check['repo'])
    result = 'passed' if code == 0 and not timed_out and all_before == after else 'failed'
    diagnostic = summarize(excerpt, code, timed_out, all_before != after)
    report = None
    if report_path:
        try:
            report = junit_results(report_path, [c for c in definitions(d, 'cases') if c.get('check') == check_id and c.get('kind') == 'auto'])
        except KitError:
            report = {'ok': False, 'cases': {}, 'tests': 0, 'failures': 0}
        finally:
            report_path.unlink(missing_ok=True)
        if not report['ok']:
            result = 'failed'
            diagnostic = {'category': 'case-results', 'message': '逐条结果未通过、缺失、跳过、重复或报告无效', 'next_action': '检查 JUnit 输出及 test_name 映射，不能用命令成功替代用例通过'}
    log_path = None
    if diagnostic_log:
        log_path = w / '.dev-ai-kit/diagnostics' / (uuid.uuid4().hex + '.log')
        atomic(log_path, redact(excerpt))
        log_path.chmod(0o600)
    with state_lock(w):
        _, current_project, _, _, current_dir, current = context(w, req_id)
        current_check = current_project.get('runtime', {}).get('checks', {}).get(check_id, {})
        current_env, _ = environment(current_project, current_check)
        if digest(current_check) != digest(check) or current_env != env_snapshot:
            raise KitError('执行期间测试配置或环境改变；结果不记为有效证据')
        if current.get('revision') != expected or fingerprint(current_dir, current) != fp:
            raise KitError('执行期间需求状态改变；本次结果不记为有效证据，请重新检查')
        e = {'id': uuid.uuid4().hex, 'at': now(), 'target_type': 'check', 'target': check_id, 'result': result, 'exit_code': code, 'timed_out': timed_out, 'code_changed_during_check': all_before != after,
             'code': before, 'fingerprint': fp, 'subject_fingerprint': subject_fingerprint(d, current, 'check', check_id), 'check_hash': digest(check), 'output_sha256': output_hash.hexdigest(), 'output_bytes': byte_count, 'diagnostic': diagnostic, 'environment': env_snapshot, 'case_results': report['cases'] if report else {}, 'report': report}
        atomic(d / '.kit/evidence' / (e['id'] + '.yaml'), e)
        persist(d, current, expected, 'check', {'id': check_id, 'result': result, 'evidence': e['id']})
    return {**e, 'requirement_id': req_id, 'revision': current['revision'], 'local_diagnostic_log': str(log_path) if log_path else None}


def next_step(workspace, req_id=None):
    w, p, local, docs, root = load(workspace)
    ids = sorted(x.name for x in root.iterdir() if x.is_dir() and not x.name.startswith('.')) if root.exists() else []
    selected = req_id or local.get('current')
    if not selected:
        return {'phase': 'select', 'action': '选择已有需求，或登记新需求', 'requirements': ids, 'mutates': False}
    d = inside(root, identifier(selected))
    if not (d / 'status.yaml').exists():
        return {'phase': 'adopt', 'action': f'{selected} 还没有新的进度记录。先只看一眼，不改任何文件，原来的规格和计划都留着。你回复可以接管之后，才会把新进度记下来。在这之前不改业务代码。', 'mutates': False}
    w, p, local, docs, d, s = context(w, selected)
    result = {'id': selected, 'revision': s.get('revision', 0), 'phase': '', 'action': '', 'mutates': False}
    def answer(phase, action, details=None):
        result.update(phase=phase, action=action)
        if details:
            result['details'] = details
        return result
    if s.get('schema_version') != SCHEMA:
        return answer('adopt', '这是旧版进度。先只看一眼，不改文件：原来的规格和计划都留着。以前清单上打过勾的，不算已经做完。你回复可以接管之后，才会写入新进度。在这之前不改业务代码。')
    if s.get('blocker'):
        return answer('blocked', '先处理当前阻塞', [s['blocker']])
    if s.get('questions') == 'open':
        return answer('questions', '确认未决事项；不修改未确认范围的业务代码')
    problems = issues_for(w, selected, ready=True)
    if problems:
        return answer('prepare', '补齐当前需求的必需材料和验收映射', problems)
    if not approval_current(d, s):
        return answer('confirm', '确认当前版本的范围、影响和任务；旧确认不能覆盖新变更')
    tasks = definitions(d, 'tasks')
    result['tasks'] = [{'id': t['id'], 'title': t['title'], 'status': s.get('tasks', {}).get(t['id'], {}).get('status', 'pending')} for t in tasks]
    unfinished = [t for t in tasks if s.get('tasks', {}).get(t['id'], {}).get('status') != 'done']
    if unfinished:
        doing = [t for t in unfinished if s.get('tasks', {}).get(t['id'], {}).get('status') == 'doing']
        available = doing or [t for t in unfinished if all(s.get('tasks', {}).get(x, {}).get('status') == 'done' for x in t.get('depends_on', []))]
        if not available:
            return answer('blocked', '没有可执行任务；检查依赖状态')
        task = available[0]
        if not doing:
            problems = contract_issues(w, p, d, task, check_references=True)
            if problems:
                return answer('prepare', '项目实现依据已变化，先核对再开始任务', problems)
        problems = branch_issues(w, p, task['repo'], s['id'])
        if problems:
            return answer('conventions', '先满足已确认的仓库规范', problems)
        return answer('build', f"{'继续' if doing else '可执行'}任务 {task['id']}：{task['title']}；只有用户授权执行时才开始")
    problems = completion_issues(w, p, docs, d, s)
    if problems:
        return answer('test', '验证当前代码；历史结果或旧版本结果不算本次通过', problems)
    if s.get('stage') == 'done':
        return answer('done', '需求已完成；可选择或登记下一条需求')
    return answer('accept', '证据齐全；请用户确认本轮验收结束，再标记完成')


def prepare(workspace, req_id, expected, bundle):
    """Apply reviewed material updates. Invalidate first so interruption cannot retain approval."""
    w = Path(workspace).resolve()
    with state_lock(w):
        w, p, local, docs, d, s = context(w, req_id)
        if s.get('schema_version') != SCHEMA or s.get('revision') != expected:
            raise KitError('revision 冲突或旧版状态；请重新读取')
        allowed = {'title', 'profile', 'files', 'sources', 'questions', 'blocker', 'handoff'}
        fields = bundle.get('state', {})
        if not isinstance(fields, dict) or set(fields) - allowed:
            raise KitError('prepare 只能更新材料、映射、问题、阻塞和交接；不能写确认、完成或历史')
        artifacts = bundle.get('artifacts', {})
        if not isinstance(artifacts, dict):
            raise KitError('artifacts 必须是相对路径到内容的映射')
        candidate = copy.deepcopy(s)
        candidate.update(fields)
        validate_state_shape(candidate)
        if candidate.get('questions') not in ('none', 'open', 'confirmed'):
            raise KitError('questions 必须是 none/open/confirmed')
        if candidate.get('profile') not in ('quick', 'standard', 'cross-system'):
            raise KitError('profile 无效')
        if not isinstance(candidate.get('sources'), dict) or any(not isinstance(x, dict) for x in candidate['sources'].values()):
            raise KitError('sources 必须是来源编号到对象的映射')
        if not isinstance(candidate.get('files'), dict) or set(candidate['files']) - set(ROLES):
            raise KitError('files 包含未知文件角色')
        valid_names = {str(role_file(d, candidate, r).relative_to(d)) for r in ROLES}
        valid_names.update(('requirements.yaml', 'tasks.yaml', 'cases.yaml', '01-meeting.md', '02-sources.md', '03-questions.md'))
        for name, value in artifacts.items():
            inside(d, name)
            if name not in valid_names or not isinstance(value, (str, dict)):
                raise KitError('只能编辑声明的需求文档和结构化定义，不能覆盖状态或证据')
        if candidate['questions'] == 'open':
            protected = {str(role_file(d, candidate, r).relative_to(d)) for r in ('requirement', 'impact', 'plan')}
            protected.update(('requirements.yaml', 'tasks.yaml'))
            if set(artifacts) & protected:
                raise KitError('问题未确认时只整理来源和问题，不能写最终需求和计划')
        before = fingerprint(d, s)
        # Backup material bytes before any writes; useful for interrupted edits and manual recovery.
        backup = d / '.kit/edits' / uuid.uuid4().hex
        if artifacts:
            for name in artifacts:
                path = inside(d, name)
                if path.is_file():
                    atomic(inside(backup, name), path.read_bytes())
        delta = analyze(d, s, bundle)
        was_approved = approval_current(d, s)
        candidate['approval'] = {} if artifacts or delta['confirmation_required'] else candidate.get('approval', {})
        if delta['confirmation_required']:
            candidate['scope_revision'] = candidate.get('scope_revision', 0) + 1
            if delta['kind'] == 'broad':
                candidate['evidence_epoch'] = candidate.get('evidence_epoch', 0) + 1
            for tid, entry in candidate.get('tasks', {}).items():
                if delta['kind'] == 'broad' or tid in delta['affected_tasks']:
                    entry['status'] = 'pending'
            candidate['stage'] = 'questions' if candidate['questions'] == 'open' else 'impact'
        if artifacts or delta['confirmation_required']:
            candidate.pop('pending_change', None)
        persist(d, candidate, expected, 'prepare', {'fields': sorted(fields), 'artifacts': sorted(artifacts), 'backup': str(backup.relative_to(d)) if artifacts else '', 'previous_fingerprint': before, 'delta': delta})
        # Invalidate before writing. Interruption leaves an unapproved draft, never a partial approved one.
        for name, value in artifacts.items():
            atomic(inside(d, name), value)
        if artifacts or delta['confirmation_required']:
            if was_approved and delta['kind'] in ('none', 'editorial'):
                candidate['approval'] = copy.deepcopy(s['approval'])
                candidate['approval']['fingerprint'] = fingerprint(d, candidate)
                candidate['approval']['editorial_note'] = delta['reason']
                if candidate.get('execution_authorization', {}).get('fingerprint') == before:
                    candidate['execution_authorization']['fingerprint'] = candidate['approval']['fingerprint']
            else:
                candidate['pending_change'] = {**delta, 'fingerprint': fingerprint(d, candidate)}
            persist(d, candidate, candidate['revision'], 'material-update-complete', {'delta': delta})
        return {'id': candidate['id'], 'revision': candidate['revision'], 'approval_current': approval_current(d, candidate), 'delta': delta, 'backup': str(backup.relative_to(d)) if artifacts else None}



def select(workspace, req_id):
    w, p, local, docs, root = load(workspace)
    identifier(req_id)
    if not (inside(root, req_id) / 'status.yaml').is_file():
        raise KitError('需求尚未接管；先 adopt，不先设置无效 current')
    with state_lock(w):
        local = read(w / 'project.local.yaml')
        local['current'] = req_id
        atomic(w / 'project.local.yaml', local)
    return {'current': req_id}
