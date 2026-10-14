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
        cases = definitions(d,'cases')
        for case in cases:
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
        lines+=['', '## 总结与交付检查（Agent 补充）', '',
                '状态：待补充实际观察与证据，不能作为完整交付。测试轮不修复。',
                '补充环境/版本、范围、实际通过/失败/阻塞/跳过/未执行数量、主要问题、停止原因和下一步。逐条结果数量须与原件对账。',
                '', '## 原始用例与追溯', '',
                '以下是当前定义的来源索引，不是原件备份。Agent 必须附最原始文件的受控引用或经允许保存的原件，核对 SHA-256、原件总数、导入数及遗漏原因；不可访问明确标缺失。AI 生成用例标明来源，不伪称测试人员原件。', '',
                '| 用例 | 原始编号 | 来源位置 | 原件 SHA-256 | 来源类型 |',
                '|---|---|---|---|---|']
        for case in cases:
            origin = case.get('origin') or {}
            lines.append('| '+' | '.join(cell(v) for v in [case['id'], origin.get('external_id', '未记录'), case.get('source_location', '未记录'), origin.get('file_sha256', '未记录'), origin.get('type', '未记录')])+' |')
        lines+=['', '## 实际操作步骤（Agent 补充）', '',
                '| 用例/步骤序号 | 实际时间 | 页面/前置 | 实际操作与安全测试数据引用 | 预期 | 实际结果 | 状态及未执行原因 | 证据/问题编号 |',
                '|---|---|---|---|---|---|---|---|', '',
                '尚未补充。按真实工具调用填写，不能把计划步骤当实际操作。逐条关联上方用例；原件未解析或未导入项也须列出并解释，不能只汇报已运行项。',
                '', '## 全程录像与问题截图（Agent 补充）', '',
                '| 文件/受控引用 | 类型 | 会话/分段 | 起止时间及覆盖用例 | 问题相对时间 | 可播放/可读核对 | 缺口 |',
                '|---|---|---|---|---|---|---|', '',
                '尚未补充。浏览器测试前开始全程录屏，问题立即截图；所有成功和失败场景均保留。多段分别核对偏移；缺能力或录制中断停止后续浏览器操作并报告，不能用日志代替录像。纯单元/API 测试填写不适用及原因。',
                '', '## 问题分析（Agent 补充）', '',
                '| 问题/用例 | 复现/预期与实际 | 严重程度及影响 | 模块/前端/后端/接口契约/数据/环境/未知 | 已验证原因 | 推测及证据/待验证方法 | 截图与录像时间点 | 跳过/阻塞及理由 | 后续建议 |',
                '|---|---|---|---|---|---|---|---|---|', '',
                '尚未补充，不表示没有问题。仅凭页面错误不能归因前端，仅凭 HTTP 500 不能确定根因；跨层问题列出相关层及证据，证据不足写未知。只读分析，不执行修复建议。',
                '', '## 完整性核对（Agent 补充）', '',
                '逐项核对：总结、原始用例及对账、每条结果与实际步骤、全程录像、问题截图和时间点、原因归属及不确定性、停止/未执行原因。补齐并验证受控引用可用后才能标交付完整；缺项保留待补充/阻塞，不自动判定验收通过。原件含敏感数据时保留受控原件，报告仅提供安全引用，不复制密码、令牌或客户数据。', '']
        markdown='\n'.join(lines)
        result={'id':s['id'],'revision':s['revision'],'since':since,'through':end,'counts':counts,'mutates':apply,'markdown':markdown}
        if apply:
            target=inside(d,'.kit/test-reports/'+uuid.uuid4().hex+'.md')
            atomic(target,markdown)
            result['path']=str(target)
        return result
