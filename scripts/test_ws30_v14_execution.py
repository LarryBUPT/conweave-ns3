"""Offline negative tests only. Synthetic control states are not simulation evidence."""
from contextlib import contextmanager
import argparse
import ast
from contextlib import redirect_stderr
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import run_ws30_v14 as r
import remote_worker as worker

def command_from_worker(source,params):
    """Evaluate only the real execute() argv construction, never execute()."""
    fn=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='execute')
    first=next(i for i,n in enumerate(fn.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='command' for t in n.targets))
    end=next(i for i,n in enumerate(fn.body[first:],first) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='log' for t in n.targets))
    ns={'params':params,'sys':type('Runtime',(),{'executable':'python3'})}
    exec(compile(ast.Module(body=fn.body[first:end],type_ignores=[]),'<argv only>','exec'),ns)
    return ns['command']

def parser_from_runpy(source):
    # Omit main()'s directory creation and all statements after parse_args().
    fn=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='main')
    first=next(i for i,n in enumerate(fn.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='parser' for t in n.targets))
    end=next(i for i,n in enumerate(fn.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='args' for t in n.targets))
    ns={'argparse':argparse}
    exec(compile(ast.Module(body=fn.body[first:end],type_ignores=[]),'<old parser only>','exec'),ns)
    return ns['parser']

