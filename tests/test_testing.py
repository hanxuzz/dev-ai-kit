"""Normalized QA intake and test runs against an ephemeral local HTTP fixture."""
import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch
import test_workflow as fixtures
from kitcore.testing import draft, import_cases, environment, junit_results
from kitcore.storage import atomic, read, KitError
from kitcore.workflow import prepare, run_check, context, valid_evidence, next_step


class TestingTests(unittest.TestCase):
    setUp = fixtures.WorkspaceCase.setUp
    state = fixtures.WorkspaceCase.state
    mutate = fixtures.WorkspaceCase.mutate
    bundle = fixtures.WorkspaceCase.bundle
    ready = fixtures.WorkspaceCase.ready

    def case(self):
        return {'id':'QA-1','title':'默认值正确','requirements':['R1'],'repo':'ui','kind':'manual','steps':['读取 app 的默认值'],'expected':'值为 2','source_location':'Sheet1 第 2 行'}

    def test_arbitrary_original_is_traceable_and_import_is_preview_first(self):
        self.ready()
        original=Path(self.tmp.name)/'测试原件.custom'
        original.write_bytes(b'arbitrary format parsed by agent')
        normalized=Path(self.tmp.name)/'normalized.yaml'
        atomic(normalized,{'cases':[self.case()]})
        before=(self.d/'status.yaml').read_bytes()
        result=import_cases(self.w,None,normalized,original=original)
        self.assertFalse(result['mutates'])
        self.assertEqual((self.d/'status.yaml').read_bytes(),before)
        result=import_cases(self.w,None,normalized,self.state()['revision'],reviewed_by='qa-reviewer',apply=True,original=original)
        c=read(self.d/'cases.yaml')['cases'][-1]
        self.assertEqual(c['origin']['type'],'qa')
        self.assertEqual(c['source_location'],'Sheet1 第 2 行')
        self.assertEqual(c['review_status'],'reviewed')
        self.assertNotIn(str(original),str(c))
        self.assertFalse(self.state()['approval'])

    def test_original_conversion_requires_location_and_duplicate_needs_explicit_replace(self):
        self.ready()
        path=Path(self.tmp.name)/'normalized.yaml'
        original=Path(self.tmp.name)/'source.pdf'
        original.write_bytes(b'fixture')
        c=self.case(); c.pop('source_location')
        atomic(path,{'cases':[c]})
        with self.assertRaisesRegex(KitError,'source_location'):
            import_cases(self.w,None,path,original=original)
        atomic(path,{'cases':[self.case()]})
        import_cases(self.w,None,path,self.state()['revision'],apply=True)
        with self.assertRaisesRegex(KitError,'已存在'):
            import_cases(self.w,None,path)
        self.assertFalse(import_cases(self.w,None,path,replace=True)['mutates'])

    def test_generated_seeds_are_drafts_and_cannot_satisfy_delivery(self):
        self.ready()
        generated=draft(self.w,None,'ui')
        self.assertEqual(generated['cases'][0]['review_status'],'draft')
        p=Path(self.tmp.name)/'ai.yaml'; atomic(p,{'cases':generated['cases']})
        import_cases(self.w,None,p,self.state()['revision'],source='ai',apply=True)
        with self.assertRaisesRegex(KitError,'草稿'):
            self.mutate('confirm',by='owner',note='尚未审阅不能确认')

    def test_csv_and_invalid_requirement(self):
        self.ready()
        p=Path(self.tmp.name)/'qa.csv'
        p.write_text('id,title,requirements,repo,kind,steps,expected\nQA-1,检查默认值,R1,ui,manual,打开|观察,等于2\n',encoding='utf-8-sig')
        result=import_cases(self.w,None,p)
        self.assertEqual(result['bundle']['artifacts']['cases.yaml']['cases'][-1]['steps'],['打开','观察'])
        p.write_text(p.read_text(encoding='utf-8-sig').replace(',R1,',',R999,'))
        with self.assertRaisesRegex(KitError,'未知需求'):
            import_cases(self.w,None,p)

    def test_malformed_csv_reports_actionable_error_without_changing_materials(self):
        self.ready()
        p=Path(self.tmp.name)/'qa.csv'
        before=(self.d/'cases.yaml').read_bytes()
        for text in ('id,title,requirements,repo,kind,steps,expected\nQA-1,title,R1,ui,manual\n',
                     'id,title,requirements,repo,kind,steps,expected\nQA-1,title,R1,ui,manual,step,expected,extra\n'):
            p.write_text(text)
            with self.assertRaisesRegex(KitError,'第 2 行列数'):
                import_cases(self.w,None,p,self.state()['revision'],apply=True)
        p.write_bytes(b'\xff\xfe\x00')
        with self.assertRaisesRegex(KitError,'UTF-8'):
            import_cases(self.w,None,p)
        self.assertEqual((self.d/'cases.yaml').read_bytes(),before)

    def setup_http(self, kind='local', mode='pass'):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200); self.end_headers(); self.wfile.write(b'healthy')
            def log_message(self,*args):
                pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        def cleanup():
            server.shutdown(); server.server_close(); thread.join(timeout=2)
        self.addCleanup(cleanup)
        self.p['runtime']['environments']={'target':{'kind':kind,'base_url':f'http://127.0.0.1:{server.server_port}','deployment_id':'dev-build-17' if kind=='dev' else ''}}
        runner='''import os, urllib.request, xml.etree.ElementTree as ET
from pathlib import Path
assert urllib.request.urlopen(os.environ['KIT_BASE_URL'] + '/health', timeout=3).read() == b'healthy'
root=ET.Element('testsuite')
case=ET.SubElement(root,'testcase',classname='qa',name='test_health')
'''
        if mode=='skip': runner+="ET.SubElement(case,'skipped')\n"
        if mode=='fail': runner+="ET.SubElement(case,'failure',message='private raw text')\n"
        if mode=='duplicate': runner+="ET.SubElement(root,'testcase',classname='qa',name='test_health')\n"
        if mode!='missing': runner+="ET.ElementTree(root).write(os.environ['KIT_JUNIT_PATH'],encoding='utf-8')\n"
        self.p['runtime']['checks']['http']={'repo':'ui','argv':[sys.executable,'-c',runner],'environment':'target','report':'junit','timeout_seconds':5}
        atomic(self.w/'project.yaml',self.p)
        b=self.bundle()
        b['artifacts']['cases.yaml']['cases'].append({'id':'QA-1','repo':'ui','kind':'auto','check':'http','requirements':['R1'],'expected':'健康接口返回 healthy','test_name':'qa::test_health','review_status':'reviewed'})
        self.ready(b)

    def test_real_http_and_junit_result_are_bound_to_local_environment(self):
        self.setup_http()
        result=run_check(self.w,None,'http',self.state()['revision'])
        self.assertEqual(result['result'],'passed')
        self.assertEqual(result['case_results'],{'QA-1':'passed'})
        self.assertEqual(result['environment']['kind'],'local')
        self.assertFalse(list((self.w/'.dev-ai-kit/reports').glob('*.xml')))
        w,p,_,docs,d,s=context(self.w)
        self.assertTrue(valid_evidence(w,p,docs,d,s,'check','http','ui'))
        p['runtime']['environments']['target']['deployment_id']='changed'
        self.assertFalse(valid_evidence(w,p,docs,d,s,'check','http','ui'))

    def test_dev_requires_explicit_target_readiness_and_records_remote_version(self):
        self.setup_http(kind='dev')
        with self.assertRaisesRegex(KitError,'部署版本'):
            run_check(self.w,None,'http',self.state()['revision'])
        result=run_check(self.w,None,'http',self.state()['revision'],ready=['environment:target'])
        self.assertEqual(result['environment']['deployment_id'],'dev-build-17')
        self.assertEqual(result['result'],'passed')
        self.assertNotIn('base_url',str(result['environment']))

    def test_skipped_case_is_not_passing_even_when_command_succeeds(self):
        self.setup_http(mode='skip')
        result=run_check(self.w,None,'http',self.state()['revision'])
        self.assertEqual(result['exit_code'],0)
        self.assertEqual(result['result'],'failed')
        self.assertEqual(result['case_results']['QA-1'],'skipped')

    def test_missing_fresh_report_is_not_passing(self):
        self.setup_http(mode='missing')
        result=run_check(self.w,None,'http',self.state()['revision'])
        self.assertEqual(result['result'],'failed')

    def test_failed_test_output_not_copied_into_evidence(self):
        self.setup_http(mode='fail')
        result=run_check(self.w,None,'http',self.state()['revision'])
        self.assertEqual(result['result'],'failed')
        self.assertNotIn('private raw text',str(result))
        self.assertNotIn('private raw text',''.join(p.read_text() for p in (self.d/'.kit/evidence').glob('*.yaml')))

    def test_junit_duplicate_missing_and_entity_are_rejected(self):
        p=Path(self.tmp.name)/'report.xml'
        p.write_text('<testsuite><testcase classname="qa" name="x"/><testcase classname="qa" name="x"/></testsuite>')
        result=junit_results(p,[{'id':'QA-1','test_name':'qa::x'},{'id':'QA-2','test_name':'qa::y'}])
        self.assertEqual(result['cases'],{'QA-1':'ambiguous','QA-2':'missing'})
        self.assertFalse(result['ok'])
        p.write_text('<!DOCTYPE foo [<!ENTITY x "text">]><testsuite/>')
        with self.assertRaises(KitError): junit_results(p,[])

    def test_auto_import_requires_executable_mapping_and_keeps_external_id(self):
        self.ready()
        p=Path(self.tmp.name)/'normalized.yaml'
        c=self.case(); c.update(kind='auto',check='unit',test_name='qa::test_value',external_id='original-1')
        atomic(p,{'cases':[c]})
        with self.assertRaisesRegex(KitError,'junit'):
            import_cases(self.w,None,p)
        self.p['runtime']['checks']['unit']['report']='junit'
        atomic(self.w/'project.yaml',self.p)
        result=import_cases(self.w,None,p,reviewed_by='qa')
        imported=result['bundle']['artifacts']['cases.yaml']['cases'][-1]
        self.assertEqual(imported['origin']['external_id'],'original-1')

    def test_dev_check_cannot_finish_local_implementation_task(self):
        self.setup_http(kind='dev')
        tasks=read(self.d/'tasks.yaml')
        tasks['tasks'][0]['checks']=['http']
        prepare(self.w,None,self.state()['revision'],{'artifacts':{'tasks.yaml':tasks}})
        with self.assertRaisesRegex(KitError,'不能用 dev'):
            self.mutate('confirm',by='owner',note='不能混淆远端与本地结果')

    def test_task_only_report_cannot_pass_skipped_or_ambiguous_tests(self):
        p=Path(self.tmp.name)/'report.xml'
        p.write_text('<testsuite><testcase name="x"><skipped/></testcase></testsuite>')
        result=junit_results(p,[])
        self.assertFalse(result['ok'])
        self.assertEqual(result['skipped'],1)
        p.write_text('<testsuite><testcase name="x"/><testcase name="x"/></testsuite>')
        self.assertFalse(junit_results(p,[])['ok'])

    def test_utf16_entity_declaration_cannot_bypass_report_validation(self):
        p=Path(self.tmp.name)/'report.xml'
        p.write_bytes('<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE testsuite [<!ENTITY x "text">]><testsuite/>'.encode('utf-16'))
        with self.assertRaises(KitError):
            junit_results(p,[])

    def test_environment_validation_and_missing_credentials(self):
        p={'runtime':{'environments':{'dev':{'kind':'dev','base_url':'https://dev.example.test','deployment_id':'17','required_env':['KIT_TEST_TOKEN']}}}}
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaisesRegex(KitError,'凭证'):
                environment(p,{'environment':'dev'},require_secrets=True)
        p['runtime']['environments']['dev']['base_url']='https://user:password@dev.example.test'
        with self.assertRaises(KitError): environment(p,{'environment':'dev'})


if __name__ == '__main__': unittest.main()
