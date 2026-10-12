"""Public CLI. Reading next/status never authorizes execution."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys
from . import VERSION
from . import experience
from . import testing
from . import quality
from .discovery import discover, AREAS
from .storage import KitError, read
from .workspace import KIT, install, rollback, load, config_issues
from .workflow import adopt, select, prepare, next_step, context, issues_for, mutate, run_check


def dependencies(capability):
    required = ['git']
    optional = []
    if capability == 'recording':
        required += ['asr-watch', 'ffmpeg']
    elif capability == 'browser':
        # Presence is not proof of an authenticated session. Agent verifies the actual connector at use time.
        optional = ['当前会话中可调用的浏览器工具及已授权登录态（需交互验证）']
    elif capability == 'figma':
        optional = ['当前会话中可调用的 Figma 连接器及文件访问权限（需交互验证）']
    return {'version': VERSION, 'capability': capability, 'missing': [x for x in required if not shutil.which(x)], 'interaction_checks': optional}


def parser():
    p = argparse.ArgumentParser(description='dev-ai-kit：需求状态、验证证据与下一步；不会自动提交或部署')
    p.add_argument('--version', action='version', version=VERSION)
    sub = p.add_subparsers(dest='command', required=True)
    for name in ('install', 'upgrade'):
        c = sub.add_parser(name)
        c.add_argument('--workspace', required=True)
        c.add_argument('--apply', action='store_true', help='默认仅预览；此参数应用安装/升级')
        c.add_argument('--mode', choices=('local', 'tracked', 'repo', 'share'))
        c.add_argument('--docs-repo')
        c.add_argument('--share')
        c.add_argument('--migrate-config', action='store_true', help='迁移旧配置结构并要求重新确认规范；保留旧命令，不猜测执行方式')
    c = sub.add_parser('assist', help='Agent 使用的统一意图入口；默认只读/预览')
    c.add_argument('intent', choices=('begin', 'resume', 'change', 'review'))
    c.add_argument('--workspace', required=True)
    c.add_argument('--id')
    c.add_argument('--request', default='')
    c.add_argument('--repo', default='')
    c.add_argument('--file', action='append', default=[])
    c.add_argument('--check', action='append', default=[])
    c.add_argument('--acceptance', default='')
    c.add_argument('--out-of-scope', default='')
    c.add_argument('--profile', choices=('auto', 'quick', 'standard', 'cross-system'), default='auto')
    c.add_argument('--risk', action='append', default=[])
    c.add_argument('--by', default='')
    c.add_argument('--authorization-note', default='')
    c.add_argument('--manual-acceptance', default='')
    c.add_argument('--input')
    c.add_argument('--expect', type=int)
    c.add_argument('--apply', action='store_true')
    c = sub.add_parser('quality', help='开发依据、实际差异检查与需求/项目适配审查')
    c.add_argument('action', choices=('plan', 'inspect', 'review'))
    c.add_argument('--workspace', required=True)
    c.add_argument('--id')
    c.add_argument('--target', required=True)
    c.add_argument('--expect', type=int)
    c.add_argument('--input')
    c.add_argument('--by', default='')
    c = sub.add_parser('discover', help='只读发现项目资料、过期事实和配置绑定差异')
    c.add_argument('--workspace', required=True)
    c.add_argument('--area', choices=AREAS, default='overview')
    c = sub.add_parser('cases', help='用例种子生成和规范化导入；原件由 Agent 解析')
    c.add_argument('action', choices=('draft', 'import'))
    c.add_argument('--workspace', required=True)
    c.add_argument('--id')
    c.add_argument('--repo')
    c.add_argument('--input')
    c.add_argument('--original', help='原始任意格式文件；输入包每条需 source_location')
    c.add_argument('--source', choices=('qa', 'ai'), default='qa')
    c.add_argument('--reviewed-by', default='')
    c.add_argument('--replace', action='store_true')
    c.add_argument('--expect', type=int)
    c.add_argument('--apply', action='store_true')
    c = sub.add_parser('rollback')
    c.add_argument('--workspace', required=True)
    c.add_argument('--backup', required=True)
    c = sub.add_parser('check')
    c.add_argument('--capability', choices=('core', 'recording', 'browser', 'figma'), default='core')
    for name in ('next', 'status', 'validate', 'adopt', 'select', 'prepare', 'confirm', 'change', 'block', 'start', 'finish', 'manual', 'complete', 'run'):
        c = sub.add_parser(name)
        c.add_argument('--workspace', required=True)
        c.add_argument('--id', required=name in ('adopt', 'select'))
        if name in ('next', 'status'):
            c.add_argument('--full', action='store_true')
        if name == 'validate':
            c.add_argument('--ready', action='store_true')
            c.add_argument('--all', action='store_true')
            c.add_argument('--config-only', action='store_true')
        if name == 'adopt':
            c.add_argument('--profile', choices=('quick', 'standard', 'cross-system'), default='standard')
            c.add_argument('--apply', action='store_true')
        if name in ('prepare', 'confirm', 'change', 'block', 'start', 'finish', 'manual', 'complete', 'run'):
            c.add_argument('--expect', type=int, required=True, help='从 status/next 读取的 revision，防止覆盖并发更新')
        if name == 'prepare':
            c.add_argument('--input', required=True, help='材料更新 YAML，格式见 docs/schema.md')
        if name in ('confirm', 'change', 'manual', 'complete'):
            c.add_argument('--by', required=True)
            c.add_argument('--note', required=True)
        if name == 'block':
            c.add_argument('--note', required=True, help='空字符串表示已解决；历史保留')
        if name in ('start', 'finish', 'manual'):
            c.add_argument('--target', required=True)
        if name == 'manual':
            c.add_argument('--result', choices=('passed', 'failed', 'blocked'), required=True)
        if name == 'run':
            c.add_argument('--check', required=True)
            c.add_argument('--diagnostic-log', action='store_true', help='显式保存本机受控脱敏诊断尾部；不进入需求证据目录')
            c.add_argument('--ready', action='append', default=[], help='用户授权且已验证的依赖名，可重复')
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        command = args.command
        if command == 'quality':
            if args.action == 'inspect':
                result = quality.inspect(args.workspace, args.id, args.target)
            else:
                if args.expect is None or not args.input:
                    raise KitError('quality plan/review 需要最新 --expect 与 --input')
                payload = read(args.input)
                result = quality.plan(args.workspace, args.id, args.target, args.expect, payload) if args.action == 'plan' else quality.review(args.workspace, args.id, args.target, args.expect, payload, args.by)
        elif command == 'discover':
            result = discover(args.workspace, args.area)
        elif command == 'cases':
            if args.action == 'draft':
                result = testing.draft(args.workspace, args.id, args.repo)
            else:
                if not args.input:
                    raise KitError('先由 Agent 解析原件并生成规范化用例，import 需要 --input')
                result = testing.import_cases(args.workspace, args.id, args.input, args.expect, args.source, args.reviewed_by, args.replace, args.apply, args.original)
        elif command == 'assist':
            if args.intent == 'begin':
                result = experience.begin(args.workspace, args.id, request=args.request, repo=args.repo, files=args.file, checks=args.check, acceptance=args.acceptance, out_of_scope=args.out_of_scope, profile=args.profile, risks=args.risk, by=args.by, authorization_note=args.authorization_note, manual_acceptance=args.manual_acceptance, apply=args.apply)
            elif args.intent == 'change':
                if args.expect is None or not args.input:
                    raise KitError('Agent 应先读取当前 revision 并准备更新内容；change 需要 --expect 和 --input')
                result = experience.change(args.workspace, args.id, args.expect, read(args.input), args.apply)
            else:
                result = experience.resume(args.workspace, args.id)
                if args.intent == 'review':
                    result['delivery_ready'] = result.get('phase') in ('accept', 'done')
        elif command in ('install', 'upgrade'):
            result = install(args.workspace, apply=args.apply, mode=args.mode, docs_repo=args.docs_repo, share=args.share, migrate_config=args.migrate_config)
        elif command == 'rollback':
            result = rollback(args.workspace, args.backup)
        elif command == 'check':
            result = dependencies(args.capability)
        elif command == 'adopt':
            result = adopt(args.workspace, args.id, args.profile, args.apply)
        elif command == 'select':
            result = select(args.workspace, args.id)
        elif command == 'prepare':
            result = prepare(args.workspace, args.id, args.expect, read(args.input))
        elif command in ('next', 'status'):
            result = next_step(args.workspace, args.id)
            if command == 'status' or args.full:
                try:
                    w, p, local, docs, d, state = context(args.workspace, args.id)
                    result['state'] = state
                except KitError:
                    pass
            elif 'tasks' in result:
                result['task_counts'] = {status: sum(t['status'] == status for t in result['tasks']) for status in ('pending', 'doing', 'done')}
                del result['tasks']
        elif command == 'validate':
            if args.config_only:
                problems = config_issues(args.workspace)
            elif args.all:
                w, p, local, docs, root = load(args.workspace)
                problems = config_issues(w)
                for d in sorted(root.iterdir()) if root.exists() else []:
                    if d.is_dir() and not d.name.startswith('.'):
                        try:
                            problems += [f'{d.name}: {x}' for x in issues_for(w, d.name, args.ready)]
                        except KitError as error:
                            problems.append(f'{d.name}: {error}')
            else:
                w, p, local, docs, root = load(args.workspace)
                problems = issues_for(w, args.id, args.ready) if args.id or local.get('current') else config_issues(w)
            result = {'ok': not problems, 'issues': problems}
        elif command == 'run':
            result = run_check(args.workspace, args.id, args.check, args.expect, args.ready, args.diagnostic_log)
        else:
            result = mutate(args.workspace, args.id, args.expect, command, by=getattr(args, 'by', ''), note=getattr(args, 'note', ''), target=getattr(args, 'target', ''), value=getattr(args, 'result', ''))
        # Every state-changing workflow command returns a fresh summary for the Agent to report.
        # A summary failure must never disguise a successful write or invite repeating a command.
        summary_commands = {'adopt', 'select', 'prepare', 'confirm', 'change', 'block', 'start', 'finish', 'manual', 'complete', 'run', 'quality', 'cases', 'next', 'status'}
        applied = command not in ('adopt', 'cases') or getattr(args, 'apply', False)
        include_summary = command in summary_commands and applied and not (command == 'quality' and args.action == 'inspect')
        if command == 'assist' and args.intent in ('begin', 'change') and args.apply:
            include_summary = True
        if command in ('install', 'upgrade') and args.apply:
            include_summary = True
        if include_summary:
            selected = (result.get('id') or result.get('current') or getattr(args, 'id', None)) if command != 'run' else getattr(args, 'id', None)
            if command == 'run':
                selected = result.get('requirement_id', selected)
            try:
                result['progress'] = experience.resume(args.workspace, selected)['progress']
            except (KitError, OSError, TypeError, KeyError, ValueError, AttributeError):
                result['progress'] = {'available': False, 'reason': '本次操作结果已返回，但进度摘要暂不可读；不要重复执行写入',
                                      'next': {'owner': 'agent', 'action': '重新读取状态，定位材料或配置缺口后恢复摘要'}}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get('ok') is False or result.get('missing') or result.get('result') == 'failed' else 0
    except KitError as error:
        print(json.dumps(experience.error_response(str(error)), ensure_ascii=False), file=sys.stderr)
        return 1
    except (OSError, TypeError, KeyError, ValueError, AttributeError) as error:
        # Never echo malformed configuration values or secrets in a traceback.
        print(json.dumps({'ok': False, 'error': f'配置结构或文件操作错误（{type(error).__name__}）；请按 docs/schema.md 检查字段类型与目录权限'}, ensure_ascii=False), file=sys.stderr)
        return 1
