"""Project discovery must surface uncertainty, not promote hints to configuration."""
from pathlib import Path
import unittest
import test_workflow as fixtures
from kitcore.discovery import discover
from kitcore.storage import atomic, digest


class DiscoveryTests(unittest.TestCase):
    setUp = fixtures.WorkspaceCase.setUp

    def record(self):
        source=self.repo/'package.json'
        source.write_text('{"scripts":{"test":"actual-project-command"}}')
        fact={'id':'testing.unit','area':'testing','status':'verified','value':'existing tests',
              'verified_by':'tester','verification':'read config and executed locally',
              'sources':[{'kind':'file','repo':'ui','path':'package.json','sha256':digest(source)}],
              'binding':['runtime','checks','unit'],'applied_sha256':digest(self.p['runtime']['checks']['unit'])}
        profile=self.w/'docs/team/project-context.yaml'
        atomic(profile,{'schema_version':1,'facts':[fact]})
        return source,profile,fact

    def test_discovery_is_readonly_and_does_not_expose_file_contents(self):
        source=self.repo/'package.json'
        source.write_text('{"scripts":{"test":"do-not-run-private-marker"}}')
        before={p:p.read_bytes() for p in self.w.rglob('*') if p.is_file()}
        result=discover(self.w,'testing')
        self.assertTrue(result['collection_needed'])
        self.assertTrue(any(c['path']=='package.json' for c in result['candidates']))
        self.assertNotIn('do-not-run-private-marker',str(result))
        after={p:p.read_bytes() for p in self.w.rglob('*') if p.is_file()}
        self.assertEqual(before,after)

    def test_source_and_applied_configuration_drift_are_reported(self):
        source,profile,fact=self.record()
        self.assertFalse(discover(self.w,'testing')['collection_needed'])
        source.write_text('{}')
        self.assertIn('来源文件已变化或缺失',discover(self.w,'testing')['facts'][0]['issues'])
        self.p['runtime']['checks']['unit']['argv']=['changed']
        atomic(self.w/'project.yaml',self.p)
        self.assertIn('应用到项目配置的值已变化或缺失',discover(self.w,'testing')['facts'][0]['issues'])

    def test_inference_and_unrelated_area_do_not_become_verified(self):
        source,profile,fact=self.record()
        fact['status']='inferred'
        atomic(profile,{'facts':[fact]})
        self.assertFalse(discover(self.w,'testing')['facts'][0]['usable_record'])
        result=discover(self.w,'business')
        self.assertEqual(result['facts'],[])
        self.assertTrue(result['collection_needed'])

    def test_dynamic_source_requires_recheck_without_network(self):
        source,profile,fact=self.record()
        fact['sources']=[{'kind':'external','reference':'https://dev.example.test/build','checked_at':'2026-10-09'}]
        atomic(profile,{'facts':[fact]})
        self.assertIn('动态来源需在本次相关操作前复核',discover(self.w,'testing')['facts'][0]['issues'])

    def test_verified_label_alone_does_not_count_as_verified_fact(self):
        source,profile,fact=self.record()
        fact.pop('verification')
        atomic(profile,{'facts':[fact]})
        self.assertFalse(discover(self.w,'testing')['facts'][0]['usable_record'])

    def test_unrelated_and_secret_files_are_not_inventory_candidates(self):
        (self.repo/'.env').write_text('private')
        (self.repo/'unrelated').mkdir()
        (self.repo/'unrelated/README.md').write_text('unrelated')
        paths=[c['path'] for c in discover(self.w)['candidates']]
        self.assertNotIn('.env',paths)
        self.assertNotIn('unrelated/README.md',paths)


if __name__ == '__main__': unittest.main()
