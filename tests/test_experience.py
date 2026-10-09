"""Developer journeys with real temporary Git workspaces and child commands."""
import copy
import json
import subprocess
import sys
import unittest
import test_workflow as fixtures
from kitcore.experience import begin, resume, change
from kitcore.workflow import prepare, run_check, next_step, valid_evidence, context
from kitcore.storage import read, atomic, KitError
from kitcore.workspace import KIT


class ExperienceTests(unittest.TestCase):
    setUp = fixtures.WorkspaceCase.setUp
    state = fixtures.WorkspaceCase.state
    mutate = fixtures.WorkspaceCase.mutate
    bundle = fixtures.WorkspaceCase.bundle
    ready = fixtures.WorkspaceCase.ready
    run_unit = fixtures.WorkspaceCase.run_unit
    finish_auto = fixtures.WorkspaceCase.finish_auto

    def quick(self, **overrides):
        args = dict(request='把提示文案改为已保存', repo='ui', files=['src/app.py'], checks=['unit'],
                    acceptance='保存后显示已保存', out_of_scope='不改变保存逻辑', apply=True)
        args.update(overrides)
        return begin(self.w, 'REQ-copy', **args)

    def test_preview_has_no_side_effect_and_cli_supports_intent(self):
        result = self.quick(apply=False)
        self.assertEqual(result['profile'], 'quick')
        self.assertFalse((self.d.parent / 'REQ-copy').exists())
        p = subprocess.run([sys.executable, str(KIT/'scripts/kit.py'), 'assist', 'begin', '--workspace', str(self.w), '--id', 'REQ-cli', '--request', '修改提示文案', '--file', 'src/app.py'], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertFalse(json.loads(p.stdout)['mutates'])
        self.assertFalse((self.d.parent/'REQ-cli').exists())

    def test_quick_reuses_real_authorization_but_does_not_start_code(self):
        result = self.quick(by='requester', authorization_note='原始请求：请把提示文案改为已保存，并验证')
        self.assertEqual(result['result']['phase'], 'build')
        self.assertTrue(result['result']['authorization']['valid_for_current_scope'])
        s = read(self.d.parent/'REQ-copy/status.yaml')
        self.assertFalse(any(t['status'] == 'doing' for t in s['tasks'].values()))
        self.assertEqual((self.repo/'src/app.py').read_text(), 'value = 1\n')

    def test_quick_without_authorization_stops_at_confirmation(self):
        self.assertEqual(self.quick()['result']['phase'], 'confirm')

    def test_manual_quick_and_risk_upgrade(self):
        result = self.quick(checks=[], manual_acceptance='实际保存后观察提示文字', by='requester', authorization_note='明确请求修改并验证')
        self.assertEqual(result['result']['phase'], 'build')
        result = begin(self.w, 'REQ-risk', request='修改权限提示文案', repo='ui', files=['src/app.py'], profile='quick')
        self.assertEqual(result['profile'], 'cross-system')

    def test_existing_material_is_not_overwritten(self):
        target = self.d.parent/'REQ-copy'
        target.mkdir()
        original = target/'brief.md'
        original.write_text('existing')
        with self.assertRaisesRegex(KitError, '已有材料'):
            self.quick()
        self.assertEqual(original.read_text(), 'existing')

    def test_resume_explains_drift_without_writing_or_restarting(self):
        self.ready()
        self.mutate('start', target='TASK-1')
        (self.repo/'src/app.py').write_text('value = 2\n')
        before = (self.d/'status.yaml').read_bytes()
        result = resume(self.w)
        self.assertTrue(result['in_progress'][0]['code_changed_since_start'])
        self.assertEqual(result['verification'][0]['state'], 'not-run')
        self.assertFalse(result['needs_decision'])
        self.assertEqual((self.d/'status.yaml').read_bytes(), before)

    def test_editorial_retains_completed_task_and_evidence(self):
        self.finish_auto()
        result = change(self.w, None, self.state()['revision'], {'change_kind':'editorial', 'reason':'仅纠正标题错字，业务含义不变', 'artifacts': {'Existing Spec.md': (self.d/'Existing Spec.md').read_text().replace('原有规格', '既有规格')}}, apply=True)
        self.assertEqual(result['update']['delta']['kind'], 'editorial')
        self.assertEqual(self.state()['tasks']['TASK-1']['status'], 'done')
        self.assertEqual(next_step(self.w)['phase'], 'accept')

    def test_editorial_cannot_hide_structured_scope_change(self):
        self.ready()
        defs = read(self.d/'requirements.yaml')
        defs['requirements'][0]['acceptance'] = '值为 3'
        with self.assertRaisesRegex(KitError, 'editorial'):
            change(self.w, None, self.state()['revision'], {'change_kind':'editorial', 'reason':'typo', 'artifacts': {'requirements.yaml': defs}}, apply=True)
        self.assertEqual(read(self.d/'requirements.yaml')['requirements'][0]['acceptance'], '给定默认配置，当读取值，则为 2')

    def test_unknown_prose_change_is_broad_including_markdown_whitespace(self):
        self.finish_auto()
        result = change(self.w, None, self.state()['revision'], {'artifacts': {'Existing Spec.md': (self.d/'Existing Spec.md').read_text()+'\n'}}, apply=True)
        self.assertEqual(result['delta']['kind'], 'broad')
        self.assertEqual(self.state()['tasks']['TASK-1']['status'], 'pending')

    def test_scoped_change_preserves_independent_work_and_evidence(self):
        b = self.bundle()
        b['artifacts']['requirements.yaml']['requirements'].append({'id':'R2','title':'独立需求','acceptance':'仍为原值','sources':['S1']})
        b['artifacts']['tasks.yaml']['tasks'].append({'id':'TASK-2','title':'独立任务','repo':'ui','requirements':['R2'],'files':['src/app.py'],'checks':['other'],'depends_on':[]})
        b['artifacts']['cases.yaml']['cases'].append({'id':'T2','repo':'ui','kind':'auto','requirements':['R2'],'check':'other','expected':'仍为原值'})
        self.p['runtime']['checks']['other'] = copy.deepcopy(self.p['runtime']['checks']['unit'])
        atomic(self.w/'project.yaml',self.p)
        self.ready(b)
        for task, check in [('TASK-1','unit'),('TASK-2','other')]:
            self.mutate('start',target=task)
            run_check(self.w,None,check,self.state()['revision'])
            self.mutate('finish',target=task)
        defs=read(self.d/'requirements.yaml')
        defs['requirements'][0]['acceptance']='值为 3'
        bundle={'artifacts':{'requirements.yaml':defs}}
        before=(self.d/'status.yaml').read_bytes()
        preview=change(self.w,None,self.state()['revision'],bundle)
        self.assertEqual(preview['delta']['affected_tasks'],['TASK-1'])
        self.assertEqual((self.d/'status.yaml').read_bytes(),before)
        change(self.w,None,self.state()['revision'],bundle,apply=True)
        self.assertEqual(self.state()['tasks']['TASK-2']['status'],'done')
        prepare(self.w,None,self.state()['revision'],{'state':{'handoff':{'note':'等待确认 R1'}}})
        self.assertEqual(self.state()['pending_change']['kind'],'scoped')
        self.mutate('confirm',by='owner',note='确认 R1 的新验收')
        w,p,local,docs,d,s=context(self.w)
        self.assertTrue(valid_evidence(w,p,docs,d,s,'check','other','ui'))
        self.assertFalse(valid_evidence(w,p,docs,d,s,'check','unit','ui'))

    def test_transitive_dependencies_are_invalidated(self):
        b=self.bundle()
        tasks=b['artifacts']['tasks.yaml']['tasks']
        for n in (2,3):
            task=copy.deepcopy(tasks[0])
            task.update(id=f'TASK-{n}', depends_on=[f'TASK-{n-1}'])
            tasks.append(task)
        self.ready(b)
        defs=read(self.d/'tasks.yaml')
        defs['tasks'][0]['title']='更新第一步'
        result=change(self.w,None,self.state()['revision'],{'artifacts':{'tasks.yaml':defs}})
        self.assertEqual(result['delta']['affected_tasks'],['TASK-1','TASK-2','TASK-3'])

    def test_interrupted_editorial_update_cannot_keep_approval(self):
        from unittest.mock import patch
        from kitcore import workflow
        self.finish_auto()
        real_atomic=workflow.atomic
        def fail_material(path, data):
            if path.resolve() == (self.d/'Existing Spec.md').resolve():
                raise OSError('simulated disk failure')
            return real_atomic(path,data)
        with patch('kitcore.workflow.atomic',side_effect=fail_material):
            with self.assertRaises(OSError):
                prepare(self.w,None,self.state()['revision'],{'change_kind':'editorial','reason':'标题纠错','artifacts':{'Existing Spec.md':'新标题'}})
        self.assertFalse(self.state()['approval'])
        self.assertEqual(next_step(self.w)['phase'],'confirm')

    def test_out_of_band_change_cannot_be_laundered_through_scoped_update(self):
        self.finish_auto()
        (self.d/'Existing Spec.md').write_text('未记录的新范围')
        defs=read(self.d/'requirements.yaml')
        defs['requirements'][0]['title']='新标题'
        result=change(self.w,None,self.state()['revision'],{'artifacts':{'requirements.yaml':defs}},apply=True)
        self.assertEqual(result['update']['delta']['kind'],'broad')

    def test_check_inputs_keep_unrelated_changes_fresh_but_detect_relevant_changes(self):
        self.p['runtime']['checks']['unit']['inputs']=['src/*']
        atomic(self.w/'project.yaml',self.p)
        self.finish_auto()
        (self.repo/'README.md').write_text('docs only')
        self.assertEqual(resume(self.w)['verification'][0]['state'],'current')
        (self.repo/'src/app.py').write_text('value = 3')
        self.assertEqual(resume(self.w)['verification'][0]['state'],'code-changed')

    def test_check_inputs_do_not_hide_command_side_effects(self):
        self.p['runtime']['checks']['unit'].update(inputs=['src/*'],argv=[sys.executable,'-c','from pathlib import Path; Path("extra.txt").write_text("side effect")'])
        atomic(self.w/'project.yaml',self.p)
        self.ready()
        self.assertEqual(self.run_unit()['result'],'failed')

    def test_failure_diagnostics_are_safe_by_default_and_local_logs_are_opt_in(self):
        self.p['runtime']['checks']['unit']['argv']=[sys.executable,'-c','print("token=example-private-value"); raise AssertionError("bad value")']
        atomic(self.w/'project.yaml',self.p)
        self.ready()
        result=self.run_unit()
        self.assertEqual(result['diagnostic']['category'],'assertion')
        self.assertIsNone(result['local_diagnostic_log'])
        self.assertNotIn('example-private-value',json.dumps(result))
        result=run_check(self.w,None,'unit',self.state()['revision'],diagnostic_log=True)
        from pathlib import Path
        log=Path(result['local_diagnostic_log'])
        self.assertNotIn('example-private-value',log.read_text())
        self.assertIn('[REDACTED]',log.read_text())
        evidence=''.join(f.read_text() for f in (self.d/'.kit/evidence').glob('*.yaml'))
        self.assertNotIn('example-private-value',evidence)


if __name__ == '__main__':
    unittest.main()
