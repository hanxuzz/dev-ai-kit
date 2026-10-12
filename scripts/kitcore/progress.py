"""Small, factual progress summaries; these never grant execution permission."""
LABELS = {'select': '选择需求', 'adopt': '接管已有需求', 'prepare': '准备开发依据',
          'questions': '澄清业务问题', 'confirm': '核对需求范围', 'conventions': '核对项目规范',
          'build': '开发中', 'blocked': '处理阻塞', 'test': '补齐验证与审查',
          'accept': '等待验收', 'done': '需求已验收完成'}


def summarize(snapshot, task_states=(), history=()):
    phase = snapshot['phase']
    counts = {key: sum(t.get('status', 'pending') == key for t in task_states) for key in ('pending', 'doing', 'done')}
    counts['total'] = len(task_states)
    cases = snapshot.get('cases', [])
    checks = snapshot.get('verification', [])
    quality = [q for q in snapshot.get('development_quality', []) if q['required']]
    current_cases = sum(c.get('current_passed', False) for c in cases)
    current_checks = sum(c['state'] == 'current' for c in checks)
    current_reviews = sum(not q['issues'] for q in quality)
    issues = snapshot.get('details', [])
    reasons = {
        'select': '尚未选定需求，不能推断你要继续哪一项。',
        'adopt': '已有资料尚未接入当前进度，需要先核对原件。',
        'prepare': '开发依据或验收映射还有缺口。',
        'questions': '有影响实现的业务问题尚未澄清。',
        'confirm': '当前范围尚无有效确认，需核对新增决定与已有授权。',
        'conventions': '项目规范或分支条件尚未满足。',
        'build': '仍有开发任务未完成；是否继续取决于本次请求的授权范围。',
        'blocked': '当前存在阻塞，需先判断原因和可恢复方式。',
        'test': '实现已登记完成，但验证或审查尚未齐全或已过期。',
        'accept': '实现、验证与必要审查已齐，尚待你接受交付。',
        'done': '本需求已验收结束；提交、推送和部署状态需另行核实。',
    }
    actions = {
        'select': ('user', '选择要继续的需求，或描述一个新需求。', '继续处理〔需求名称〕。'),
        'adopt': ('agent_then_user', '先核对已有规格与计划，说明接管范围；需要接管授权时再写入。', '接管这条需求，保留原材料。'),
        'prepare': ('agent', '先根据已有代码和资料补齐缺口，无法查清的业务决定再询问。', None),
        'questions': ('user', '回答 Agent 列出的具体业务问题，再继续受影响的工作。', None),
        'confirm': ('agent_then_user', '对照原始请求核对变化，只将尚未授权的业务决定交给你确认。', None),
        'conventions': ('agent', '核对既有项目规范和分支；只有存在真实冲突才请你选择。', None),
        'build': ('agent', snapshot.get('next_action', '继续当前任务'), '继续完成已确认范围内的任务。'),
        'blocked': ('agent', '先定位阻塞；需要账号、资料或业务决定时明确说明由谁提供。', None),
        'test': ('agent', '补齐失效或缺失的检查、人工验收与代码审查，然后重新检查交付。', '继续补齐验证和审查，说明剩余风险。'),
        'accept': ('user', '查看本轮结果与验收说明；实际验收通过后明确接受，发现偏差则指出。', '本轮结果已验收，标记完成。'),
        'done': ('user', '本需求无需继续开发；可选择下一条需求，或明确要求提交、推送或发布。', None),
    }
    owner, action, reply = actions[phase]
    failed_checks = [c['check'] for c in checks if c['state'] == 'failed']
    if phase in ('build', 'test') and failed_checks:
        action = '先诊断失败检查：' + '、'.join(failed_checks) + '；修复后重跑，再核对剩余工作。'
    elif phase == 'build' and snapshot.get('in_progress') and checks and current_checks == len(checks):
        action = '当前检查已通过；核对实际差异、需求及回归覆盖，补齐代码审查后登记任务完成。'
    summary = f"{LABELS[phase]}；任务已完成 {counts['done']}/{counts['total']}" if counts['total'] else f'{LABELS[phase]}；尚未形成任务计划'
    progress = {'available': True, 'id': snapshot.get('id'), 'title': snapshot.get('title'),
                'stage': LABELS[phase], 'summary': summary, 'tasks': counts,
                'verification': {'checks_current': current_checks, 'checks_total': len(checks),
                                 'cases_current': current_cases, 'cases_total': len(cases),
                                 'reviews_current': current_reviews, 'reviews_total': len(quality)},
                'current_tasks': [t['title'] for t in snapshot.get('in_progress', [])],
                'recent_completed': snapshot.get('completed', [])[-3:],
                'verification_gaps': [{'check': c['check'], 'state': c['state'], 'next_action': c['next_action']} for c in checks if c['state'] != 'current'],
                'reason': reasons[phase], 'remaining': issues[:5], 'remaining_count': len(issues),
                'next': {'owner': owner, 'action': action, 'reply_example': reply},
                'delivery': {'accepted': phase == 'done', 'git_and_deployment': 'not_inspected'},
                'read_only': True, 'grants_execution_permission': False}
    if history:
        last = history[-1]
        # This is a recorded event, not a claim that all work happened in this conversation.
        progress['latest_record'] = {'event': last.get('event'), 'at': last.get('at')}
    return progress
