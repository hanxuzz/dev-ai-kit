"""Explain material changes and conservatively limit their invalidation radius."""
import copy
from .storage import KitError, read, inside, digest

NAMES = ('requirements', 'tasks', 'cases')



def material_snapshot(directory, state):
    result = {'profile': state.get('profile'), 'sources': copy.deepcopy(state.get('sources', {})), 'definitions': {}}
    for name in NAMES:
        result['definitions'][name] = read(directory / f'{name}.yaml', {name: []})
    return result


def indexed(obj, name):
    items = obj.get(name, [])
    if not isinstance(items, list) or any(not isinstance(x, dict) or not isinstance(x.get('id'), str) for x in items):
        raise KitError(f'{name} 必须是有 id 的对象列表')
    if len({x['id'] for x in items}) != len(items):
        raise KitError(f'{name} 编号重复')
    return {x['id']: x for x in items}


def analyze(directory, state, bundle):
    fields = bundle.get('state', {})
    artifacts = bundle.get('artifacts', {})
    before = material_snapshot(directory, state)
    after = copy.deepcopy(before)
    after.update({k: fields[k] for k in ('profile', 'sources') if k in fields})
    changed_documents = []
    layout_only = True
    for path, content in artifacts.items():
        dest = inside(directory, path)
        if path in {f'{name}.yaml' for name in NAMES}:
            if not isinstance(content, dict):
                raise KitError('结构化定义更新必须使用 YAML 对象，不接受文本字符串')
            after['definitions'][path[:-5]] = content
        else:
            old = dest.read_text(encoding='utf-8') if dest.is_file() else ''
            if not isinstance(content, str):
                raise KitError('Markdown 更新必须是字符串')
            if old != content:
                changed_documents.append(path)
                layout_only &= bool(dest.is_file()) and old == content
    changed = {}
    old_maps, new_maps = {}, {}
    for name in NAMES:
        old_maps[name] = indexed(before['definitions'][name], name)
        new_maps[name] = indexed(after['definitions'][name], name)
        changed[name] = sorted(k for k in set(old_maps[name]) | set(new_maps[name]) if old_maps[name].get(k) != new_maps[name].get(k))
    global_change = any(before.get(k) != after.get(k) for k in ('profile', 'sources'))
    global_change |= any(k in fields and fields[k] != state.get(k) for k in ('files', 'questions'))
    for name in NAMES:
        old_meta = {k: v for k, v in before['definitions'][name].items() if k != name}
        new_meta = {k: v for k, v in after['definitions'][name].items() if k != name}
        global_change |= old_meta != new_meta
    requested = bundle.get('change_kind', 'auto')
    if requested not in ('auto', 'editorial', 'broad'):
        raise KitError('change_kind 必须是 auto/editorial/broad')
    semantic_change = global_change or any(changed.values())
    if requested == 'editorial':
        if semantic_change or not bundle.get('reason', '').strip():
            raise KitError('editorial 仅允许已核对的不改业务含义的文字修改，并需 reason；不能改变结构化范围/任务/验收/来源')
        kind = 'editorial'
    elif requested == 'broad' or global_change:
        kind = 'broad'
    elif semantic_change:
        kind = 'scoped'
    elif layout_only:
        kind = 'editorial' if changed_documents else 'none'
    else:
        kind = 'broad'  # Prose changed without structured mapping: impact is unknown.
    from .workflow import approval_current
    unapproved = not approval_current(directory, state)
    if unapproved and (artifacts or kind in ('broad', 'scoped')):
        kind = 'broad'
    all_tasks = {**old_maps['tasks'], **new_maps['tasks']}
    task_versions = [*old_maps['tasks'].values(), *new_maps['tasks'].values()]
    affected_requirements = set(changed['requirements'])
    for cid in changed['cases']:
        for mapping in (old_maps['cases'], new_maps['cases']):
            affected_requirements.update(mapping.get(cid, {}).get('requirements', []))
    affected = set(changed['tasks'])
    for task in task_versions:
        if affected_requirements.intersection(task.get('requirements', [])):
            affected.add(task['id'])
    while True:
        more = {t['id'] for t in task_versions if affected.intersection(t.get('depends_on', []))}
        if more <= affected:
            break
        affected |= more
    if kind == 'broad':
        affected = set(all_tasks)
    if kind in ('none', 'editorial'):
        affected = set()
    checks = sorted({check for tid in affected for check in all_tasks.get(tid, {}).get('checks', [])})
    return {'kind': kind, 'changed': changed, 'documents': changed_documents,
            'affected_tasks': sorted(affected), 'preserved_tasks': sorted(set(all_tasks) - affected), 'checks_to_repeat': checks,
            'reason': ('没有有效的旧确认，复核当前全部材料' if unapproved and kind == 'broad' else bundle.get('reason')) or ('仅排版变化' if kind == 'editorial' else '来源/约束或未映射正文变化，保守复核' if kind == 'broad' else '按需求映射及任务依赖计算'),
            'confirmation_required': kind in ('broad', 'scoped')}


def subject_fingerprint(directory, state, kind, target):
    """Evidence follows the definitions relevant to its task/case/check, not all prose."""
    snapshot = material_snapshot(directory, state)
    reqs = indexed(snapshot['definitions']['requirements'], 'requirements')
    tasks = indexed(snapshot['definitions']['tasks'], 'tasks')
    cases = indexed(snapshot['definitions']['cases'], 'cases')
    task_ids = {target} if kind == 'task' else {tid for tid, t in tasks.items() if kind == 'check' and target in t.get('checks', [])}
    case_ids = {target} if kind == 'case' else {cid for cid, c in cases.items() if kind == 'check' and c.get('check') == target}
    while True:
        deps = {dep for tid in task_ids for dep in tasks.get(tid, {}).get('depends_on', [])}
        if deps <= task_ids:
            break
        task_ids |= deps
    relevant_tasks = {tid: tasks.get(tid) for tid in sorted(task_ids)}
    relevant_cases = {cid: cases.get(cid) for cid in sorted(case_ids)}
    req_ids = {rid for value in [*relevant_tasks.values(), *relevant_cases.values()] if value for rid in value.get('requirements', [])}
    relevant_reqs = {rid: reqs.get(rid) for rid in sorted(req_ids)}
    source_ids = {sid for r in relevant_reqs.values() if r for sid in r.get('sources', [])}
    sources = {sid: copy.deepcopy(state.get('sources', {}).get(sid)) for sid in sorted(source_ids)}
    for source in sources.values():
        if source and source.get('path'):
            file = inside(directory, source['path'])
            source['sha256'] = digest(file) if file.is_file() else 'missing'
    return digest({'id': state['id'], 'epoch': state.get('evidence_epoch', 0), 'tasks': relevant_tasks, 'cases': relevant_cases,
                   'requirements': relevant_reqs, 'sources': sources, 'constraints': {k:v for k,v in snapshot['definitions']['requirements'].items() if k != 'requirements'}})
