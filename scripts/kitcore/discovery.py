"""Read-only project discovery: evidence candidates are not verified project facts."""
from .storage import KitError, read, inside, digest
from .workspace import load

AREAS = ('overview', 'conventions', 'development', 'testing', 'environments', 'business')
PATTERNS = ('AGENTS.md', 'README*', 'CONTRIBUTING*', 'package.json', 'package-lock.json', 'pnpm-lock.yaml', 'yarn.lock', 'poetry.lock', 'uv.lock', 'Cargo.lock', 'go.sum', 'pyproject.toml', 'pytest.ini',
            'pom.xml', 'build.gradle*', 'Makefile', 'compose*.y*ml', 'docker-compose*.y*ml',
            'playwright.config.*', 'vitest.config.*', '.github/workflows/*.y*ml', '.cursor/rules/*.mdc',
            'docs/README*', 'docs/*test*.md', 'docs/*develop*.md')


def discover(workspace, area='overview'):
    if area not in AREAS:
        raise KitError('未知项目上下文领域')
    w, p, local, docs, _ = load(workspace)
    candidates = []
    seen = set()
    roots = [('workspace', w)] + [(name, inside(w, value['path'] if isinstance(value, dict) else value)) for name, value in p['repos'].items()]
    for repo, root in roots:
        count = 0
        for pattern in PATTERNS:
            for file in sorted(root.glob(pattern)):
                relative = file.relative_to(root).as_posix()
                try:
                    resolved = inside(root, relative)
                except KitError:
                    continue
                if not resolved.is_file() or resolved in seen:
                    continue
                seen.add(resolved)
                candidates.append({'repo': repo, 'path': relative, 'sha256': digest(resolved)})
                count += 1
                if count >= 60:
                    break
            if count >= 60:
                break
    profile = read(docs/'team/project-context.yaml', {'facts': []})
    if profile.get('schema_version', 1) != 1:
        raise KitError('不支持此项目上下文 schema_version')
    facts = profile.get('facts', [])
    if not isinstance(facts, list):
        raise KitError('project-context.facts 必须是列表')
    result = []
    ids = set()
    for fact in facts:
        if not isinstance(fact, dict) or not isinstance(fact.get('id'), str) or fact['id'] in ids:
            raise KitError('项目事实必须有唯一 id')
        ids.add(fact['id'])
        if area != 'overview' and fact.get('area') != area:
            continue
        problems = []
        status = fact.get('status', 'unknown')
        if status == 'verified' and any(not fact.get(k) for k in ('value', 'verified_by', 'verification')):
            problems.append('已核实事实缺少值、核实者或核实方法')
        if status == 'not-applicable' and not fact.get('reason'):
            problems.append('不适用必须说明原因')
        if status not in ('verified', 'inferred', 'unknown', 'conflict', 'not-applicable'):
            problems.append('状态无效')
        if status != 'verified' and status != 'not-applicable':
            problems.append('未核实或存在冲突')
        sources = fact.get('sources', [])
        if not isinstance(sources, list) or not sources:
            problems.append('缺少来源依据')
            sources = []
        for source in sources:
            if not isinstance(source, dict):
                problems.append('来源格式无效'); continue
            if source.get('kind') == 'file':
                value = p['repos'].get(source.get('repo'))
                root = w if source.get('repo') == 'workspace' else inside(w, value['path'] if isinstance(value, dict) else value) if value else None
                if not root:
                    problems.append('来源仓库不存在'); continue
                file = inside(root, source.get('path'))
                if not file.is_file() or digest(file) != source.get('sha256'):
                    problems.append('来源文件已变化或缺失')
            elif source.get('kind') in ('external', 'user', 'observation'):
                if not source.get('reference') or not source.get('checked_at'):
                    problems.append('非文件来源缺少引用或核实时间')
                if source.get('kind') in ('external', 'observation'):
                    problems.append('动态来源需在本次相关操作前复核')
            else:
                problems.append('未知来源类型')
        binding = fact.get('binding')
        if binding:
            if not isinstance(binding, list) or any(not isinstance(k,str) for k in binding):
                raise KitError('binding 必须是 project.yaml 键路径数组')
            value = p
            for key in binding:
                value = value.get(key) if isinstance(value, dict) else None
            if value is None or digest(value) != fact.get('applied_sha256'):
                problems.append('应用到项目配置的值已变化或缺失')
        result.append({'id': fact['id'], 'area': fact.get('area'), 'status': status, 'issues': problems,
                       'usable_record': not problems})
    checks = p.get('runtime', {}).get('checks', {})
    envs = p.get('runtime', {}).get('environments', {})
    bindings = [{'path': ['runtime', 'checks', name], 'sha256': digest(spec)} for name,spec in checks.items()]
    bindings += [{'path': ['runtime', 'environments', name], 'sha256': digest(spec)} for name,spec in envs.items()]
    bindings.append({'path': ['conventions'], 'sha256': digest(p.get('conventions', {}))})
    return {'mutates': False, 'area': area, 'candidates': candidates, 'facts': result, 'bindings': bindings,
            'collection_needed': not result or any(not item['usable_record'] for item in result),
            'next_action': 'Agent 读取与当前操作相关的原件，核实并应用项目配置；候选文件、指纹和历史记录不等于内容已读或命令已验证'}
