"""Workspace discovery and reversible, ownership-aware installation."""
from pathlib import Path
import copy
import shutil
import subprocess
import uuid
from . import VERSION, SCHEMA
from .storage import KitError, read, atomic, inside, digest, lock, now

KIT = Path(__file__).resolve().parents[2]
MARKERS = ('.git', 'package.json', 'pom.xml', 'build.gradle', 'go.mod', 'Cargo.toml', 'pyproject.toml', 'composer.json')


def git(path, *args):
    try:
        p = subprocess.run(['git', '-C', str(path), *args], capture_output=True, timeout=15)
        return p.stdout.decode('utf-8', errors='replace').strip() if p.returncode == 0 else ''
    except (OSError, subprocess.TimeoutExpired):
        return ''


def load(workspace):
    w = Path(workspace).resolve()
    p = read(w / 'project.yaml')
    local = read(w / 'project.local.yaml')
    if p.get('schema_version', 1) not in (1, SCHEMA):
        raise KitError('不支持此 project schema_version；请升级套件')
    config = p.get('docs', {})
    mode = config.get('mode')
    if mode not in ('local', 'tracked', 'repo', 'share'):
        raise KitError('docs.mode 必须是 local/tracked/repo/share')
    base = w
    if mode == 'share':
        share = local.get('share', {}).get('path')
        if not share:
            raise KitError('share 模式缺少本机 share.path')
        base = Path(share).expanduser().resolve()
        if not base.is_dir():
            raise KitError('共享目录不可用；请先挂载或同步，不能创建替代目录')
    docs = inside(base, config.get('path', 'docs'))
    name = config.get('requirements_dir') or 'requirements'
    if '/' in name or name in ('.', '..'):
        raise KitError('requirements_dir 必须是单个目录名')
    req = inside(docs, name)
    repos = p.get('repos', {})
    if not isinstance(repos, dict) or not repos:
        raise KitError('repos 至少配置一个代码目录')
    for value in repos.values():
        path = value.get('path') if isinstance(value, dict) else value
        if not inside(w, path).is_dir():
            raise KitError(f'代码目录不存在：{path}')
    return w, p, local, docs, req


def config_issues(workspace):
    w, p, local, docs, req = load(workspace)
    issues = []
    mode = p['docs']['mode']
    root = git(docs, 'rev-parse', '--show-toplevel') if docs.exists() else ''
    if not docs.is_dir():
        issues.append('文档根不存在')
    if mode == 'local' and root:
        issues.append('local 文档不能位于 Git 仓库内；明确选择 tracked 或 share')
    if mode == 'tracked' and (not root or Path(root).resolve() != w):
        issues.append('tracked 文档必须属于当前工作区 Git 仓库')
    if mode == 'repo' and (not root or Path(root).resolve() != docs):
        issues.append('repo 文档根必须是独立 Git 仓库的根')
    kit = Path(local.get('kit', {}).get('path') or '.')
    if not (kit / 'kit.yaml').is_file():
        issues.append('本机 kit.path 无效')
    return issues


