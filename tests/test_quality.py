"""Development quality gates linked to requirements, reference code and current changes."""
import copy
import unittest
import test_workflow as fixtures
from kitcore.storage import atomic, read, KitError
from kitcore.workflow import prepare, run_check, next_step
from kitcore import quality
from kitcore.experience import begin


class QualityTests(unittest.TestCase):
    state = fixtures.WorkspaceCase.state
    mutate = fixtures.WorkspaceCase.mutate
    bundle = fixtures.WorkspaceCase.bundle

    def setUp(self):
        fixtures.WorkspaceCase.setUp(self)
        self.p['development']['require_contract']=True
        atomic(self.w/'project.yaml',self.p)
        prepare(self.w,None,self.state()['revision'],self.bundle())

    def contract(self):
        return {'behaviors':[{'requirement':'R1','current':'默认值 1','expected':'默认值 2','cases':['T1']}],
                'references':[{'repo':'ui','path':'src/app.py','reason':'沿用现有常量定义方式'}],
                'approach':'仅修改现有常量，不改变读取入口',
                'reuse':'直接复用原模块，不新增配置层',
                'impact':'调用方仍从同一模块读取；只改变约定的默认值',
                'preserve':'导出名称、读取方式不变',
                'regression_cases':['T1'],
                'regression':'unit 复核原导出和新默认值，人工对照原调用方式'}

    def ready(self):
        quality.plan(self.w,None,'TASK-1',self.state()['revision'],self.contract())
        self.mutate('confirm',by='owner',note='原请求要求此范围修改并验证')
        self.mutate('start',target='TASK-1')

    def report(self):
        return {'requirements':[{'id':'R1','implementation':'ui/src/app.py 默认值','evidence':'检查 unit 与 T1 观察结果'}],
                'reuse':'沿用既有模块', 'style':'与原文件常量定义保持一致',
                'impact':'核对读取位置，未改导出契约', 'regression':'原调用方式及导出仍有效', 'findings':[]}

    def record_review(self):
        return quality.review(self.w,None,'TASK-1',self.state()['revision'],self.report(),'actual-reviewer')

    def test_cannot_confirm_or_start_without_project_specific_contract(self):
        with self.assertRaisesRegex(KitError,'开发依据'):
            self.mutate('confirm',by='owner',note='不能跳过调查')
        self.assertEqual(next_step(self.w)['phase'],'prepare')

    def test_invalid_behavior_mapping_and_missing_reference_are_rejected(self):
        c=self.contract(); c['behaviors'][0]['cases']=['unknown']
        with self.assertRaisesRegex(KitError,'验收用例'):
            quality.plan(self.w,None,'TASK-1',self.state()['revision'],c)
        c=self.contract(); c['references'][0]['path']='missing.py'
        with self.assertRaisesRegex(KitError,'不存在'):
            quality.plan(self.w,None,'TASK-1',self.state()['revision'],c)

    def test_changed_reference_before_start_requires_new_investigation(self):
        quality.plan(self.w,None,'TASK-1',self.state()['revision'],self.contract())
        self.mutate('confirm',by='owner',note='确认')
        (self.repo/'src/app.py').write_text('value = 99\n')
        self.assertEqual(next_step(self.w)['phase'],'prepare')
        with self.assertRaisesRegex(KitError,'参考实现已变化'):
            self.mutate('start',target='TASK-1')

    def test_passing_tests_alone_cannot_finish_and_inspect_is_readonly(self):
        self.ready()
        (self.repo/'src/app.py').write_text('value = 2\n')
        run_check(self.w,None,'unit',self.state()['revision'])
        with self.assertRaisesRegex(KitError,'缺少当前代码'):
            self.mutate('finish',target='TASK-1')
        before=(self.d/'status.yaml').read_bytes()
        result=quality.inspect(self.w,None,'TASK-1')
        self.assertEqual(result['changed_since_start'],['src/app.py'])
        self.assertEqual((self.d/'status.yaml').read_bytes(),before)
        self.record_review()
        self.mutate('finish',target='TASK-1')
        self.assertEqual(next_step(self.w)['phase'],'accept')

    def test_review_cannot_replace_tests_or_survive_code_changes(self):
        self.ready(); self.record_review()
        with self.assertRaisesRegex(KitError,'证据'):
            self.mutate('finish',target='TASK-1')
        (self.repo/'src/app.py').write_text('value = 2\n')
        run_check(self.w,None,'unit',self.state()['revision'])
        with self.assertRaisesRegex(KitError,'审查已过期'):
            self.mutate('finish',target='TASK-1')
        self.record_review(); self.mutate('finish',target='TASK-1')
        (self.repo/'src/app.py').write_text('value = 3\n')
        run_check(self.w,None,'unit',self.state()['revision'])
        with self.assertRaisesRegex(KitError,'审查已过期'):
            self.mutate('complete',by='owner',note='不能仅补测跳过新审查')

    def test_unresolved_findings_and_uncovered_requirement_cannot_pass_review(self):
        self.ready()
        report=self.report(); report['findings']=['仍有公共影响未处理']
        with self.assertRaisesRegex(KitError,'尚有审查问题'):
            quality.review(self.w,None,'TASK-1',self.state()['revision'],report,'reviewer')
        report=self.report(); report['requirements']=[]
        with self.assertRaisesRegex(KitError,'未覆盖'):
            quality.review(self.w,None,'TASK-1',self.state()['revision'],report,'reviewer')

    def test_quick_intent_waits_for_real_project_evidence_without_fake_approval(self):
        result=begin(self.w,'REQ-copy',request='修改提示文案',repo='ui',files=['src/app.py'],checks=['unit'],acceptance='新文案显示',out_of_scope='不改逻辑',by='owner',authorization_note='用户明确要求修改并验证',apply=True)
        self.assertEqual(result['result']['phase'],'prepare')
        self.assertFalse(read(self.d.parent/'REQ-copy/status.yaml')['approval'])

    def test_preserved_behavior_needs_real_evidence_before_finish(self):
        cases=read(self.d/'cases.yaml')
        cases['cases'].append({'id':'T2','requirements':['R1'],'repo':'ui','kind':'manual','expected':'原导出名称和读取方式不变'})
        prepare(self.w,None,self.state()['revision'],{'artifacts':{'cases.yaml':cases}})
        c=self.contract(); c['regression_cases']=['T2']
        quality.plan(self.w,None,'TASK-1',self.state()['revision'],c)
        self.mutate('confirm',by='owner',note='确认原请求及保留行为')
        self.mutate('start',target='TASK-1')
        run_check(self.w,None,'unit',self.state()['revision'])
        self.record_review()
        with self.assertRaisesRegex(KitError,'保留行为用例 T2'):
            self.mutate('finish',target='TASK-1')
        self.mutate('manual',target='case:T2',value='passed',by='tester',note='实际核对原导出和读取方式')
        self.mutate('finish',target='TASK-1')

    def test_new_install_enables_contract_and_legacy_config_remains_explicit(self):
        from kitcore.workspace import install
        import subprocess
        path=self.w.parent/'new-app'; path.mkdir()
        subprocess.run(['git','init','-b','main',str(path)],check=True,capture_output=True)
        install(path,apply=True)
        self.assertTrue(read(path/'project.yaml')['development']['require_contract'])


if __name__ == '__main__': unittest.main()
