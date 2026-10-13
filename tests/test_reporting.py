"""Reports distinguish historical evidence, failures and fresh execution."""
from datetime import datetime, timezone, timedelta
import json
import subprocess
import sys
import unittest
import test_workflow as fixtures
from kitcore.reporting import report
from kitcore.storage import KitError, read, atomic
from kitcore.workspace import KIT


class ReportingTests(unittest.TestCase):
    setUp=fixtures.WorkspaceCase.setUp
    state=fixtures.WorkspaceCase.state
    mutate=fixtures.WorkspaceCase.mutate
    bundle=fixtures.WorkspaceCase.bundle
    ready=fixtures.WorkspaceCase.ready
    run_unit=fixtures.WorkspaceCase.run_unit
    finish_auto=fixtures.WorkspaceCase.finish_auto

    def test_history_is_not_current_round_and_report_does_not_change_state(self):
        self.finish_auto()
        for path in (self.d/'.kit/evidence').glob('*.yaml'):
            e=read(path);e['at']='2020-01-01T00:00:00+00:00';atomic(path,e)
        before=(self.d/'status.yaml').read_bytes()
        since=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()
        preview=report(self.w,None,since)
        self.assertEqual(preview['counts']['executed'],0)
        self.assertIn('历史证据当前适用',preview['markdown'])
        self.assertFalse((self.d/'.kit/test-reports').exists())
        saved=report(self.w,None,since,True)
        from pathlib import Path
        self.assertEqual(Path(saved['path']).read_text(),saved['markdown'])
        self.assertEqual(before,(self.d/'status.yaml').read_bytes())
        self.assertNotEqual(saved['path'],report(self.w,None,since,True)['path'])

    def test_failure_and_retest_are_both_visible(self):
        self.ready()
        self.p['runtime']['checks']['unit']['argv']=[sys.executable,'-c','raise SystemExit(1)']
        atomic(self.w/'project.yaml',self.p)
        self.run_unit()
        self.p['runtime']['checks']['unit']['argv']=[sys.executable,'-c','print("ok")']
        atomic(self.w/'project.yaml',self.p)
        self.run_unit()
        r=report(self.w,None,'2000-01-01T00:00:00Z')
        self.assertEqual(r['counts']['executed'],1)
        self.assertIn('失败',r['markdown']);self.assertIn('通过',r['markdown'])
        self.assertIn('自动检查级（非逐条断言）',r['markdown'])

    def test_stale_manual_and_missing_cases_remain_visible(self):
        self.ready(self.bundle(manual=True))
        r=report(self.w,None,'2000-01-01T00:00:00Z')
        self.assertIn('本轮未执行',r['markdown'])
        self.mutate('manual',target='case:T1',value='passed',by='tester',note='实际观察，无敏感日志')
        (self.repo/'src/app.py').write_text('value = 5\n')
        r=report(self.w,None,'2000-01-01T00:00:00Z')
        self.assertEqual(r['counts']['current_passed'],0)
        self.assertIn('未通过/已失效/待审阅',r['markdown'])

    def test_cli_and_timestamp_validation(self):
        for value in ['invalid','2020-01-01T00:00:00','2999-01-01T00:00:00Z']:
            with self.assertRaises(KitError): report(self.w,None,value)
        result=subprocess.run([sys.executable,str(KIT/'scripts/kit.py'),'test-report','--workspace',str(self.w),'--since','2000-01-01T00:00:00Z','--apply'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue(json.loads(result.stdout)['path'].endswith('.md'))