def plan_install(workspace, mode=None, docs_repo=None, share=None, migrate_config=False):
    w = Path(workspace).resolve()
    if not w.is_dir():
        raise KitError('工作区不存在')
    if w == KIT or w in KIT.parents:
        raise KitError('套件必须位于业务工作区外部')
    changes, kept = {}, []
    project_file = w / 'project.yaml'
    if project_file.exists():
        p = read(project_file)
        if mode and mode != p.get('docs', {}).get('mode'):
            raise KitError('已有 docs.mode 与参数不同；先迁移文档并编辑配置')
        if docs_repo and docs_repo != p.get('docs', {}).get('path'):
            raise KitError('已有 docs.path 与参数不同')
        if p.get('schema_version', 1) > SCHEMA:
            raise KitError('不能降级较新的配置')
        # Existing user config is kept byte-for-byte; upgrade never guesses runtime or policy.
        if migrate_config and p.get('schema_version', 1) < SCHEMA:
            p = copy.deepcopy(p)
            p['schema_version'] = SCHEMA
            p.setdefault('runtime', {}).setdefault('checks', {})
            conv = p.setdefault('conventions', {})
            branch = conv.setdefault('branch', {})
            branch.setdefault('mode', 'feature' if branch.get('enabled') is True else 'project')
            branch.setdefault('auto_create', False)
            branch.setdefault('allowed_pattern', '')
            conv['confirmed'] = False
            changes[project_file] = p
        else:
            kept.append('project.yaml')
    else:
        children = {d.name: d.name for d in sorted(w.iterdir()) if d.is_dir() and not d.name.startswith('.') and d.name not in ('node_modules', 'dist', 'target') and any((d / m).exists() for m in MARKERS)}
        if not children and any((w / m).exists() for m in MARKERS):
            children = {'app': '.'}
        if not children:
            raise KitError('没有识别到代码仓；先提供已有代码目录')
        independent_docs = git(w / 'docs', 'rev-parse', '--show-toplevel')
        has_docs_repo = independent_docs and Path(independent_docs).resolve() == w / 'docs'
        mode = mode or ('repo' if docs_repo or has_docs_repo else 'tracked' if git(w, 'rev-parse', '--show-toplevel') else 'share' if share else 'local')
        docpath = docs_repo or 'docs'
        children.pop(docpath, None)
        if not children and any((w / m).exists() for m in MARKERS):
            children = {'app': '.'}
        if not children:
            raise KitError('文档库之外至少需要一个代码目录')
        p = read(KIT / 'templates/project.yaml')
        p.update(schema_version=SCHEMA, project=w.name, repos=children)
        p['docs'].update(mode=mode, path=docpath)
        candidate = inside(Path(share).resolve() if mode == 'share' and share else w, docpath)
        if (candidate / 'requirement').is_dir() and not (candidate / 'requirements').exists():
            p['docs']['requirements_dir'] = 'requirement'
        changes[project_file] = p
    local_file = w / 'project.local.yaml'
    if local_file.exists():
        local = read(local_file)
        kept.append('project.local.yaml')
    else:
        local = {'kit': {'path': KIT.as_posix()}, 'share': {'path': str(Path(share).resolve()) if share else ''}, 'current': ''}
        changes[local_file] = local
    base = w
    mode = p['docs']['mode']
    if mode == 'share':
        share_path = local.get('share', {}).get('path')
        if not share_path or not Path(share_path).is_dir():
            raise KitError('共享目录未配置或不可用；安装前请先准备目录')
        base = Path(share_path).resolve()
    docs = inside(base, p['docs']['path'])
    # Validate placement before any writes, including partially initialized workspaces.
    ancestor = docs
    while not ancestor.exists():
        ancestor = ancestor.parent
    gitroot = git(ancestor, 'rev-parse', '--show-toplevel')
    if mode == 'local' and gitroot:
        raise KitError('local 模式不能写入 Git 仓库内部')
    if mode == 'tracked' and (not gitroot or Path(gitroot).resolve() != w):
        raise KitError('tracked 模式需要工作区 Git 仓库')
    if mode == 'repo' and (not gitroot or Path(gitroot).resolve() != docs):
        raise KitError('repo 模式需要已有的独立文档 Git 仓库')
    for src in (KIT / 'templates/team').glob('*.md'):
        dest = docs / 'team' / src.name
        if not dest.exists():
            changes[dest] = src.read_bytes()
    if not docs.exists() or not any(docs.iterdir()):
        changes[docs / 'README.md'] = (KIT / 'templates/docs-readme.md').read_bytes()
    manifest_path = w / '.dev-ai-kit/install.yaml'
    manifest = read(manifest_path, {})
    target = w / '.cursor/rules/dev-ai-kit.mdc'
    src = KIT / 'rules/dev-ai-kit.mdc'
    if not target.exists() or digest(target) == manifest.get('rule_hash'):
        if not target.exists() or digest(target) != digest(src):
            changes[target] = src.read_bytes()
    else:
        kept.append('.cursor/rules/dev-ai-kit.mdc（用户修改或旧版未登记；已提供候选）')
        proposed = w / '.dev-ai-kit/dev-ai-kit.mdc.proposed'
        if not proposed.exists() or digest(proposed) != digest(src):
            changes[proposed] = src.read_bytes()
    ignore = w / '.gitignore'
    content = ignore.read_text(encoding='utf-8') if ignore.exists() else ''
    entries = ['project.local.yaml', '/.dev-ai-kit/', '/.dev-ai-kit.lock', '/.cursor/next-step.txt']
    existing = content.splitlines()
    missing = [x for x in entries if x not in existing]
    if missing:
        changes[ignore] = content.rstrip('\n') + '\n# dev-ai-kit\n' + '\n'.join(missing) + '\n'
    # The manifest only owns the current rule if installation will actually supply it.
    owned_hash = digest(src) if target in changes else manifest.get('rule_hash', '')
    updated_manifest = {'version': VERSION, 'schema_version': SCHEMA, 'rule_hash': owned_hash}
    if manifest != updated_manifest:
        changes[manifest_path] = updated_manifest
    return w, changes, kept


def install(workspace, apply=False, **options):
    w, changes, kept = plan_install(workspace, **options)
    result = {'action': 'install', 'apply': apply, 'changes': [str(x.relative_to(w)) if w in x.parents else str(x) for x in changes], 'kept': kept}
    if not apply or not changes:
        return result
    with lock(w):
        # Recalculate inside the lock before collecting reversible snapshots.
        w, changes, kept = plan_install(workspace, **options)
        tx = w / '.dev-ai-kit/backups' / uuid.uuid4().hex
        tx.mkdir(parents=True)
        records = []
        for index, (path, value) in enumerate(changes.items()):
            backup = tx / str(index)
            existed = path.exists()
            if existed:
                shutil.copy2(path, backup)
            records.append({'path': str(path), 'backup': str(backup), 'existed': existed})
        journal = {'created_at': now(), 'state': 'pending', 'files': records}
        atomic(tx / 'journal.yaml', journal)
        try:
            for path, value in changes.items():
                atomic(path, value)
            for record in records:
                record['after'] = digest(Path(record['path']))
            journal['state'] = 'applied'
            atomic(tx / 'journal.yaml', journal)
        except BaseException:
            for record in reversed(records):
                path = Path(record['path'])
                if record['existed']:
                    atomic(path, Path(record['backup']).read_bytes())
                else:
                    path.unlink(missing_ok=True)
            journal['state'] = 'rolled-back'
            atomic(tx / 'journal.yaml', journal)
            raise
        result['backup'] = tx.name
    return result


def rollback(workspace, backup):
    w = Path(workspace).resolve()
    tx = inside(w / '.dev-ai-kit/backups', backup)
    with lock(w):
        j = read(tx / 'journal.yaml')
        if j['state'] != 'applied':
            raise KitError('此备份不是可回退的已完成安装')
        for record in j['files']:
            path = Path(record['path'])
            if not path.exists() or digest(path) != record['after']:
                raise KitError('安装后文件已被修改，拒绝覆盖；请人工合并备份')
        for record in reversed(j['files']):
            path = Path(record['path'])
            if record['existed']:
                atomic(path, Path(record['backup']).read_bytes())
            else:
                path.unlink()
        j['state'] = 'rolled-back'
        atomic(tx / 'journal.yaml', j)
    return {'rolled_back': backup}
