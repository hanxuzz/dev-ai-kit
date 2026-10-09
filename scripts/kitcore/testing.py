"""Case intake, explicit test environments and fresh per-case JUnit results."""
import copy
import csv
import os
from pathlib import Path
import re
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET
from .storage import KitError, read, digest


def environment(project, check, require_secrets=False):
    name = check.get('environment')
    if not name:
        return None, {}
    spec = project.get('runtime', {}).get('environments', {}).get(name)
    if not isinstance(spec, dict) or spec.get('kind') not in ('local', 'dev'):
        raise KitError('测试 environment 必须引用已配置的 local/dev 环境')
    url = spec.get('base_url', '')
    parsed = urlsplit(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise KitError('测试 base_url 必须是无凭证、查询参数和片段的 HTTP(S) 地址')
    if spec['kind'] == 'local' and parsed.hostname not in ('localhost', '127.0.0.1', '::1'):
        raise KitError('local 测试地址必须是本机回环地址')
    if spec['kind'] == 'dev' and not str(spec.get('deployment_id', '')).strip():
        raise KitError('dev 测试必须记录实际部署版本 deployment_id；不能用本地 HEAD 冒充远端版本')
    secrets = spec.get('required_env', [])
    if not isinstance(secrets, list) or any(not isinstance(x, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', x) for x in secrets):
        raise KitError('required_env 只允许环境变量名，不写凭证值')
    if require_secrets and any(not os.environ.get(x) for x in secrets):
        raise KitError('测试所需凭证环境变量缺失；请通过已授权方式注入，不写入配置')
    return {'name': name, 'hash': digest(spec), 'kind': spec['kind'], 'deployment_id': spec.get('deployment_id', '')}, {'KIT_BASE_URL': url, 'KIT_ENVIRONMENT': name, 'KIT_ENVIRONMENT_KIND': spec['kind']}


def junit_results(path, cases):
    """No stdout, attachments or failure text from reports enters shared evidence."""
    try:
        if not path.is_file() or path.stat().st_size > 10 * 1024 * 1024:
            raise KitError('JUnit 报告缺失或超过 10 MiB')
        raw = path.read_bytes()
        try:
            xml_text = raw.decode('utf-8-sig')
        except UnicodeError as error:
            raise KitError('JUnit 报告必须使用 UTF-8 编码') from error
        if '<!DOCTYPE' in xml_text.upper() or '<!ENTITY' in xml_text.upper():
            raise KitError('JUnit 报告不能包含 DTD 或实体')
        root = ET.fromstring(raw)
    except (ET.ParseError, OSError) as error:
        raise KitError('JUnit 报告无法读取或解析') from error
    if root.tag not in ('testsuite', 'testsuites'):
        raise KitError('JUnit 根必须为 testsuite/testsuites')
    outcomes = {}
    suite_failed = any(node.find('error') is not None or node.find('failure') is not None or any(node.get(k, '0') not in ('', '0', '0.0') for k in ('errors', 'failures')) for node in root.iter() if node.tag in ('testsuite', 'testsuites'))
    failures = 0
    count = 0
    skipped = 0
    for node in root.iter('testcase'):
        count += 1
        key = f"{node.get('classname', '')}::{node.get('name', '')}"
        result = 'failed' if node.find('failure') is not None or node.find('error') is not None else 'skipped' if node.find('skipped') is not None else 'passed'
        failures += result == 'failed'
        skipped += result == 'skipped'
        outcomes.setdefault(key, []).append(result)
    mapped = {}
    for case in cases:
        records = outcomes.get(case.get('test_name'), [])
        # Duplicate names/retries are ambiguous; never select a convenient passing attempt.
        mapped[case['id']] = records[0] if len(records) == 1 else 'missing' if not records else 'ambiguous'
    ambiguous = sum(len(records) > 1 for records in outcomes.values())
    return {'cases': mapped, 'tests': count, 'failures': failures, 'skipped': skipped, 'ambiguous': ambiguous,
            'suite_failed': suite_failed, 'ok': count > 0 and not suite_failed and failures == 0 and skipped == 0 and ambiguous == 0 and all(x == 'passed' for x in mapped.values()),
            'report_sha256': digest(path)}


def draft(workspace, req_id, repo):
    from .workflow import context, definitions
    w, p, local, docs, d, s = context(workspace, req_id)
    if repo not in p['repos']:
        raise KitError('生成用例需要选择实际代码仓库')
    cases = [{'id': f"DRAFT-{r['id']}", 'title': r['title'], 'requirements': [r['id']], 'repo': repo,
              'kind': 'manual', 'steps': ['按需求描述构造前置条件，执行对应业务操作并观察结果（待细化）'],
              'expected': r['acceptance'], 'review_status': 'draft', 'origin': {'type': 'ai', 'note': '验收条件种子，尚未审阅或执行'}}
             for r in definitions(d, 'requirements')]
    return {'mutates': False, 'cases': cases, 'next_action': 'Agent 结合代码细化正常、边界和异常场景；审阅后导入，不把种子当作完整测试'}


def import_cases(workspace, req_id, path, expected=None, source='qa', reviewed_by='', replace=False, apply=False, original=None):
    from .workflow import context, definitions, prepare
    from .changes import analyze
    w, p, local, docs, d, s = context(workspace, req_id)
    if apply and s['revision'] != expected:
        raise KitError('revision 冲突；导入前读取最新状态')
    path = Path(path)
    original = Path(original) if original else path
    if not original.is_file():
        raise KitError('原始用例文件不可用；先由 Agent 获取并解析原件')
    if source not in ('qa', 'ai'):
        raise KitError('用例来源必须为 qa/ai')
    if path.suffix.lower() == '.csv':
        try:
            with path.open(encoding='utf-8-sig', newline='') as f:
                reader = csv.DictReader(f, strict=True)
                if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
                    raise KitError('CSV 表头缺失或重复')
                incoming = []
                for row in reader:
                    if None in row or any(value is None for value in row.values()):
                        raise KitError(f'CSV 第 {reader.line_num} 行列数与表头不一致；Agent 核对原件后补齐字段，不猜测缺失内容')
                    for key in ('requirements', 'steps'):
                        value = row.get(key)
                        if not isinstance(value, str):
                            raise KitError(f'CSV 第 {reader.line_num} 行缺少 {key} 列')
                        row[key] = [v.strip() for v in value.split('|') if v.strip()]
                    incoming.append(row)
        except (csv.Error, UnicodeError) as error:
            raise KitError('规范化 CSV 无法解析；Agent 请核对 UTF-8 编码、引号和列结构') from error
    elif path.suffix.lower() in ('.yaml', '.yml'):
        incoming = read(path).get('cases')
    else:
        raise KitError('核心接收规范化 CSV/YAML；Agent 请先按 flow-testing 解析原件并转换，保留原始文件与来源位置，不要求用户自行转换')
    if not isinstance(incoming, list) or not incoming:
        raise KitError('导入必须包含非空 cases 列表')
    reqs = {r['id'] for r in definitions(d, 'requirements')}
    checks = p.get('runtime', {}).get('checks', {})
    existing = read(d/'cases.yaml', {'cases': []})
    merged = {c['id']: c for c in definitions(d, 'cases')}
    ids = set()
    original_hash, normalized_hash = digest(original), digest(path)
    for raw in incoming:
        if not isinstance(raw, dict):
            raise KitError('每条用例必须是对象')
        c = copy.deepcopy(raw)
        for key in ('id', 'title', 'repo', 'kind', 'expected'):
            if not isinstance(c.get(key), str) or not c[key].strip():
                raise KitError(f'用例缺少非空 {key}')
        if c['id'] in ids:
            raise KitError('导入文件包含重复用例编号')
        ids.add(c['id'])
        if c['id'] in merged and not replace:
            raise KitError('用例编号已存在；先比较差异，明确替换时加 --replace')
        if c['repo'] not in p['repos'] or c['kind'] not in ('manual', 'auto'):
            raise KitError('用例仓库或类型无效')
        for key in ('requirements', 'steps'):
            if not isinstance(c.get(key), list) or not c[key] or any(not isinstance(v,str) or not v.strip() for v in c[key]):
                raise KitError(f'用例 {key} 必须是非空字符串列表')
        if not set(c['requirements']) <= reqs:
            raise KitError('导入用例引用未知需求，先核对映射')
        if c['kind'] == 'auto':
            check = checks.get(c.get('check'))
            if not isinstance(check, dict) or check.get('repo') != c['repo'] or check.get('report') != 'junit':
                raise KitError('自动导入用例需要同仓库、report: junit 的已有检查')
            if not isinstance(c.get('test_name'), str) or '::' not in c['test_name']:
                raise KitError('自动用例需要精确 JUnit 标识 test_name: classname::name')
        if original.resolve() != path.resolve() and (not isinstance(c.get('source_location'), str) or not c['source_location'].strip()):
            raise KitError('从任意原件转换的用例必须保留 source_location（页码、工作表/行、图片位置等）')
        c.setdefault('source_location', f'用例 {c["id"]}')
        c['review_status'] = 'reviewed' if reviewed_by.strip() else 'draft'
        c['origin'] = {'type': source, 'external_id': c.get('external_id') or c['id'], 'file_sha256': original_hash, 'normalized_sha256': normalized_hash, 'reviewed_by': reviewed_by}
        merged[c['id']] = c
    bundle = {'artifacts': {'cases.yaml': {**existing, 'cases': list(merged.values())}}}
    delta = analyze(d, s, bundle)
    result = {'mutates': apply, 'imported': sorted(ids), 'review_status': 'reviewed' if reviewed_by.strip() else 'draft', 'delta': delta}
    if apply:
        result['update'] = prepare(w, s['id'], expected, bundle)
    else:
        result['bundle'] = bundle
    return result
