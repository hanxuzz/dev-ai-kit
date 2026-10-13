"""Human-readable evidence reports; report generation never grants acceptance."""
from datetime import datetime, timezone
from html import escape
import uuid
from .storage import KitError, read, atomic, inside, now
from .workflow import context, definitions, state_lock
from .experience import resume


def timestamp(value):
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (ValueError, TypeError, AttributeError) as error:
        raise KitError('since 必须是带时区的 ISO 时间，例如 2026-10-13T09:00:00+08:00') from error
    if result.tzinfo is None:
        raise KitError('since 必须包含时区，不猜测本机时间')
    return result.astimezone(timezone.utc)


def cell(value):
    # Metadata is text, never active Markdown/HTML (including credential-bearing links).
    return escape(str(value)).replace('|', '&#124;').replace('\n', ' ').replace('\r', ' ').replace('[', '&#91;').replace(']', '&#93;').replace('`', '&#96;')


LABELS = {'passed':'通过', 'failed':'失败', 'blocked':'阻塞', 'skipped':'跳过',
          'not-run':'未执行', 'not-mapped':'缺少逐条映射', 'duplicate':'重复映射'}


def report(workspace, req_id, since, apply=False):
    start = timestamp(since)
    if start > datetime.now(timezone.utc):
        raise KitError('报告起始时间不能在未来')
    with state_lock(workspace):
        w,p,local,docs,d,s = context(workspace,req_id)
        end = now()
        snapshot = resume(w,s['id'])
        evidence = [read(path) for path in (d/'.kit/evidence').glob('*.yaml')]
        evidence.sort(key=lambda item:(timestamp(item['at']),item.get('id','')))
        current = {c['id']:c for c in snapshot.get('cases',[])}
        def in_round(e):
            return start <= timestamp(e['at']) <= timestamp(end)
        events = [e for e in evidence if in_round(e)]
        rows=[]
        counts={'executed':0,'not_executed':0,'current_passed':0}
        for case in definitions(d,'cases'):
            kind = 'check' if case.get('kind')=='auto' else 'case'
            target = case.get('check') if kind=='check' else case['id']
            history = [e for e in evidence if e.get('target_type')==kind and e.get('target')==target]
            recent = [e for e in history if in_round(e)]
            executed = bool(recent)
            counts['executed' if executed else 'not_executed']+=1
            info=current.get(case['id'],{})
            valid=info.get('current_passed',False)
            counts['current_passed']+=bool(valid)
            outcomes=[]
            for e in recent:
                value=e.get('case_results',{}).get(case['id'],'not-mapped') if case.get('test_name') else e.get('result','not-run')
                label=LABELS.get(value,value)
                if value=='passed' and e.get('result')!='passed':
                    label+='（检查整体未通过）'
                outcomes.append(label)
            status=' → '.join(outcomes) if outcomes else '本轮未执行'
            freshness='当前有效' if valid else '未通过/已失效/待审阅'
            if not executed and valid: freshness='历史证据当前适用，非本轮执行'
            last=recent[-1] if recent else (history[-1] if history else {})
            env=last.get('environment') or {}
            env_text=' / '.join(str(env.get(k,'')) for k in ('name','kind','deployment_id') if env.get(k)) or '未记录环境（不可推断）'
            mode='自动逐条' if case.get('test_name') else '自动检查级（非逐条断言）' if kind=='check' else '观察记录（人工或 Agent）'
            rows.append([case['id'],case.get('title',case['id']),', '.join(case.get('requirements',[])),case.get('expected',''),mode,env_text,status,freshness])
        lines=['# 测试报告','',f"需求：{cell(s['id'])} — {cell(s.get('title',''))}",
               f"统计区间：{cell(since)} 至 {cell(end)}（含端点）",f"状态版本：{s['revision']}；阶段：{cell(snapshot['progress']['stage'])}",'',
               f"当前定义用例 {len(rows)} 项；本轮有关联检查/观察记录 {counts['executed']} 项；本轮未执行 {counts['not_executed']} 项；当前有效通过 {counts['current_passed']} 项（可含历史证据）。",'',
               '本报告是生成时的证据快照，不代表用户已验收。期间增删的用例以当前定义展示，原始执行记录见下表；缺少环境或观察说明不能推断已完成浏览器测试。','',
               '## 用例与结果','',
               '| 用例 | 名称 | 需求 | 预期 | 方式 | 环境/部署版本 | 本轮结果序列 | 证据时效 |',
               '|---|---|---|---|---|---|---|---|']
        lines += ['| '+' | '.join(cell(v) for v in row)+' |' for row in rows]
        lines += ['', '## 本轮执行记录（包括失败和复测）','', '| 时间 | 类型/目标 | 结果 | 诊断类别 | 证据编号 |','|---|---|---|---|---|']
        for e in events:
            lines.append('| '+' | '.join(cell(v) for v in [e.get('at',''),f"{e.get('target_type','')}/{e.get('target','')}",LABELS.get(e.get('result'),e.get('result','')), (e.get('diagnostic') or {}).get('category',''),e.get('id','')])+' |')
        if not events: lines+=['','本轮没有已登记执行证据；不得据此声称测试通过。']
        lines+=['','## 待处理与下一步','',cell(snapshot['progress']['reason']),cell(snapshot['progress']['next']['action'])]
        lines += ['- '+cell(v) for v in snapshot.get('details',[])]
        lines+=['','## 实际观察与修复说明（Agent 补充）','',
                '尚未补充。请按本轮实际工具调用补充浏览器页面/操作、实际结果、缺陷与修复、重启就绪、复测范围、未执行原因，以及本机截图/录像引用。不从 passed 推断这些动作发生，不复制原始日志、令牌或客户数据。','']
        markdown='\n'.join(lines)
        result={'id':s['id'],'revision':s['revision'],'since':since,'through':end,'counts':counts,'mutates':apply,'markdown':markdown}
        if apply:
            target=inside(d,'.kit/test-reports/'+uuid.uuid4().hex+'.md')
            atomic(target,markdown)
            result['path']=str(target)
        return result
