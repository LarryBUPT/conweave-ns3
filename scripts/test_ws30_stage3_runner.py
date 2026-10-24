"""Failure/recovery and admission tests using no SSH or simulation launches."""
import hashlib
import json
from pathlib import Path
import tempfile
import contextlib
import io
import os
import runpy
import random
import shutil
import sys
import types
import unittest
from unittest import mock

import analyze_ws30_tags
import run_ws30_stage3 as run


class FakeBackend:
    def __init__(self):
        self.states={};self.locals={};self.starts=[];self.builds=[];self.preserved=[]
        self.memory=120;self.pressure_after_start=None;self.corrupt=set()

    def resource(self):return {'load_1m':0,'mem_available_gib':self.memory,'free_gib':1000}
    def gate(self):return self.resource()
    def local(self,c):return c['id'] in self.locals
    def verify(self,c):
        if c['id'] in self.corrupt:raise RuntimeError('Raw identity/hash mismatch')
        return self.locals[c['id']]
    def snapshot(self,cells,known=None,drain=False):
        if known:
            for c in cells:
                state=self.states.get(c['id'])
                if state and state['status'] in ['RUNNING','BUILDING']:
                    state['status']='SUCCEEDED' if state['status']=='RUNNING' else 'BUILT'
        return {'states':{c['id']:self.states.get(c['id']) for c in cells},'resource':self.resource()}
    def build(self,cells):
        for c in cells:self.builds.append(c['id']);self.states[c['id']]={'status':'BUILT','git_commit':'source'}
    def start(self,c,cap):
        self.starts.append((c['id'],cap));self.states[c['id']]['status']='RUNNING'
        if self.pressure_after_start:self.memory=self.pressure_after_start
    def finish(self,c):self.locals[c['id']]={'id':c['id'],'raw_verified':True};return self.verify(c)
    def preserve_failure(self,c):self.preserved.append(c['id'])


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'state.json'
        self.cells=[{'id':'cell%d'%i,'source_sha':'source'} for i in range(12)]
    def tearDown(self):self.temp.cleanup()

    def test_running_and_building_resume_without_duplicate_build_or_start(self):
        b=FakeBackend();cells=self.cells[:2]
        b.states={'cell0':{'status':'RUNNING','git_commit':'source'},
                  'cell1':{'status':'BUILDING','git_commit':'source'}}
        r=run.Runner(cells,b,self.path);r.state['pending']=['cell0','cell1'];r.save('simulated_crash')
        final=run.Runner(cells,b,self.path).run()
        self.assertEqual(len(final['verified']),2);self.assertFalse(b.builds)
        self.assertEqual(b.starts,[('cell1',12)])

    def test_failure_drains_current_workers_and_never_admits_missing_cell(self):
        b=FakeBackend();cells=self.cells[:3]
        b.states={'cell0':{'status':'FAILED','git_commit':'source'},
                  'cell1':{'status':'RUNNING','git_commit':'source'}}
        r=run.Runner(cells,b,self.path);r.state['pending']=[c['id'] for c in cells];r.save('simulated_crash')
        with self.assertRaises(RuntimeError):r.run()
        self.assertEqual(b.preserved,['cell0']);self.assertFalse(b.starts);self.assertFalse(b.builds)
        saved=run.read(self.path);self.assertEqual(set(saved['verified']),{'cell1'})
        self.assertEqual(set(saved['failures']),{'cell0'})

    def test_pressure_reduces_admission_and_preserves_all_ids(self):
        b=FakeBackend();b.pressure_after_start=60
        final=run.Runner(self.cells,b,self.path).run()
        self.assertEqual(len(final['verified']),12);self.assertEqual(final['cap'],8)
        self.assertEqual(len({i for i,cap in b.starts}),12)
        self.assertTrue(all(cap==8 for i,cap in b.starts[1:]))

    def test_hard_pressure_pauses_new_starts_but_collects_current_success(self):
        b=FakeBackend();b.pressure_after_start=20
        r=run.Runner(self.cells[:3],b,self.path)
        with self.assertRaises(RuntimeError):r.run()
        self.assertEqual(len(b.starts),1);self.assertEqual(len(run.read(self.path)['verified']),1)

    def test_summary_does_not_override_corrupt_raw(self):
        b=FakeBackend();b.locals['cell0']={'id':'cell0'};b.corrupt.add('cell0')
        r=run.Runner(self.cells[:2],b,self.path);r.state['verified']['cell0']={'id':'cell0'}
        with self.assertRaisesRegex(RuntimeError,'Raw identity'):r.run()
        self.assertFalse(b.starts);self.assertFalse(b.builds)

    def test_closed_authorization_performs_no_external_work(self):
        with mock.patch.object(run,'AUTHORIZATION',Path(self.temp.name)/'absent.json'), \
             mock.patch.object(run.subprocess,'check_output') as external:
            with self.assertRaisesRegex(RuntimeError,'closed'):run.authorize('main',None)
            external.assert_not_called()

    def test_unknown_simulation_blocks_admission_even_with_idle_resources(self):
        self.assertEqual(run.capacity({'load_1m':0,'mem_available_gib':120,'free_gib':1000,
                                       'unexpected_simulation_pids':['123']},12),0)

    def test_fixture_build_adapter_supplies_receipt_context_without_changing_cell(self):
        cell={'id':'fixture','source_sha':'source','mode':'classreserve','expected_tags':{'1':2,'2':3}}
        original=dict(cell)
        with mock.patch.object(run.stage.remote,'command'), \
             mock.patch.object(run.stage.engine,'build_missing_group') as build:
            run.Backend().build([cell])
            adapted=build.call_args.args[0][0]
            self.assertEqual(adapted['seed'],0);self.assertEqual(adapted['background'],2)
            self.assertEqual(adapted['run_order'],0);self.assertEqual(cell,original)

    def test_real_driver_reaches_simulator_with_fixed_non_os_topology(self):
        directory=Path(self.temp.name);(directory/'config').mkdir()
        for name in ['ws30_composition8.txt','ws30_composition_swap0_cont0.txt']:
            shutil.copyfile(run.ROOT/'config'/name,directory/'config'/name)
        class ReachedSimulator(Exception):pass
        def waf(argv,**kwargs):
            self.assertEqual(argv[0],'./waf')
            config=Path(argv[2].split(' ',1)[1]).read_text()
            self.assertIn('TOPOLOGY_FILE config/ws30_composition8.txt',config)
            self.assertIn('LB_MODE 21',config)
            raise ReachedSimulator()
        previous=Path.cwd()
        try:
            os.chdir(directory)
            with mock.patch.dict(os.environ,{'WS30_COMPOSITION':'1'}), \
                 mock.patch.dict(sys.modules,{'numpy':types.ModuleType('numpy')}), \
                 mock.patch.object(random,'seed'), \
                 mock.patch.object(sys,'argv',['run.py','--lb','classreserve','--pfc','0','--irn','1',
                  '--bw','400','--buffer','9','--topo','ws30_composition8',
                  '--flow-file','config/ws30_composition_swap0_cont0.txt']), \
                 mock.patch.object(run.subprocess,'check_call',side_effect=waf), \
                 contextlib.redirect_stdout(io.StringIO()):
                module=runpy.run_path(str(run.ROOT/'run.py'))
                with self.assertRaises(ReachedSimulator):module['main']()
        finally:os.chdir(previous)

    def test_class_release_origins_use_hand_calculated_complete_times(self):
        folder=Path(self.temp.name);(folder/'config').mkdir();(folder/'raw/1').mkdir(parents=True)
        trace='3\n0 1 3 1000 2.000000000 1\n0 2 3 1000 2.000020000 2\n0 3 3 1000 2.000020000 2\n'
        (folder/'config/traffic_trace.txt').write_text(trace)
        (folder/'metadata.json').write_text(json.dumps({'status':'SUCCEEDED','raw_directory':'1',
             'input_flow_sha256':hashlib.sha256((folder/'config/traffic_trace.txt').read_bytes()).hexdigest()}))
        (folder/'raw/1/1_out_fct.txt').write_text('0 1 10000 100 1000 2000000000 10000 1\n'
             '0 2 10001 100 1000 2000020000 5000 1\n0 3 10002 100 1000 2000020000 7000 1\n')
        data=analyze_ws30_tags.summarize(folder)
        self.assertEqual(data['tags']['2']['release_origin_ns'],2000020000)
        self.assertEqual(data['tags']['2']['batch_us'],7)
        self.assertEqual(data['tags']['1']['p99_us'],10)


if __name__=='__main__':unittest.main()
