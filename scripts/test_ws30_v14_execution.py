"""Offline negative tests only. Synthetic control states are not simulation evidence."""
from contextlib import contextmanager
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import run_ws30_v14 as r

@contextmanager
def scratch():
    root=r.ROOT/'results/ws30-v14-offline-tests'
    root.mkdir(parents=True,exist_ok=True)
    yield tempfile.mkdtemp(prefix='negative-',dir=root)

class GuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.plan=r.read(r.CONTRACT);cls.schedule=r.schedule(cls.plan)
    def test_schedule_partitions_all_cells_and_sources(self):
        ids=[i for p in self.schedule['phases'].values() for i in p['ids']]
        self.assertEqual(len(ids),252);self.assertEqual(len(set(ids)),252)
        self.assertEqual(sum(len(self.schedule['phases'][n]['ids']) for n in ('technical-single','technical-rest','life-pair','life-state','life-other')),48)
        self.assertEqual(sum(len(self.schedule['phases'][n]['ids']) for n in ('cw-tech','cw-long','w5-resource','w5-rest')),36)
        self.assertTrue(all(v['source_sha']==(self.plan['formal_source_sha_preserved'] if n.startswith('formal-') else self.plan['source_sha']) for n,v in self.schedule['phases'].items()))
    def test_formal_independent_of_new_life_and_w5(self):
        def deps(n):
            return {d for p in self.schedule['phases'][n]['requires'] for d in ([p]+list(deps(p)) if p in self.schedule['phases'] else [p])}
        self.assertEqual(deps('formal-rest'),{'formal-first','old-source-technical-resource'})
        self.assertNotIn('life-state',deps('w5-rest'))
        self.assertTrue({'technical-single','technical-rest','cw-tech','cw-long','w5-resource'}<=deps('w5-rest'))
    def test_absent_approval_refuses_before_remote(self):
        with scratch() as d,patch.object(r,'AUTH',Path(d)/'absent.json'),patch.object(r.legacy.stage.remote.remote,'config',side_effect=AssertionError('network forbidden')):
            with self.assertRaisesRegex(RuntimeError,'Execution closed'):r.authorize(['technical-single'],None)
    def test_changed_controller_refuses_before_model_or_remote(self):
        with scratch() as d:
            p=Path(d)/'negative-only.json';p.write_text(json.dumps({'approved':True,'external_sync_approved':True,'authorization_evidence':'synthetic unit test only','contract_sha256':r.sha(r.CONTRACT),'schedule_sha256':r.sha(r.SCHEDULE),'control_sha256':{}}))
            with patch.object(r,'AUTH',p),self.assertRaisesRegex(RuntimeError,'version not approved'):r.authorize(['technical-single'],None)
    def test_resume_contract_cannot_change(self):
        with scratch() as d:
            p=Path(d)/'summary.json';p.write_text(json.dumps({'contract':'wrong','verified':{}}))
            with self.assertRaisesRegex(RuntimeError,'Resume contract changed'):r.Runner(self.plan['regression'][:1],None,p)
    def test_remote_source_collision_stops_before_log_query(self):
        c=self.plan['regression'][0];b=r.Backend([c])
        with patch.object(b.base,'snapshot',return_value={'states':{c['id']:{'status':'BUILT','git_commit':'0'*40}}}),patch.object(r.legacy.stage.remote.remote,'config',side_effect=AssertionError('network forbidden')):
            with self.assertRaisesRegex(RuntimeError,'source/state collision'):b.snapshot([c])
    def test_lost_build_return_never_reissues_mutation(self):
        c=self.plan['regression'][0];b=r.Backend([c])
        with scratch() as d,patch.object(r,'ROOT',Path(d)),patch.object(b,'compatible'),patch.object(b,'snapshot',return_value={'states':{c['id']:None}}),patch.object(r.legacy.stage.remote.remote,'config',return_value={}),patch.object(r.legacy.stage.remote.remote,'worker_call',side_effect=RuntimeError('lost return')) as call:
            with self.assertRaisesRegex(RuntimeError,'lost return'):b.build([c])
            with self.assertRaisesRegex(RuntimeError,'prior build intent'):b.build([c])
            self.assertEqual(call.call_count,1)
            self.assertEqual(json.loads((Path(d)/('results/ws30-v14-build-intents/'+c['id']+'.json')).read_text())['state'],'requested')
    def test_validation_failure_persists_and_stops(self):
        c=self.plan['regression'][0]
        class Bad:
            def local(self,c):return True
            def verify(self,c):raise RuntimeError('coverage absent')
        with scratch() as d:
            runner=r.Runner([c],Bad(),Path(d)/'summary.json')
            with self.assertRaisesRegex(RuntimeError,'coverage absent'):runner.collect([c],{c['id']:{'status':'SUCCEEDED'}})
            self.assertIn('validation',r.read(runner.path)['failures'])
    def test_old_source_qualification_from_real_local_raw(self):
        rows=r.old_source_gate();self.assertEqual(len(rows),30)
    def test_no_new_results_exist(self):
        self.assertTrue(all(not (r.ROOT/'results'/c['id']).exists() for g in r.GROUPS for c in self.plan[g]))
    def test_deployed_worker_bytes_must_match(self):
        b=r.Backend([])
        with patch.object(r.legacy.stage.remote.remote,'config',return_value={}),patch.object(r.legacy.stage.remote.remote,'ssh_base',return_value=[]),patch.object(r.subprocess,'check_output',return_value='0'*64):
            with self.assertRaisesRegex(RuntimeError,'Controller/worker mismatch'):b.compatible()
    def test_explicit_seed_arguments_for_prefix_without_filename_seed(self):
        c=next(c for c in self.plan['ConWeave_observation_controls'] if c['trace']=='ws30w5_sustained_prefix.txt')
        b=r.Backend([c])
        with patch.object(b,'compatible'),patch.object(b,'local',return_value=False),patch.object(b,'snapshot',return_value={'states':{c['id']:{'status':'BUILT','git_commit':c['source_sha']}}}),patch.object(r.legacy.stage.engine.calibration,'verify_remote_trace'),patch.object(r.legacy.stage.remote.remote,'config',return_value={}),patch.object(r.legacy.stage.remote.remote,'ssh_base',return_value=[]),patch.object(r.subprocess,'check_output',side_effect=[c['topology_sha256'],'0\n0']),patch.object(r.legacy.stage.remote,'start_watch'),patch.object(r.legacy.stage.remote,'command') as call:
            b.start(c,4)
            args=call.call_args.args
            self.assertEqual(args[args.index('--simulation-seed')+1],'1')
            self.assertEqual(args[args.index('--demand-seed')+1],'20263101')
    def test_retained_failure_cannot_resume_as_success(self):
        with scratch() as d:
            runner=r.Runner(self.plan['regression'][:1],None,Path(d)/'summary.json')
            runner.state['failures']={'prior':'failed physical coverage'}
            with self.assertRaisesRegex(RuntimeError,'Retained failure'):runner.run()
    def test_gate_allows_owned_siblings_but_refuses_unknown_process(self):
        b=r.Backend(self.plan['regression'][:4])
        safe={'load_1m':1,'mem_available_gib':100,'free_gib':1000,'other_users':[],'unexpected_simulation_pids':[],'rss_mib':100}
        with patch.object(b,'compatible'),patch.object(b,'snapshot',return_value={'resource':safe}),patch.object(r.legacy.stage.resources,'host_gate',return_value=dict(safe)) as gate:
            self.assertEqual(b.gate()['unexpected_simulation_pids'],[])
            gate.assert_called_once_with(reject_active=False)
        unsafe=dict(safe,unexpected_simulation_pids=['999'])
        with patch.object(b,'compatible'),patch.object(b,'snapshot',return_value={'resource':unsafe}),patch.object(r.legacy.stage.resources,'host_gate',return_value=dict(safe)):
            with self.assertRaisesRegex(RuntimeError,'Unknown worker'):b.gate()
    def test_four_cell_batch_can_complete_without_extra_human_gate(self):
        cells=self.plan['regression'][:4]
        class Fake:
            def __init__(self):self.states={};self.started=[]
            def gate(self):return {'load_1m':0,'mem_available_gib':100,'free_gib':1000}
            def snapshot(self,cs,known=None,drain=False):return {'states':{c['id']:self.states.get(c['id']) for c in cs},'resource':self.gate()}
            def build(self,cs):
                for c in cs:self.states[c['id']]={'git_commit':c['source_sha'],'status':'BUILT'}
            def start(self,c,cap):self.started.append((c['id'],cap));self.states[c['id']]['status']='SUCCEEDED'
            def local(self,c):return False
            def finish(self,c):return {'id':c['id'],'unit_test_only':True}
            def verify(self,c):return self.finish(c)
        with scratch() as d:
            backend=Fake();state=r.Runner(cells,backend,Path(d)/'runner.json',cap=4).run()
            self.assertEqual(len(state['verified']),4)
            self.assertEqual(backend.started,[(c['id'],4) for c in cells])

if __name__=='__main__':unittest.main()
