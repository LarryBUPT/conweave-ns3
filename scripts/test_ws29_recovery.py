"""Offline recovery identity, GO/STOP, unit-evidence and target checks."""
import copy
import json
import shutil
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

import run_ws29_recovery as runner
import prepare_ws29_recovery as prepare
import remote_worker as worker
import test_ws29_regression_entry as passage_tests


class RecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan,cls.contract,cls.lock = runner.load()

    def test_all_active_identities_and_segment_coverage(self):
        self.assertEqual(len(self.plan['cells']),13)
        self.assertEqual(len(self.plan['reuse']),14)
        self.assertEqual(self.plan['cells'][0]['label'],'link-23-c0')
        self.assertEqual(self.plan['source_sha'],self.contract['source_sha'])
        self.assertEqual(self.plan['unit_id'],self.contract['new_id'])
        self.assertEqual(self.plan['unit_id'],prepare.PREFIX+'unit')
        self.assertEqual(runner.engine.SOURCE,prepare.OLD)
        self.assertTrue(all(c['source_sha']==prepare.SOURCE for c in self.plan['cells']))

    def test_stale_top_level_source_unit_and_cell_rejected(self):
        for target,key,value in [('plan','source_sha',prepare.OLD),('plan','unit_id','old-unit'),
                                 ('contract','source_sha',prepare.OLD),('contract','new_id','old-unit')]:
            plan,contract=copy.deepcopy(self.plan),copy.deepcopy(self.contract)
            (plan if target=='plan' else contract)[key]=value
            with self.assertRaisesRegex(RuntimeError,'identity'):
                runner.validate_identity(plan,contract)
        plan=copy.deepcopy(self.plan); plan['cells'][0]['source_sha']=prepare.OLD
        with self.assertRaisesRegex(RuntimeError,'identity'):
            runner.validate_identity(plan,self.contract)

    def test_new_unit_case_and_stage_order_required(self):
        contract=copy.deepcopy(self.contract);contract['required_pass_cases'].pop()
        with self.assertRaisesRegex(RuntimeError,'New physical test'):
            runner.validate_identity(self.plan,contract)
        plan=copy.deepcopy(self.plan);plan['cells'].reverse()
        with self.assertRaisesRegex(RuntimeError,'order'):
            runner.validate_identity(plan,self.contract)

    def test_local_prepare_cannot_call_remote(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(runner,'load',return_value=(self.plan,self.contract,self.lock)), \
             patch.object(runner,'EVIDENCE',Path(tmp)), \
             patch.object(runner.remote,'config',side_effect=AssertionError('No SSH')), \
             patch.object(runner,'command',side_effect=AssertionError('No remote')):
            self.assertEqual(runner.execute('prepare')['remote_actions'],0)
            row=json.loads((Path(tmp)/'ws29-segmented-recovery-entry.json').read_text())
            self.assertEqual(row['unit_build'][-3:],['--unit-suite','devices-point-to-point','--unit-compat'])
            self.assertEqual(row['unit_build'][row['unit_build'].index('--source-sha')+1],prepare.SOURCE)

    def test_missing_go_blocks_every_phase_before_remote_and_preserves_old_stop(self):
        before=runner.OLD_STOP.read_bytes()
        with tempfile.TemporaryDirectory() as tmp,patch.object(runner,'CONTROL',Path(tmp)), \
             patch.object(runner,'load',return_value=(self.plan,self.contract,self.lock)), \
             patch.object(runner,'worker_identity',side_effect=AssertionError('No SSH')), \
             patch.object(runner,'command',side_effect=AssertionError('No remote')):
            for phase in ('unit-build','unit-collect','build','start','collect'):
                with self.assertRaisesRegex(RuntimeError,'GO missing'):
                    runner.execute(phase,'link-23-c0')
            self.assertFalse((Path(tmp)/'STOP.json').exists())
        self.assertEqual(before,runner.OLD_STOP.read_bytes())

    def test_go_binds_stage_runner_worker_plan_contract_and_stop(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(runner,'CONTROL',Path(tmp)):
            good=runner.binding(self.plan,self.lock,'unit')
            approval=Path(tmp)/'approval-unit.json'
            approval.write_text(json.dumps(good))
            runner.authorize(self.plan,self.lock,'unit')
            for key in ('stage','runner_sha256','worker_sha256','plan_sha256','unit_contract_sha256','old_stop_sha256','source_sha'):
                bad=dict(good);bad[key]='stale';approval.write_text(json.dumps(bad))
                with self.assertRaisesRegex(RuntimeError,'does not bind'):
                    runner.authorize(self.plan,self.lock,'unit')
            approval.write_text(json.dumps(good));(Path(tmp)/'STOP.json').write_text('{}')
            with self.assertRaisesRegex(RuntimeError,'Recovery STOP'):
                runner.authorize(self.plan,self.lock,'unit')

    def test_old_stop_removal_or_mutation_rejected(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(runner,'OLD_STOP',Path(tmp)/'STOP.json'):
            with self.assertRaisesRegex(RuntimeError,'Original STOP'):
                runner.stop_guard(self.plan)
            (Path(tmp)/'STOP.json').write_text('{}')
            with self.assertRaisesRegex(RuntimeError,'Original STOP'):
                runner.stop_guard(self.plan)

    def test_simulation_go_still_requires_new_cpp_unit(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(runner,'CONTROL',Path(tmp)), \
             patch.object(runner,'load',return_value=(self.plan,self.contract,self.lock)), \
             patch.object(runner,'worker_identity',side_effect=AssertionError('No SSH')):
            (Path(tmp)/'approval-physical.json').write_text(json.dumps(runner.binding(self.plan,self.lock,'physical')))
            with self.assertRaisesRegex(RuntimeError,r'C\+\+ unit not accepted'):
                runner.execute('build','link-23-c0')
            self.assertTrue((Path(tmp)/'STOP.json').exists())

    def test_new_worker_prefix_gets_resource_and_required_case_policy(self):
        self.assertTrue(worker.ws29_managed_experiment(self.plan['cells'][0]['id']))
        self.assertTrue(worker.ws29_managed_experiment('20261022-180000-ws29-obs2-link-20-c0'))
        self.assertFalse(worker.ws29_managed_experiment('20261023-090000-unrelated'))
        self.assertEqual(list(worker.ws29_unit_cases(self.plan['unit_id'])),self.contract['required_pass_cases'])
        self.assertEqual(len(worker.ws29_unit_cases('old-unit')),5)

    def test_new_13_parameter_chains_reach_controller_and_worker_without_remote(self):
        helper=passage_tests.RegressionEntryTests()
        for cell in self.plan['cells']:
            params=helper.passage(cell)
            for name in ('arm','fault','fault_tor','fault_port','fault_start_ns','fault_end_ns'):
                self.assertEqual(params['ws29_'+name],cell[name])
            for name,value in cell['control_options'].items():self.assertEqual(params[name],value)
            args=runner.engine.build_arguments(cell,prepare.SOURCE)
            self.assertEqual(args[args.index('--source-sha')+1],cell['source_sha'])

    def test_unit_build_source_and_compatibility_flags_reach_worker_parser(self):
        calls=[]; builds=[]
        args=runner.manifest(self.plan,self.contract,self.lock)['unit_build']
        with patch.object(runner.remote,'config',return_value={}), \
             patch.object(runner.remote,'local_fork',return_value=(str(runner.ROOT),'https://github.com/LarryBUPT/conweave-ns3.git','feature/ws29-downstream-feedback',prepare.SOURCE)), \
             patch.object(runner.remote,'worker_call',side_effect=lambda cfg,*a:calls.append(list(a))), \
             patch('sys.argv',['remote_experiment.py']+args):
            self.assertEqual(runner.remote.main(),0)
        with patch.object(worker,'build',side_effect=lambda *a:builds.append(a)), \
             patch('sys.argv',['remote_worker.py']+calls[0]):worker.main()
        self.assertEqual(builds[0][0:2],(self.plan['unit_id'],prepare.SOURCE))
        self.assertEqual(builds[0][-2:],('devices-point-to-point',True))

    def test_preflight_uses_explicit_source_and_separate_recorder(self):
        output=json.dumps(dict(mem_available_gib=100,free_gib=1000,load_1m=0)).encode()
        with patch.object(runner.engine.remote,'config',return_value={}), \
             patch.object(runner.engine.remote,'ssh_base',return_value=['ssh']), \
             patch.object(runner.engine.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=output)) as run, \
             patch.object(runner.engine,'receipt',side_effect=AssertionError('Old control must not change')), \
             patch.object(runner,'record') as record:
            runner.engine.preflight(self.plan['cells'][0],self.plan['resource_limits'],False,
                source_sha=prepare.SOURCE,record=record)
            code=run.call_args.args[0][-1]
            self.assertIn(prepare.SOURCE,code);self.assertNotIn(prepare.OLD,code)
            record.assert_called_once()

    def test_running_unit_collect_does_not_fetch_or_advance(self):
        status=json.dumps(dict(git_commit=prepare.SOURCE,status='TESTING'))
        with tempfile.TemporaryDirectory() as tmp,patch.object(runner,'CONTROL',Path(tmp)/'control'), \
             patch.object(runner,'ROOT',Path(tmp)), \
             patch.object(runner,'load',return_value=(self.plan,self.contract,self.lock)), \
             patch.object(runner,'authorize'),patch.object(runner,'worker_identity'), \
             patch.object(runner,'command',return_value=status) as command:
            self.assertEqual(runner.execute('unit-collect')['status'],'TESTING')
            command.assert_called_once_with(self.plan,dict(id=self.plan['unit_id'],label='unit'),['status',self.plan['unit_id']])
            self.assertFalse((Path(tmp)/'control/STOP.json').exists())

    def test_failed_unit_fetches_once_and_stops_only_new_control(self):
        original=runner.OLD_STOP.read_bytes()
        status=json.dumps(dict(git_commit=prepare.SOURCE,status='UNIT_FAILED'))
        with tempfile.TemporaryDirectory() as tmp,patch.object(runner,'CONTROL',Path(tmp)/'control'), \
             patch.object(runner,'ROOT',Path(tmp)), \
             patch.object(runner,'load',return_value=(self.plan,self.contract,self.lock)), \
             patch.object(runner,'authorize'),patch.object(runner,'worker_identity'), \
             patch.object(runner,'command',side_effect=[status,'fetched']) as command:
            with self.assertRaisesRegex(RuntimeError,'Terminal failure'):
                runner.execute('unit-collect')
            self.assertEqual(command.call_args.args[-1],['fetch',self.plan['unit_id']])
            self.assertEqual(json.loads((Path(tmp)/'control/STOP.json').read_text())['id'],self.plan['unit_id'])
        self.assertEqual(original,runner.OLD_STOP.read_bytes())

    def test_accepted_unit_collect_rechecks_local_bytes_without_remote(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(runner,'CONTROL',Path(tmp)/'control'), \
             patch.object(runner,'ROOT',Path(tmp)), \
             patch.object(runner,'load',return_value=(self.plan,self.contract,self.lock)), \
             patch.object(runner,'authorize'), \
             patch.object(runner,'worker_identity',side_effect=AssertionError('No SSH')):
            folder=Path(tmp)/'results'/self.plan['unit_id'];folder.mkdir(parents=True);self.fixture(folder)
            row=runner.verify_unit(folder,self.plan,self.contract)
            runner.immutable(Path(tmp)/'control/unit.verified.json',row)
            self.assertEqual(runner.execute('unit-collect')['remote_actions'],0)

    def fixture(self,base):
        logs=base/'logs';logs.mkdir()
        core=prepare.blob(prepare.SOURCE,self.contract['file'])
        meta=dict(experiment_id=self.contract['new_id'],git_commit=prepare.SOURCE,status='TESTED',unit_status='PASS',
                  unit_suite=self.contract['suite'],unit_compatibility=True,cpu_jobs=2,build_mode='optimized',
                  unit_pass_cases=self.contract['required_pass_cases'])
        (base/'metadata.json').write_text(json.dumps(meta))
        for name in self.contract['required_logs']:(logs/name).write_text('placeholder\n')
        (logs/'build.log').write_text("'build' finished successfully\n")
        (logs/'ws29-point-to-point-unit-test.log').write_text('\n'.join('PASS '+n for n in self.contract['required_pass_cases']))
        (logs/'unit-suites.log').write_text(self.contract['suite']+'\n')
        (logs/'command-line-test-suite.original').write_bytes(core)
        (logs/'unit-compatibility.patch').write_text(self.contract['exact_diff'])
        (logs/'unit-compatibility.json').write_text(json.dumps(dict(source_sha=prepare.SOURCE,file=self.contract['file'],
            original_sha256=self.contract['original_sha256'],restored_sha256=self.contract['original_sha256'],
            patched_sha256=self.contract['patched_sha256'],tracked_diff_after_restore='')))
        (logs/'unit-commands.json').write_text(json.dumps([
            ['./waf','configure','--enable-tests','--build-profile=optimized','--out=build-ws29-tests'],
            ['./waf','--out=build-ws29-tests','-j2'],['runner','--print-test-name-list'],
            ['runner','--suite='+self.contract['suite'],'--verbose']]))
        sample=dict(process_tree_rss_mib=20,mem_available_gib=100,free_gib=1000,load_1m=1,status='TESTING')
        (logs/'resource-samples.jsonl').write_text(json.dumps(sample)+'\n')
        (logs/'resource-summary.json').write_text(json.dumps(dict(id=self.contract['new_id'],final_status='TESTED',
            samples=1,peak_tree_rss_mib=20,minimum_mem_available_gib=100,minimum_free_gib=1000,maximum_load_1m=1)))
        return logs

    def test_unit_acceptance_needs_new_case_and_restored_compatibility(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);logs=self.fixture(folder)
            self.assertEqual(runner.verify_unit(folder,self.plan,self.contract)['source_sha'],prepare.SOURCE)
            test=logs/'ws29-point-to-point-unit-test.log';original=test.read_text()
            test.write_text('\n'.join(original.splitlines()[:-1]))
            with self.assertRaisesRegex(RuntimeError,'verbose unit PASS'):
                runner.verify_unit(folder,self.plan,self.contract)
            test.write_text(original)
            compat=logs/'unit-compatibility.json';row=json.loads(compat.read_text());row['restored_sha256']='bad'
            compat.write_text(json.dumps(row))
            with self.assertRaisesRegex(RuntimeError,'restoration'):
                runner.verify_unit(folder,self.plan,self.contract)

    def test_unit_resource_summary_must_match_samples(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);logs=self.fixture(folder)
            path=logs/'resource-summary.json';row=json.loads(path.read_text());row['peak_tree_rss_mib']=1
            path.write_text(json.dumps(row))
            with self.assertRaisesRegex(RuntimeError,'differs from samples'):
                runner.verify_unit(folder,self.plan,self.contract)

    def test_physical_target_validation_uses_real_old_raw_and_rejects_host_port(self):
        cell=next(c for c in self.plan['cells'] if c['label']=='link-20-c0')
        original=runner.ROOT/'results/20261022-180000-ws29-obs2-link-20-c0'
        runner.verify_physical_targets(original,cell)
        meta=json.loads((original/'metadata.json').read_text());rawid=str(meta['raw_directory'])
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);(folder/'config').mkdir();(folder/'raw'/rawid).mkdir(parents=True)
            shutil.copyfile(original/'metadata.json',folder/'metadata.json')
            shutil.copyfile(original/'config/topology.txt',folder/'config/topology.txt')
            text=(original/'raw'/rawid/'config.log').read_text()
            self.assertIn('switch=32 port=6 up=0',text)
            (folder/'raw'/rawid/'config.log').write_text(text.replace('switch=32 port=6 up=0','switch=32 port=1 up=0'))
            with self.assertRaisesRegex(RuntimeError,'host port'):
                runner.verify_physical_targets(folder,cell)


if __name__=='__main__':unittest.main()
