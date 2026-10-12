"""Development contracts and reviews bound to actual code, not completion checkboxes."""
import copy
from .storage import KitError, read, inside, digest, now


def required(project, task):
    policy = project.get('development', {}).get('require_contract', False)
    if type(policy) is not bool:
        raise KitError('development.require_contract 必须是布尔值')
    return policy or 'development' in task


def reference_snapshot(workspace, project, contract, must_exist=False):
    from .workflow import repo_path
    result = []
    refs = contract.get('references', [])
    if not isinstance(refs, list):
        raise KitError('references 必须是对象列表')
    for ref in refs:
        if not isinstance(ref, dict) or not ref.get('reason'):
            raise KitError('参考实现需要 repo/path/reason')
        file = inside(repo_path(workspace, project, ref.get('repo')), ref.get('path'))
        if must_exist and not file.is_file():
            raise KitError('参考实现文件不存在；重新调查项目，不能以示例代替')
        result.append({'repo': ref['repo'], 'path': ref['path'], 'sha256': digest(file) if file.is_file() else 'missing'})
    return result


def contract_issues(workspace, project, directory, task, check_references=False):
    from .workflow import definitions
    if not required(project, task):
        return []
    prefix = f"{task['id']} 开发依据："
    c = task.get('development')
    if not isinstance(c, dict):
        return [prefix + '先调查需求行为、参考实现、复用与影响，再用 quality plan 保存']
    issues = []
    for key in ('approach', 'reuse', 'impact', 'preserve', 'regression'):
        if not isinstance(c.get(key), str) or not c[key].strip():
            issues.append(prefix + f'缺少 {key} 的具体依据')
    refs = c.get('references')
    if not isinstance(refs, list) or not refs:
        issues.append(prefix + '至少记录一处实际参考代码或项目规范，新项目可引用已确认设计/规范文件')
    else:
        try:
            actual = reference_snapshot(workspace, project, c, must_exist=check_references)
            if check_references and actual != c.get('reference_snapshot'):
                issues.append(prefix + '参考实现已变化，请重新调查并更新开发依据')
        except KitError as error:
            issues.append(prefix + str(error))
    behaviors = c.get('behaviors')
    cases = {x['id']: x for x in definitions(directory, 'cases')}
    regression_cases = c.get('regression_cases')
    if not isinstance(regression_cases, list) or not regression_cases or any(not isinstance(cid, str) or cid not in cases for cid in regression_cases):
        issues.append(prefix + '保留行为必须关联真实 regression_cases（自动或人工验收），不能只写回归口号')
    covered = set()
    if not isinstance(behaviors, list) or not behaviors:
        issues.append(prefix + '缺少需求到行为与验收的映射')
    else:
        for b in behaviors:
            if not isinstance(b, dict):
                issues.append(prefix + 'behaviors 必须为对象列表'); continue
            rid = b.get('requirement')
            if rid not in task.get('requirements', []):
                issues.append(prefix + '行为引用了本任务以外的需求')
            else:
                covered.add(rid)
            for key in ('current', 'expected'):
                if not isinstance(b.get(key), str) or not b[key].strip():
                    issues.append(prefix + f'行为缺少 {key}')
            ids = b.get('cases')
            if not isinstance(ids, list) or not ids or any(not isinstance(cid, str) or cid not in cases or rid not in cases[cid].get('requirements', []) for cid in ids):
                issues.append(prefix + '行为必须关联实际覆盖该需求的验收用例')
    if set(task.get('requirements', [])) - covered:
        issues.append(prefix + '并非每条需求都有行为约定')
    return issues


def verification_issues(w, p, docs, d, state, task):
    from .workflow import definitions, valid_evidence, latest_evidence
    if not required(p, task):
        return []
    c = task.get('development', {})
    ids = set(c.get('regression_cases', []))
    for behavior in c.get('behaviors', []):
        ids.update(behavior.get('cases', []))
    issues = []
    for case in definitions(d, 'cases'):
        if case['id'] not in ids:
            continue
        kind = 'check' if case['kind'] == 'auto' else 'case'
        target = case['check'] if kind == 'check' else case['id']
        valid = valid_evidence(w, p, docs, d, state, kind, target, case['repo'])
        if kind == 'check' and case.get('test_name'):
            valid = valid and (latest_evidence(d, kind, target) or {}).get('case_results', {}).get(case['id']) == 'passed'
        if not valid:
            issues.append(f"{task['id']} 的行为/保留行为用例 {case['id']} 缺少当前有效通过证据")
    return issues


def _task(workspace, req_id, target):
    from .workflow import context, definitions
    ctx = context(workspace, req_id)
    task = next((t for t in definitions(ctx[4], 'tasks') if t['id'] == target), None)
    if task is None:
        raise KitError('任务不存在')
    return ctx, task


def plan(workspace, req_id, target, expected, contract):
    from .workflow import prepare
    (w, p, local, docs, d, s), task = _task(workspace, req_id, target)
    if s['revision'] != expected:
        raise KitError('revision 冲突')
    if not isinstance(contract, dict):
        raise KitError('开发依据必须是对象')
    c = copy.deepcopy(contract)
    candidate = {**task, 'development': c}
    problems = contract_issues(w, p, d, candidate)
    if problems:
        raise KitError('；'.join(problems))
    c['reference_snapshot'] = reference_snapshot(w, p, c, must_exist=True)
    tasks = read(d/'tasks.yaml')
    for entry in tasks['tasks']:
        if entry['id'] == target:
            entry['development'] = c
    return prepare(w, s['id'], expected, {'artifacts': {'tasks.yaml': tasks}})


