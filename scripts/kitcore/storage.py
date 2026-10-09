"""Validated YAML, confined paths, atomic writes and optimistic concurrency."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
import yaml


class KitError(Exception):
    pass


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in result:
            raise KitError('YAML 键必须是唯一字符串，禁止重复键')
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def read(path, default=None):
    path = Path(path)
    if not path.exists():
        if default is not None:
            return default
        raise KitError(f'缺少文件：{path.name}')
    try:
        value = yaml.load(path.read_text(encoding='utf-8-sig'), Loader=UniqueLoader)
    except (yaml.YAMLError, UnicodeError) as error:
        raise KitError(f'无效 YAML：{path.name}（{type(error).__name__}）') from error
    if not isinstance(value, dict):
        raise KitError(f'{path.name} 必须是映射对象')
    return value


def atomic(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, dict):
        data = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    raw = data.encode('utf-8') if isinstance(data, str) else data
    fd, temp = tempfile.mkstemp(prefix='.kit-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def inside(root, relative):
    """Reject traversal, absolute paths, and symlinks escaping the selected root."""
    root = Path(root).resolve()
    if not isinstance(relative, str) or not relative or '\\' in relative:
        raise KitError('请使用非空的相对路径和 / 分隔符')
    p = Path(relative)
    if p.is_absolute() or ':' in relative or '..' in p.parts:
        raise KitError('路径不得为绝对路径或包含 ..')
    target = (root / p).resolve()
    if target != root and root not in target.parents:
        raise KitError('路径越出指定目录')
    return target


def identifier(value):
    if not isinstance(value, str) or not value or value.startswith('.') or value.strip() != value or any(ord(c) < 32 or c in '/\\:' for c in value):
        raise KitError('需求号必须是单个目录名')
    return value


def digest(value):
    if isinstance(value, Path):
        return hashlib.sha256(value.read_bytes()).hexdigest()
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def lock(root):
    """Local/shared-filesystem lock. Never steal a possibly live lock automatically."""
    root = Path(root)
    path = root / '.dev-ai-kit.lock'
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise KitError('工作区正在修改或上次异常退出留下锁；确认无执行进程后手工移除 .dev-ai-kit.lock') from error
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(f'pid={os.getpid()}\ntime={now()}\n')
        yield
    finally:
        path.unlink(missing_ok=True)
