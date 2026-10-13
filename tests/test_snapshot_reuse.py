"""Bounded observation reuse must not leak into execution or later queries."""
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch
import unittest
import test_workflow as fixtures
from kitcore import workflow, experience


class SnapshotReuseTests(unittest.TestCase):
    setUp = fixtures.WorkspaceCase.setUp
    state = fixtures.WorkspaceCase.state
    mutate = fixtures.WorkspaceCase.mutate
    bundle = fixtures.WorkspaceCase.bundle
    ready = fixtures.WorkspaceCase.ready
    run_unit = fixtures.WorkspaceCase.run_unit
    finish_auto = fixtures.WorkspaceCase.finish_auto

    def test_summary_reuses_reads_but_next_query_detects_changes(self):
        self.finish_auto()
        with patch.object(workflow, 'code_files', wraps=workflow.code_files) as scan:
            cached = experience.resume(self.w)
            cached_reads = scan.call_count
        with patch.object(experience, 'snapshot_observation', return_value=nullcontext({'hits':0,'misses':0})), patch.object(workflow, 'code_files', wraps=workflow.code_files) as scan:
            fresh = experience.resume(self.w)
            fresh_reads = scan.call_count
        self.assertEqual(cached['progress'],fresh['progress'])
        self.assertLess(cached_reads,fresh_reads)
        self.assertGreater(cached['diagnostics']['snapshot_reuses'],0)
        (self.repo/'src/app.py').write_text('value = 9\n')
        self.assertEqual(experience.resume(self.w)['progress']['verification']['cases_current'],0)

    def test_inputs_filter_before_file_hashing(self):
        w,p,local,docs,d,s=workflow.context(self.w,None)
        unrelated=self.repo/'unrelated.txt'; unrelated.write_text('large unrelated input')
        seen=[]
        original=workflow.digest
        def recording(value):
            if isinstance(value,Path): seen.append(value)
            return original(value)
        with patch.object(workflow,'digest',side_effect=recording):
            filtered=workflow.code_snapshot(w,p,docs,'ui',['src/*'])
        self.assertNotIn(unrelated.resolve(),seen)
        self.assertIn((self.repo/'src/app.py').resolve(),seen)
        all_files=workflow.code_files(w,p,docs,'ui')
        self.assertEqual(filtered['tree'],original({k:v for k,v in all_files.items() if k.startswith('src/')}))

    def test_cache_discarded_on_error_and_execution_reads_fresh(self):
        w,p,local,docs,d,s=workflow.context(self.w,None)
        with self.assertRaises(RuntimeError):
            with workflow.snapshot_observation():
                before=workflow.code_snapshot(w,p,docs,'ui')
                raise RuntimeError('interrupted observation')
        (self.repo/'src/app.py').write_text('value = 7\n')
        self.assertNotEqual(before['tree'],workflow.code_snapshot(w,p,docs,'ui')['tree'])

    def test_explicit_run_after_summary_still_executes(self):
        self.ready(); self.run_unit()
        experience.resume(self.w)
        before=len(list((self.d/'.kit/evidence').glob('*.yaml')))
        self.run_unit()
        self.assertEqual(len(list((self.d/'.kit/evidence').glob('*.yaml'))),before+1)