def inspect(workspace, req_id, target):
    from .workflow import code_files
    (w, p, local, docs, d, s), task = _task(workspace, req_id, target)
    entry = s.get('tasks', {}).get(target, {})
    current = code_files(w, p, docs, task['repo'])
    before = entry.get('files_before', {})
    changed = sorted(k for k in before.keys() | current.keys() if before.get(k) != current.get(k)) if 'files_before' in entry else []
    return {'mutates': False, 'id': s['id'], 'task': target, 'required': required(p, task),
            'contract': task.get('development'), 'contract_issues': contract_issues(w, p, d, task, entry.get('status') == 'pending'),
            'reference_changes': reference_snapshot(w, p, task.get('development', {})) != task.get('development', {}).get('reference_snapshot', []) if isinstance(task.get('development', {}), dict) else True,
            'changed_since_start': changed, 'review_issues': review_issues(w, p, docs, d, s, task),
            'next_action': '阅读实际代码差异，核对每条行为、保留行为、调用方及复用/风格；本报告不代替语义审查'}


def review_issues(w, p, docs, d, state, task):
    from .workflow import code_snapshot
    from .changes import subject_fingerprint
    if not required(p, task):
        return []
    review = state.get('tasks', {}).get(task['id'], {}).get('quality_review', {})
    if not review:
        return [f"{task['id']} 缺少当前代码的需求一致性及项目适配审查；运行 quality inspect 后实际核对并记录 quality review"]
    if not isinstance(task.get('development'), dict):
        return [f"{task['id']} 缺少开发依据，不能复用旧审查"]
    try:
        refs = reference_snapshot(w, p, task['development'])
    except KitError:
        return [f"{task['id']} 审查参考文件失效"]
    if (review.get('code') != code_snapshot(w, p, docs, task['repo'])['tree'] or
            review.get('scope') != subject_fingerprint(d, state, 'task', task['id']) or
            review.get('references') != refs or review.get('policy') != digest(p.get('conventions', {}))):
        return [f"{task['id']} 审查已过期：代码、需求、参考或项目规范变化，需要重新核对实际差异"]
    return []


def review(workspace, req_id, target, expected, report, by):
    from .workflow import state_lock, approval_current, code_snapshot, persist, code_files
    from .changes import subject_fingerprint
    import fnmatch
    with state_lock(workspace):
        (w, p, local, docs, d, s), task = _task(workspace, req_id, target)
        if s['revision'] != expected:
            raise KitError('revision 冲突')
        if not by.strip() or not approval_current(d, s):
            raise KitError('审查需要真实审查者和当前范围确认')
        entry = s.get('tasks', {}).get(target, {})
        if entry.get('status') not in ('doing', 'done'):
            raise KitError('先开始任务，再审查实际差异')
        problems = contract_issues(w, p, d, task)
        if problems:
            raise KitError('；'.join(problems))
        if not isinstance(report, dict):
            raise KitError('审查报告必须为对象')
        for key in ('reuse', 'style', 'impact', 'regression'):
            if not isinstance(report.get(key), str) or not report[key].strip():
                raise KitError(f'审查报告缺少 {key} 的实际核对结论')
        if report.get('findings') != []:
            raise KitError('尚有审查问题或未提供 findings；先修复或走明确的范围变更，不能直接通过')
        mappings = report.get('requirements')
        if not isinstance(mappings, list):
            raise KitError('审查需要 requirements 映射')
        covered = set()
        for m in mappings:
            if not isinstance(m, dict) or m.get('id') not in task['requirements'] or any(not isinstance(m.get(k), str) or not m[k].strip() for k in ('implementation', 'evidence')):
                raise KitError('每条需求需要实际实现位置及验收依据')
            covered.add(m['id'])
        if covered != set(task['requirements']):
            raise KitError('审查未覆盖本任务全部需求')
        after = code_files(w, p, docs, task['repo'])
        before = entry['files_before']
        changed = [k for k in before.keys() | after.keys() if before.get(k) != after.get(k)]
        if any(not any(fnmatch.fnmatchcase(k, pat) for pat in task['files']) for k in changed):
            raise KitError('存在范围外修改；先核对影响并更新范围，不能记录审查通过')
        entry['quality_review'] = {'by': by, 'at': now(), 'report': copy.deepcopy(report),
                                   'code': code_snapshot(w, p, docs, task['repo'])['tree'],
                                   'scope': subject_fingerprint(d, s, 'task', target),
                                   'references': reference_snapshot(w, p, task.get('development', {})),
                                   'policy': digest(p.get('conventions', {}))}
        persist(d, s, expected, 'quality-review', {'target': target, 'by': by})
        return {'id': s['id'], 'task': target, 'revision': s['revision'], 'reviewed': True, 'note': '记录实际审查，不代表测试通过；finish 仍需验证证据'}
