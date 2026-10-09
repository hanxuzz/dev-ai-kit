"""Local workflow integration tests: real files, Git, and child processes; no remote services."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from kitcore.storage import KitError, read, atomic, inside, lock
from kitcore.workspace import KIT, install, rollback
from kitcore.workflow import adopt, select, prepare, mutate, run_check, next_step, context, issues_for, state_lock


class WorkspaceCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='kit-test-')
        self.addCleanup(self.tmp.cleanup)
        self.w = Path(self.tmp.name) / 'workspace with spaces'
        self.w.mkdir()
        self.repo = self.w / 'ui'
        self.repo.mkdir()
        subprocess.run(['git', 'init', '-b', 'main', str(self.repo)], check=True, capture_output=True)
        (self.repo / 'src').mkdir()
        (self.repo / 'src/app.py').write_text('value = 1\n', encoding='utf-8')
        install(self.w, apply=True)
        self.p = read(self.w / 'project.yaml')
        self.p['conventions'].update(confirmed=True, branch={'mode': 'current', 'auto_create': False})
        self.p['runtime']['checks'] = {'unit': {'repo': 'ui', 'argv': [sys.executable, '-c', 'print("unit passed")'], 'cwd': '.', 'timeout_seconds': 5, 'requires': []}}
        atomic(self.w / 'project.yaml', self.p)
        adopt(self.w, 'REQ-one', apply=True)
        self.d = self.w / 'docs/requirements/REQ-one'

    def state(self):
        return read(self.d / 'status.yaml')

    def mutate(self, action, **kwargs):
        return mutate(self.w, None, self.state()['revision'], action, **kwargs)

    def bundle(self, manual=False):
        return {'state': {'files': {'requirement': 'Existing Spec.md'}, 'sources': {'S1': {'type': 'text', 'status': 'collected', 'version': 'ticket-1', 'summary': '用户要求修改 app 的值'}}},
                'artifacts': {'Existing Spec.md': '# 原有规格\n范围内 R1：修改 app 的值；明确不做：数据库修改。验收：值为 2。\n',
                              '05-impact.md': '# 影响分析\n只影响 ui/src/app.py 中的值；不涉及接口、数据迁移或权限。\n',
                              '06-plan.md': '# 计划\nTASK-1 修改 src/app.py 后运行 unit；本次不发布、不提交。\n',
                              'requirements.yaml': {'requirements': [{'id': 'R1', 'title': '修改值', 'acceptance': '给定默认配置，当读取值，则为 2', 'sources': ['S1']}], 'out_of_scope': ['数据库修改']},
                              'tasks.yaml': {'tasks': [{'id': 'TASK-1', 'title': '修改值并验证', 'repo': 'ui', 'requirements': ['R1'], 'depends_on': [], 'files': ['src/app.py'], 'checks': [] if manual else ['unit'], **({'manual_acceptance': '用户在本地读取值并确认等于 2'} if manual else {})}]},
                              'cases.yaml': {'cases': [{'id': 'T1', 'requirements': ['R1'], 'repo': 'ui', 'kind': 'manual' if manual else 'auto', 'expected': '值为 2', **({} if manual else {'check': 'unit'})}]}}}

    def ready(self, bundle=None):
        prepare(self.w, None, self.state()['revision'], bundle or self.bundle())
        self.mutate('confirm', by='test-user', note='已确认范围、任务和验收版本')

    def run_unit(self):
        return run_check(self.w, None, 'unit', self.state()['revision'])

    def finish_auto(self):
        self.ready()
        self.mutate('start', target='TASK-1')
        (self.repo / 'src/app.py').write_text('value = 2\n', encoding='utf-8')
        self.run_unit()
        self.mutate('finish', target='TASK-1')

    def test_existing_spec_to_delivery_without_recording_or_renaming(self):
        self.finish_auto()
        self.assertFalse((self.d / '04-requirement.md').exists())
        self.assertFalse((self.d / '01-meeting.md').exists())
        self.assertEqual(next_step(self.w)['phase'], 'accept')
        self.mutate('complete', by='user', note='已验收本轮结果')
        self.assertEqual(next_step(self.w)['phase'], 'done')
        self.assertEqual(self.state()['tasks']['TASK-1']['status'], 'done')

    def test_manual_only_flow_does_not_require_runtime_or_database(self):
        self.ready(self.bundle(manual=True))
        self.mutate('start', target='TASK-1')
        self.mutate('manual', target='task:TASK-1', value='passed', by='tester', note='本地观察值为 2')
        self.mutate('finish', target='TASK-1')
        self.assertEqual(next_step(self.w)['phase'], 'test')
        self.mutate('manual', target='case:T1', value='passed', by='tester', note='已按 R1 验收')
        self.mutate('complete', by='owner', note='接受本次结果')
        self.assertEqual(next_step(self.w)['phase'], 'done')

    def test_next_is_read_only_and_never_starts_a_task(self):
        self.ready()
        before = (self.d / 'status.yaml').read_bytes()
        self.assertEqual(next_step(self.w)['phase'], 'build')
        self.assertEqual(next_step(self.w)['phase'], 'build')
        self.assertEqual((self.d / 'status.yaml').read_bytes(), before)
        self.assertFalse((self.w / '.cursor/next-step.txt').exists())

    def test_existing_directory_missing_status_can_be_adopted(self):
        old = self.d.parent / 'REQ-old'
        old.mkdir()
        (old / 'Spec.md').write_text('existing important materials', encoding='utf-8')
        adopt(self.w, 'REQ-old', apply=True)
        self.assertEqual(read(self.w / 'project.local.yaml')['current'], 'REQ-old')
        self.assertEqual((old / 'Spec.md').read_text(), 'existing important materials')
        self.assertEqual(read(old / 'status.yaml')['revision'], 0)

    def test_legacy_status_is_backed_up_without_inheriting_confirmation(self):
        atomic(self.d / 'status.yaml', {'stage': 'done', 'questions': 'confirmed', 'files': {'requirement': 'Spec.md'}})
        adopt(self.w, 'REQ-one', apply=True)
        self.assertEqual(self.state()['stage'], 'intake')
        self.assertFalse(self.state()['approval'])
        self.assertEqual(read(self.d / '.kit/legacy-status.yaml')['stage'], 'done')

    def test_material_change_invalidates_approval(self):
        self.ready()
        (self.d / 'Existing Spec.md').write_text('changed scope and acceptance', encoding='utf-8')
        self.assertEqual(next_step(self.w)['phase'], 'confirm')
        with self.assertRaisesRegex(KitError, '重新确认'):
            self.mutate('start', target='TASK-1')

    def test_code_change_invalidates_previous_evidence(self):
        self.finish_auto()
        (self.repo / 'src/app.py').write_text('value = 3\n', encoding='utf-8')
        self.assertEqual(next_step(self.w)['phase'], 'test')
        with self.assertRaisesRegex(KitError, '证据|通过'):
            self.mutate('complete', by='user', note='尝试验收')

    def test_latest_failure_replaces_previous_success(self):
        self.ready()
        self.assertEqual(self.run_unit()['result'], 'passed')
        self.p['runtime']['checks']['unit']['argv'] = [sys.executable, '-c', 'raise SystemExit(1)']
        atomic(self.w / 'project.yaml', self.p)
        self.assertEqual(self.run_unit()['result'], 'failed')
        self.mutate('start', target='TASK-1')
        with self.assertRaisesRegex(KitError, '证据'):
            self.mutate('finish', target='TASK-1')

    def test_timeout_is_failure_and_does_not_write_raw_output(self):
        self.p['runtime']['checks']['unit'].update(argv=[sys.executable, '-c', 'import time; print("secret-example", flush=True); time.sleep(10)'], timeout_seconds=0.1)
        atomic(self.w / 'project.yaml', self.p)
        self.ready()
        result = self.run_unit()
        self.assertTrue(result['timed_out'])
        self.assertEqual(result['result'], 'failed')
        evidence = '\n'.join(x.read_text() for x in (self.d / '.kit/evidence').glob('*.yaml'))
        self.assertNotIn('secret-example', evidence)

    def test_check_that_changes_code_cannot_be_passing_evidence(self):
        self.p['runtime']['checks']['unit']['argv'] = [sys.executable, '-c', 'from pathlib import Path; Path("src/app.py").write_text("changed")']
        atomic(self.w / 'project.yaml', self.p)
        self.ready()
        result = self.run_unit()
        self.assertTrue(result['code_changed_during_check'])
        self.assertEqual(result['result'], 'failed')

    def test_concurrent_revision_is_rejected(self):
        rev = self.state()['revision']
        prepare(self.w, None, rev, self.bundle())
        with self.assertRaisesRegex(KitError, 'revision'):
            prepare(self.w, None, rev, self.bundle())

    def test_shared_root_lock_rejects_a_second_writer(self):
        with lock(self.d.parent):
            with self.assertRaisesRegex(KitError, '锁'):
                self.mutate('block', note='second writer')
        self.assertFalse((self.w / '.dev-ai-kit.lock').exists())

    def test_open_questions_block_execution_not_material_recovery(self):
        self.ready()
        prepare(self.w, None, self.state()['revision'], {'state': {'questions': 'open'}, 'artifacts': {'03-questions.md': 'Q1: 请确认新增范围'}})
        self.assertEqual(next_step(self.w)['phase'], 'questions')
        with self.assertRaises(KitError):
            self.mutate('start', target='TASK-1')
        with self.assertRaises(KitError):
            prepare(self.w, None, self.state()['revision'], self.bundle())

    def test_unrelated_blocked_requirement_does_not_block_current(self):
        self.ready()
        other = self.d.parent / 'REQ-other'
        other.mkdir()
        atomic(other / 'status.yaml', {'stage': 'questions', 'questions': 'open'})
        self.assertFalse(issues_for(self.w, ready=True))

    def test_cycles_and_uncovered_requirements_are_rejected(self):
        b = self.bundle()
        b['artifacts']['tasks.yaml']['tasks'][0]['depends_on'] = ['TASK-2']
        second = copy.deepcopy(b['artifacts']['tasks.yaml']['tasks'][0])
        second.update(id='TASK-2', depends_on=['TASK-1'])
        b['artifacts']['tasks.yaml']['tasks'].append(second)
        prepare(self.w, None, 0, b)
        with self.assertRaisesRegex(KitError, '循环'):
            self.mutate('confirm', by='user', note='confirm')

    def test_every_requirement_needs_task_and_case(self):
        b = self.bundle()
        b['artifacts']['requirements.yaml']['requirements'].append({'id': 'R2', 'title': '第二需求', 'acceptance': '可观察结果', 'sources': ['S1']})
        prepare(self.w, None, 0, b)
        issues = issues_for(self.w, ready=True)
        self.assertTrue(any('需求没有任务承接' in x for x in issues))
        self.assertTrue(any('验收未覆盖' in x for x in issues))

    def test_branch_policy_blocks_wrong_branch_even_without_auto_create(self):
        self.ready()
        self.p['conventions']['branch'] = {'mode': 'project', 'auto_create': False, 'allowed_pattern': 'feature/.+'}
        atomic(self.w / 'project.yaml', self.p)
        self.assertEqual(next_step(self.w)['phase'], 'conventions')
        with self.assertRaisesRegex(KitError, '分支'):
            self.mutate('start', target='TASK-1')

    def test_out_of_scope_edit_blocks_task_completion_without_reverting_files(self):
        self.ready()
        self.mutate('start', target='TASK-1')
        extra = self.repo / 'unexpected.py'
        extra.write_text('do not remove me', encoding='utf-8')
        self.run_unit()
        with self.assertRaisesRegex(KitError, '范围外'):
            self.mutate('finish', target='TASK-1')
        self.assertEqual(extra.read_text(), 'do not remove me')

    def test_blocker_can_be_cleared_and_progress_restored(self):
        self.ready()
        self.mutate('block', note='网络资源未同步')
        self.assertEqual(next_step(self.w)['phase'], 'blocked')
        self.mutate('block', note='')
        self.assertEqual(next_step(self.w)['phase'], 'build')

    def test_snapshot_handoff_does_not_invalidate_approval(self):
        self.ready()
        prepare(self.w, None, self.state()['revision'], {'state': {'handoff': {'note': '还没开始修改', 'next': 'TASK-1'}}})
        self.assertEqual(next_step(self.w)['phase'], 'build')

    def test_install_is_idempotent_and_preserves_user_configuration(self):
        before = (self.w / 'project.yaml').read_bytes()
        result = install(self.w, apply=True)
        self.assertEqual(result['changes'], [])
        self.assertEqual((self.w / 'project.yaml').read_bytes(), before)

    def test_upgrade_preserves_modified_rule_and_supplies_candidate(self):
        rule = self.w / '.cursor/rules/dev-ai-kit.mdc'
        rule.write_text('user project rule', encoding='utf-8')
        result = install(self.w, apply=True)
        self.assertEqual(rule.read_text(), 'user project rule')
        self.assertTrue((self.w / '.dev-ai-kit/dev-ai-kit.mdc.proposed').exists())
        rollback(self.w, result['backup'])
        self.assertEqual(rule.read_text(), 'user project rule')
        self.assertFalse((self.w / '.dev-ai-kit/dev-ai-kit.mdc.proposed').exists())

    def test_rollback_refuses_to_overwrite_post_install_user_change(self):
        rule = self.w / '.cursor/rules/dev-ai-kit.mdc'
        rule.write_text('modified', encoding='utf-8')
        result = install(self.w, apply=True)
        (self.w / '.dev-ai-kit/dev-ai-kit.mdc.proposed').write_text('later edit', encoding='utf-8')
        with self.assertRaisesRegex(KitError, '拒绝覆盖'):
            rollback(self.w, result['backup'])

    def test_shell_compatibility_entrypoint_handles_spaces(self):
        if os.name == 'nt':
            self.skipTest('POSIX adapter test')
        p = subprocess.run(['sh', str(KIT / 'scripts/validate.sh'), '-Workspace', str(self.w), '-ConfigOnly'], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue(json.loads(p.stdout)['ok'])

    def test_cli_failure_is_structured_and_nonzero(self):
        p = subprocess.run([sys.executable, str(KIT / 'scripts/kit.py'), 'confirm', '--workspace', str(self.w), '--expect', '999', '--by', 'user', '--note', 'test'], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(p.returncode, 1)
        self.assertFalse(json.loads(p.stderr)['ok'])
        self.assertNotIn('Traceback', p.stderr)

    def test_multi_repo_dependencies(self):
        backend = self.w / 'api'
        backend.mkdir()
        subprocess.run(['git', 'init', '-b', 'main', str(backend)], check=True, capture_output=True)
        (backend / 'api.py').write_text('ok = True\n', encoding='utf-8')
        self.p['repos']['api'] = 'api'
        self.p['runtime']['checks']['api-unit'] = {'repo': 'api', 'argv': [sys.executable, '-c', 'print("ok")']}
        atomic(self.w / 'project.yaml', self.p)
        b = self.bundle()
        b['artifacts']['tasks.yaml']['tasks'][0]['depends_on'] = ['API-1']
        b['artifacts']['tasks.yaml']['tasks'].append({'id': 'API-1', 'title': 'prepare contract', 'repo': 'api', 'requirements': ['R1'], 'depends_on': [], 'files': ['api.py'], 'checks': ['api-unit']})
        self.ready(b)
        self.assertIn('API-1', next_step(self.w)['action'])
        with self.assertRaisesRegex(KitError, '前置任务'):
            self.mutate('start', target='TASK-1')
        self.mutate('start', target='API-1')
        run_check(self.w, None, 'api-unit', self.state()['revision'])
        self.mutate('finish', target='API-1')
        self.assertIn('TASK-1', next_step(self.w)['action'])


    def test_quick_profile_uses_one_brief_without_extra_documents(self):
        b = self.bundle()
        b['state'].update(profile='quick', files={r: 'brief.md' for r in ('requirement', 'impact', 'plan')})
        for name in ('Existing Spec.md', '05-impact.md', '06-plan.md'):
            del b['artifacts'][name]
        b['artifacts']['brief.md'] = '# 修复说明\n范围内 R1：默认值为2。明确不做：接口和数据库。仅修改 src/app.py，由 unit 验证。'
        self.ready(b)
        self.assertEqual(next_step(self.w)['phase'], 'build')
        self.assertFalse((self.d / '05-impact.md').exists())

    def test_cross_system_requires_delivery_and_rollback_assessments(self):
        b = self.bundle()
        b['state']['profile'] = 'cross-system'
        prepare(self.w, None, 0, b)
        self.assertTrue(any('rollback' in x for x in issues_for(self.w, ready=True)))
        b['artifacts']['requirements.yaml']['assessments'] = {k: '已核对本次影响；无额外变更' for k in ('interfaces', 'data', 'permissions', 'failure_modes', 'async_cache', 'delivery_order', 'rollback')}
        prepare(self.w, None, self.state()['revision'], b)
        self.assertFalse(issues_for(self.w, ready=True))

    def test_change_and_reconfirm_does_not_resurrect_old_evidence(self):
        self.finish_auto()
        self.mutate('change', by='user', note='重新核查需求范围')
        self.mutate('confirm', by='user', note='确认当前版本')
        self.mutate('start', target='TASK-1')
        with self.assertRaisesRegex(KitError, '证据'):
            self.mutate('finish', target='TASK-1')

    def test_restarting_doing_task_does_not_erase_scope_baseline(self):
        self.ready()
        self.mutate('start', target='TASK-1')
        before = self.state()['tasks']['TASK-1']['files_before']
        (self.repo / 'unexpected.py').write_text('new', encoding='utf-8')
        with self.assertRaisesRegex(KitError, '进行中'):
            self.mutate('start', target='TASK-1')
        self.assertEqual(self.state()['tasks']['TASK-1']['files_before'], before)

    def test_switching_current_during_check_keeps_evidence_on_original_requirement(self):
        marker = Path(self.tmp.name) / 'started'
        self.p['runtime']['checks']['unit']['argv'] = [sys.executable, '-c', f'from pathlib import Path; import time; Path({str(marker)!r}).touch(); time.sleep(0.25)']
        atomic(self.w / 'project.yaml', self.p)
        self.ready()
        rev = self.state()['revision']
        with ThreadPoolExecutor(max_workers=1) as pool:
            running = pool.submit(run_check, self.w, None, 'unit', rev)
            deadline = time.monotonic() + 5
            while not marker.exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertTrue(marker.exists())
            adopt(self.w, 'REQ-two', apply=True)
            result = running.result(timeout=5)
        self.assertEqual(result['result'], 'passed')
        self.assertEqual(self.state()['revision'], rev + 1)
        other = self.d.parent / 'REQ-two'
        self.assertEqual(read(other / 'status.yaml')['revision'], 0)
        self.assertFalse((other / '.kit/evidence').exists())

    def test_check_preconditions_are_scoped_to_that_check(self):
        self.ready()
        self.assertEqual(self.run_unit()['result'], 'passed')
        self.p['runtime']['checks']['db-read'] = {'repo': 'ui', 'argv': [sys.executable, '-c', 'print("read")'], 'requires': ['database']}
        atomic(self.w / 'project.yaml', self.p)
        with self.assertRaisesRegex(KitError, '前置'):
            run_check(self.w, None, 'db-read', self.state()['revision'])
        with self.assertRaisesRegex(KitError, '只读'):
            run_check(self.w, None, 'db-read', self.state()['revision'], ready=['database'])

    def test_optional_missing_source_does_not_block_text_requirement(self):
        b = self.bundle()
        b['state']['sources']['S2'] = {'type': 'recording', 'status': 'skipped', 'required': False, 'reason': '没有录像'}
        self.ready(b)
        self.assertEqual(next_step(self.w)['phase'], 'build')

    def test_required_uncollected_source_blocks_confirmation(self):
        b = self.bundle()
        b['state']['sources']['S2'] = {'type': 'design', 'status': 'pending', 'required': True}
        prepare(self.w, None, 0, b)
        with self.assertRaisesRegex(KitError, '尚未收集'):
            self.mutate('confirm', by='user', note='try')

    def test_single_repo_workspace_can_install(self):
        standalone = Path(self.tmp.name) / 'single'
        standalone.mkdir()
        subprocess.run(['git', 'init', '-b', 'main', str(standalone)], check=True, capture_output=True)
        install(standalone, apply=True)
        project = read(standalone / 'project.yaml')
        self.assertEqual(project['repos'], {'app': '.'})
        self.assertEqual(project['docs']['mode'], 'tracked')

    def test_missing_shared_directory_fails_before_writing_configuration(self):
        standalone = Path(self.tmp.name) / 'shared-client'
        standalone.mkdir()
        (standalone / 'app').mkdir()
        (standalone / 'app/package.json').write_text('{}', encoding='utf-8')
        with self.assertRaisesRegex(KitError, '共享目录'):
            install(standalone, apply=True, mode='share', share=str(Path(self.tmp.name) / 'unmounted'))
        self.assertFalse((standalone / 'project.yaml').exists())

    def test_install_preview_does_not_write(self):
        standalone = Path(self.tmp.name) / 'preview'
        standalone.mkdir()
        (standalone / 'app').mkdir()
        (standalone / 'app/package.json').write_text('{}', encoding='utf-8')
        self.assertTrue(install(standalone)['changes'])
        self.assertFalse((standalone / 'project.yaml').exists())

    def test_config_migration_preserves_legacy_commands_and_is_reversible(self):
        self.p.pop('schema_version')
        self.p['runtime']['test'] = 'npm test && echo done'
        self.p['conventions']['branch'] = {'enabled': False, 'base': ''}
        atomic(self.w / 'project.yaml', self.p)
        original = (self.w / 'project.yaml').read_bytes()
        self.assertIn('project.yaml', install(self.w, migrate_config=True)['changes'])
        result = install(self.w, apply=True, migrate_config=True)
        updated = read(self.w / 'project.yaml')
        self.assertEqual(updated['schema_version'], 2)
        self.assertEqual(updated['runtime']['test'], 'npm test && echo done')
        self.assertFalse(updated['conventions']['confirmed'])
        rollback(self.w, result['backup'])
        self.assertEqual((self.w / 'project.yaml').read_bytes(), original)

    def test_powershell_adapter_when_available(self):
        ps = shutil.which('pwsh') or shutil.which('powershell')
        if not ps:
            self.skipTest('PowerShell not installed; Windows matrix is configured but not run here')
        env = dict(os.environ, DEV_AI_KIT_PYTHON=sys.executable)
        process = subprocess.run([ps, '-NoProfile', '-File', str(KIT / 'scripts/validate.ps1'), '-Workspace', str(self.w), '-ConfigOnly'], env=env, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertTrue(json.loads(process.stdout)['ok'])


    def test_referenced_source_cannot_be_skipped(self):
        b = self.bundle()
        b['state']['sources']['S1'].update(status='skipped', reason='not available')
        prepare(self.w, None, 0, b)
        self.assertTrue(any('尚未实际收集' in x for x in issues_for(self.w, ready=True)))

    def test_malformed_command_is_caught_before_confirmation(self):
        self.p['runtime']['checks']['unit']['argv'] = 'npm test'
        atomic(self.w / 'project.yaml', self.p)
        prepare(self.w, None, 0, self.bundle())
        self.assertTrue(any('argv' in x for x in issues_for(self.w, ready=True)))

    def test_install_write_failure_restores_user_files(self):
        rule = self.w / '.cursor/rules/dev-ai-kit.mdc'
        rule.write_text('custom-rule', encoding='utf-8')
        before = (self.w / 'project.yaml').read_bytes()
        from kitcore import workspace
        real_atomic = workspace.atomic
        failed = False
        def fail_on_proposed(path, data):
            nonlocal failed
            if Path(path).name == 'dev-ai-kit.mdc.proposed' and not failed:
                failed = True
                raise OSError('simulated full disk')
            return real_atomic(path, data)
        with patch('kitcore.workspace.atomic', side_effect=fail_on_proposed):
            with self.assertRaises(OSError):
                install(self.w, apply=True)
        self.assertEqual((self.w / 'project.yaml').read_bytes(), before)
        self.assertEqual(rule.read_text(), 'custom-rule')
        self.assertFalse((self.w / '.dev-ai-kit.lock').exists())

    def test_updated_scope_resets_previously_finished_tasks(self):
        self.finish_auto()
        (self.d / 'Existing Spec.md').write_text('new confirmed scope needs another review and updated acceptance', encoding='utf-8')
        self.mutate('confirm', by='user', note='重新确认新范围')
        self.assertEqual(self.state()['tasks']['TASK-1']['status'], 'pending')

    def test_real_assertion_failure_cannot_finish_task(self):
        self.p['runtime']['checks']['unit']['argv'] = [sys.executable, '-c', 'import runpy; assert runpy.run_path("src/app.py")["value"] == 2']
        atomic(self.w / 'project.yaml', self.p)
        self.ready()
        self.mutate('start', target='TASK-1')
        self.assertEqual(self.run_unit()['result'], 'failed')
        with self.assertRaises(KitError):
            self.mutate('finish', target='TASK-1')
        (self.repo / 'src/app.py').write_text('value = 2\n', encoding='utf-8')
        self.assertEqual(self.run_unit()['result'], 'passed')
        self.mutate('finish', target='TASK-1')
        self.assertEqual(next_step(self.w)['phase'], 'accept')


class StorageTests(unittest.TestCase):
    def test_duplicate_keys_rejected_without_echoing_values(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / 'config.yaml'
            p.write_text('key: first\nkey: secret-example\n', encoding='utf-8')
            with self.assertRaises(KitError) as ctx:
                read(p)
            self.assertNotIn('secret-example', str(ctx.exception))

    def test_traversal_and_symlink_escape_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'root'
            root.mkdir()
            with self.assertRaises(KitError):
                inside(root, '../other')
            if os.name != 'nt':
                (root / 'outside').symlink_to(Path(temp), target_is_directory=True)
                with self.assertRaises(KitError):
                    inside(root, 'outside/escape')


if __name__ == '__main__':
    unittest.main()