def environment_from_worker(source,params):
    fn=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='execute')
    block=next(n for n in fn.body if isinstance(n,ast.Try)).body
    first=next(i for i,n in enumerate(block) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='simulation_env' for t in n.targets))
    end=next(i for i,n in enumerate(block[first:],first) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='run_checked')
    ns={'params':params,'os':type('Environment',(),{'environ':{}})}
    exec(compile(ast.Module(body=block[first:end],type_ignores=[]),'<environment only>','exec'),ns)
    return ns['simulation_env']

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
        from unittest.mock import Mock
        gate={'approved':True,'external_sync_approved':True,'authorization_evidence':'in-memory negative test only','contract_sha256':r.sha(r.CONTRACT),'schedule_sha256':r.sha(r.SCHEDULE),'control_sha256':{}}
        with patch.object(r,'AUTH',Mock(exists=lambda:True)),patch.object(r,'read',return_value=gate),self.assertRaisesRegex(RuntimeError,'version not approved'):r.authorize(['technical-single'],None)
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
    def test_no_unauthorized_engineering_or_w5_results_exist(self):
        # Formal-first/rest now have their own authorization and real results.
        # The engineering and W5 phases remain closed at this recovery node.
        self.assertTrue(all(not (r.ROOT/'results'/c['id']).exists() for g in r.GROUPS if g!='formal_disabled' for c in self.plan[g]))
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
    def test_actual_model_policy_accepts_medium_and_rejects_high(self):
        for role,(model,effort) in r.MODEL_POLICY.items():
            with patch.object(r,'actual_model',return_value={'model':model,'effort':effort}):r.require_model(None,role)
            with patch.object(r,'actual_model',return_value={'model':model,'effort':'high'}),self.assertRaisesRegex(RuntimeError,'Actual '+role):r.require_model(None,role)
        with patch.object(r,'actual_model',return_value={'model':'gpt-6-sol','effort':'medium'}),self.assertRaisesRegex(RuntimeError,'Actual analysis'):r.require_model(None,'analysis')
    def test_high_receipt_rejected_in_memory_without_creating_authorization(self):
        from unittest.mock import Mock
        gate={'approved':True,'external_sync_approved':True,'authorization_evidence':'in-memory negative test; not authorization','contract_sha256':r.sha(r.CONTRACT),'schedule_sha256':r.sha(r.SCHEDULE),'control_sha256':{f:r.sha(r.ROOT/f) for f in r.CONTROLS},'phases':['formal-first'],'supervision_model':'gpt-6-luna','supervision_effort':'high','analysis_model':'gpt-6.1-sol','analysis_effort':'medium'}
        with patch.object(r,'AUTH',Mock(exists=lambda:True)),patch.object(r,'read',return_value=gate),patch.object(r,'actual_model',return_value={'model':'gpt-6-luna','effort':'medium'}):
            with self.assertRaisesRegex(RuntimeError,'supervision policy'):r.authorize(['formal-first'],None)
            gate['supervision_effort']='medium';r.authorize(['formal-first'],None)
            gate['analysis_model']='gpt-6-sol'
            with self.assertRaisesRegex(RuntimeError,'analysis policy'):r.authorize(['formal-first'],None)
    def formal_rpc(self,c,cap):
        b=r.Backend([c])
        with patch.object(b,'compatible'),patch.object(b,'local',return_value=False),patch.object(b,'snapshot',return_value={'states':{c['id']:{'status':'BUILT','git_commit':c['source_sha']}}}),patch.object(r.legacy.stage.engine.calibration,'verify_remote_trace'),patch.object(r.legacy.stage.remote.remote,'config',return_value={}),patch.object(r.legacy.stage.remote.remote,'ssh_base',return_value=[]),patch.object(r.subprocess,'check_output',side_effect=[c['topology_sha256'],'0\n0']),patch.object(r.legacy.stage.remote,'start_watch'),patch.object(r.legacy.stage.remote,'command') as call:
            b.start(c,cap);controller_argv=list(call.call_args.args)
        controller=r.legacy.stage.remote.remote
        with patch.object(controller.sys,'argv',['controller']+controller_argv),patch.object(controller,'config',return_value={}),patch.object(controller,'worker_call') as call:
            controller.main();rpc=list(call.call_args.args[1:])
        with patch.object(worker.sys,'argv',['worker']+rpc),patch.object(worker,'start') as call:
            worker.main();params=call.call_args.args[1]
        return controller_argv,rpc,params
    def test_all_168_formal_commands_preserve_old_worker_argv(self):
        import subprocess
        old_worker=subprocess.check_output(['git','-c','safe.directory='+r.ROOT.as_posix(),'show',self.plan['formal_source_sha_preserved']+':scripts/remote_worker.py']).decode()
        old_run=subprocess.check_output(['git','-c','safe.directory='+r.ROOT.as_posix(),'show',self.plan['formal_source_sha_preserved']+':run.py']).decode()
        new_worker=(r.ROOT/'scripts/remote_worker.py').read_text()
        parser=parser_from_runpy(old_run)
        self.formal_commands=[]
        for i,c in enumerate(self.plan['formal_disabled']):
            controller,rpc,params=self.formal_rpc(c,4 if i<4 else 8)
            actual=command_from_worker(new_worker,params)
            self.assertEqual(actual,command_from_worker(old_worker,params))
            parsed=parser.parse_args(actual[2:]);self.assertEqual(parsed.lb,c['mode'])
            self.assertEqual(params['simulation_seed'],1);self.assertEqual(params['demand_seed'],c['demand_seed'])
            self.assertEqual(params['ws30_lifecycle'],0);self.assertEqual(params['ws30_life_profile'],0)
            environment=environment_from_worker(new_worker,params)
            old_environment=environment_from_worker(old_worker,params)
            self.assertEqual(environment.pop('WS30_LIFE_PROFILE'),'0')
            self.assertEqual(environment,old_environment)
            for flag in ('--simulation-seed','--demand-seed','--ws30-life-profile'):self.assertNotIn(flag,actual)
            self.formal_commands.append({'id':c['id'],'source_sha':c['source_sha'],'controller':controller,'worker_rpc':rpc,'run_py_argv':actual,'simulation_seed':params['simulation_seed'],'demand_seed':params['demand_seed'],'old_environment_equal':True,'new_ignored_environment':{'WS30_LIFE_PROFILE':'0'}})
        self.assertIn('RANDOM_SEED 1',old_run)
        # Store the real argv derivations only in an ignored local audit draft.
        folder=r.ROOT/'results/ws30-v14-local-history';folder.mkdir(parents=True,exist_ok=True)
        (folder/'formal-command-audit-draft.json').write_text(json.dumps(self.formal_commands,indent=2)+'\n',encoding='utf-8')
    def test_old_parser_rejects_seed_leak_and_worker_rejects_profile_leak(self):
        import subprocess
        old_run=subprocess.check_output(['git','-c','safe.directory='+r.ROOT.as_posix(),'show',self.plan['formal_source_sha_preserved']+':run.py']).decode()
        parser=parser_from_runpy(old_run)
        with redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):parser.parse_args(['--simulation-seed','1'])
        c=self.plan['formal_disabled'][0];_,rpc,_=self.formal_rpc(c,4)
        rpc[rpc.index('--ws30-life-profile')+1]='1'
        with patch.object(worker.sys,'argv',['worker']+rpc),patch.object(worker,'start') as start:
            with self.assertRaisesRegex(RuntimeError,'profile requires lifecycle'):worker.main()
            start.assert_not_called()
        rpc[rpc.index('--ws30-life-profile')+1]='0';rpc[rpc.index('--simulation-seed')+1]='2'
        with patch.object(worker.sys,'argv',['worker']+rpc),patch.object(worker,'start') as start,redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):worker.main()
            start.assert_not_called()

if __name__=='__main__':unittest.main()
