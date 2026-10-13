"""Progress is observable after actions, distinguishes evidence from completion, and stays read-only."""
import json
import subprocess
import sys
import unittest
import test_workflow as fixtures
from kitcore.experience import resume
from kitcore.storage import read, atomic
from kitcore.workspace import KIT
from kitcore.workflow import prepare


class ProgressTests(unittest.TestCase):
    setUp = fixtures.WorkspaceCase.setUp
    state = fixtures.WorkspaceCase.state
    mutate = fixtures.WorkspaceCase.mutate
    bundle = fixtures.WorkspaceCase.bundle
    ready = fixtures.WorkspaceCase.ready
    run_unit = fixtures.WorkspaceCase.run_unit
    finish_auto = fixtures.WorkspaceCase.finish_auto

    def test_new_requirement_reports_missing_plan_not_zero_percent(self):
        p=resume(self.w)['progress']
        self.assertEqual(p['tasks']['total'],0)
        self.assertEqual(p['next']['owner'],'agent')
        self.assertFalse(p['delivery']['accepted'])
        self.assertNotIn('percent',p)

    def test_task_and_acceptance_are_distinct_and_summary_is_readonly(self):
        self.finish_auto()
        before=(self.d/'status.yaml').read_bytes()
        p=resume(self.w)['progress']
        self.assertEqual(p['tasks']['done'],1)
        self.assertEqual(p['verification']['cases_current'],1)
        self.assertFalse(p['delivery']['accepted'])
        self.assertEqual(p['next']['owner'],'user')
        self.assertEqual(p['delivery']['git_and_deployment'],'not_inspected')
        self.assertEqual(before,(self.d/'status.yaml').read_bytes())
        self.mutate('complete',by='owner',note='实际接受本轮交付')
        self.assertTrue(resume(self.w)['progress']['delivery']['accepted'])

    def test_stale_test_does_not_count_as_current_pass(self):
        self.finish_auto()
        (self.repo/'src/app.py').write_text('value = 3\n')
        s=resume(self.w)
        self.assertEqual(s['cases'][0]['last_result'],'passed')
        self.assertFalse(s['cases'][0]['current_passed'])
        self.assertEqual(s['progress']['verification']['cases_current'],0)
        self.assertEqual(s['progress']['next']['owner'],'agent')

    def test_manual_results_count_only_after_actual_observation(self):
        self.ready(self.bundle(manual=True))
        self.assertEqual(resume(self.w)['progress']['verification']['cases_current'],0)
        self.mutate('manual',target='case:T1',value='passed',by='tester',note='实际观察符合验收')
        self.assertEqual(resume(self.w)['progress']['verification']['cases_current'],1)

    def test_build_advice_does_not_grant_execution_permission(self):
        self.ready()
        p=resume(self.w)['progress']
        self.assertEqual(p['tasks']['pending'],1)
        self.assertEqual(p['next']['owner'],'agent')
        self.assertFalse(p['grants_execution_permission'])
        self.assertFalse(self.state()['tasks'])

    def test_blocker_and_business_questions_are_visible(self):
        self.ready(); self.mutate('block',note='本地依赖服务未启动')
        p=resume(self.w)['progress']
        self.assertIn('本地依赖服务未启动',p['remaining'])
        self.assertEqual(p['next']['owner'],'agent')
        self.mutate('block',note='')
        prepare(self.w,None,self.state()['revision'],{'state':{'questions':'open'}})
        self.assertEqual(resume(self.w)['progress']['next']['owner'],'user')

    def test_cli_finish_includes_current_progress_without_extra_query(self):
        self.ready(); self.mutate('start',target='TASK-1'); self.run_unit()
        p=subprocess.run([sys.executable,str(KIT/'scripts/kit.py'),'finish','--workspace',str(self.w),'--target','TASK-1','--expect',str(self.state()['revision'])],capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(p.returncode,0,p.stderr)
        response=json.loads(p.stdout)
        self.assertEqual(response['progress']['tasks']['done'],1)
        self.assertFalse(response['progress']['delivery']['accepted'])
        self.assertEqual(response['progress']['next']['owner'],'user')

    def test_failed_check_is_an_actionable_next_step_even_during_build(self):
        self.p['runtime']['checks']['unit']['argv']=[sys.executable,'-c','raise AssertionError()']
        atomic(self.w/'project.yaml',self.p)
        self.ready(); self.mutate('start',target='TASK-1'); self.run_unit()
        p=resume(self.w)['progress']
        self.assertIn('记录并分析失败检查',p['next']['action'])
        self.assertEqual(p['verification_gaps'][0]['state'],'failed')

    def test_summary_failure_does_not_report_successful_write_as_failed(self):
        from kitcore import cli
        from unittest.mock import patch
        from contextlib import redirect_stdout
        import io
        before=self.state()['revision']
        output=io.StringIO()
        with patch('kitcore.experience.resume',side_effect=ValueError('unreadable summary')), redirect_stdout(output):
            code=cli.main(['block','--workspace',str(self.w),'--expect',str(before),'--note','等待依赖'])
        self.assertEqual(code,0)
        response=json.loads(output.getvalue())
        self.assertFalse(response['progress']['available'])
        self.assertEqual(self.state()['revision'],before+1)
        self.assertEqual(self.state()['blocker'],'等待依赖')

    def test_missing_selection_has_explicit_user_next_step(self):
        local=read(self.w/'project.local.yaml'); local['current']=''
        atomic(self.w/'project.local.yaml',local)
        p=resume(self.w)['progress']
        self.assertEqual(p['next']['owner'],'user')
        self.assertFalse(p['grants_execution_permission'])


if __name__ == '__main__': unittest.main()
