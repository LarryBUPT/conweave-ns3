"""Offline guards and recovery tests; no remote calls, builds or simulations."""
import copy
from contextlib import nullcontext
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import run_ws30_v14_technical_rest as e


class RestTests(unittest.TestCase):
    def setUp(self):
        self.gate = e.v.read(e.AUTH)
        self.cells = [{'id':i, 'source_sha':e.SOURCE} for i in e.IDS]
        self.state = {'contract':hashlib.sha256(json.dumps(self.cells,sort_keys=True).encode()).hexdigest(),
                      'verified':{}, 'pending':list(e.IDS[:4]), 'failures':{}, 'cap':4}
        self.snapshot = {'states':{i:None for i in e.IDS}}
        self.inventory = {i:{'runs':False,'results':False} for i in e.IDS}

    def check(self, builds=()):
        with patch.object(e.resume, 'local_inventory', return_value=[]), \
                patch.object(e.v, 'verify_common'):
            e.reconcile(self.cells,self.state,self.snapshot,self.inventory,builds)

    def occupy(self, status, ident=None):
        ident = ident or e.IDS[0]
        self.snapshot['states'][ident] = {'status':status,'git_commit':e.SOURCE}
        self.inventory[ident] = {'runs':True,'results':True}

    def test_prepared_scope_is_exact_and_not_released(self):
        e.check_scope(self.gate)
        with self.assertRaisesRegex(RuntimeError,'release pending'):
            e.check_scope(self.gate,execution=True)

    def test_scope_expansion_rejected(self):
        for key,value in [('ids',list(e.IDS)+[e.single.ID]),('phases',[e.PHASE,'life-pair']),
                          ('phase_caps',{e.PHASE:8}),('fixed_source_sha','0'*40),
                          ('maximum_transport_restarts',3)]:
            gate=copy.deepcopy(self.gate);gate[key]=value
            with self.assertRaises(RuntimeError):e.check_scope(gate)

    def test_wrong_model_before_backend(self):
        with patch.object(e.v,'require_model',side_effect=RuntimeError('actual model')), \
                patch.object(e.v,'Backend') as backend:
            with self.assertRaisesRegex(RuntimeError,'actual model'):e.run(None)
            backend.assert_not_called()

    def test_unreleased_receipt_before_backend_or_journal(self):
        with patch.object(e.v,'require_model'),patch.object(e.v,'Backend') as backend, \
                patch.object(e,'note') as note:
            with self.assertRaisesRegex(RuntimeError,'release pending'):e.run(None)
            backend.assert_not_called();note.assert_not_called()

    def test_original_main_load_and_authorize_retain_scope_and_globals(self):
        original_read=e.v.read
        def released(path):
            gate=original_read(path)
            if path==e.AUTH:gate['approved']=True
            return gate
        before=e.v.load,e.v.AUTH,sys.argv
        with patch.object(e.v,'read',side_effect=released),patch.object(e.v,'require_model'), \
                patch.object(e.v.recovery,'controller_lock',return_value=nullcontext()), \
                patch.object(e.v,'prerequisite',side_effect=RuntimeError('offline boundary')), \
                patch.object(e.v,'Backend') as backend, \
                patch.object(e.v,'authorize',wraps=e.v.authorize) as authorize:
            with self.assertRaisesRegex(RuntimeError,'offline boundary'):
                with e.scoped_executor(None):e.v.main()
            authorize.assert_called_once_with([e.PHASE],Path('None'))
            backend.assert_not_called()
        self.assertIs(e.v.load,before[0]);self.assertEqual(e.v.AUTH,before[1]);self.assertIs(sys.argv,before[2])

    def test_real_local_validation_and_dependency(self):
        session=Path(r'C:\Users\Administrator\.codex\sessions\2026\10\26\rollout-2026-10-26T04-37-01-01a174c7-ecf5-7f21-a9dc-6f8b4f5634b8.jsonl')
        with patch.object(e.v,'Backend') as backend:
            _,cells=e.validate(session,'analysis')
            self.assertEqual([c['id'] for c in cells],list(e.IDS))
            backend.assert_not_called()

    def test_single_phase_accepted_required(self):
        original_read=e.v.read
        def damaged(path):
            data=original_read(path)
            if path==e.single.STATE:data['events'][-1]['event']='batch_verified'
            return data
        with patch.object(e.v,'read',side_effect=damaged):
            with self.assertRaisesRegex(RuntimeError,'accepted terminal'):e.dependency({})

    def test_empty_reserved_ids_are_safe_without_occupied_paths(self):
        self.check()

    def test_built_running_successful_are_reconciled_without_mutation(self):
        for status in ('BUILT','RUNNING','SUCCEEDED'):
            self.occupy(status);self.check()

    def test_stale_building_refused_live_build_not_rebuilt(self):
        self.occupy('BUILDING')
        with self.assertRaisesRegex(RuntimeError,'Stale BUILDING'):self.check()
        self.check([e.IDS[0]])

    def test_unowned_occupied_id_refused(self):
        self.occupy('BUILT',e.IDS[-1])
        with self.assertRaisesRegex(RuntimeError,'Unowned'):self.check()

    def test_failed_worker_or_state_never_restarted(self):
        self.occupy('FAILED')
        with self.assertRaisesRegex(RuntimeError,'must be preserved'):self.check()
        self.state['failures']={'id':'retained'}
        with self.assertRaisesRegex(RuntimeError,'invalid or failed'):self.check()

    def test_missing_metadata_with_build_intent_refused(self):
        with patch.object(e.resume,'local_inventory',return_value=[Path('retained-intent')]):
            with self.assertRaisesRegex(RuntimeError,'Ambiguous empty metadata'):
                e.reconcile(self.cells,self.state,self.snapshot,self.inventory)

    def test_transport_retry_only_recognized_read_only_probe(self):
        error="import glob,os,json; ids=[]; config.log returned non-zero exit status 255"
        state={'failures':{},'events':[{'event':'controller_stopped','error':error}]}
        self.assertIsNotNone(e.transport.retry_reason(state,error,0))
        self.assertIsNone(e.transport.retry_reason(state,error,1))
        self.assertIsNone(e.transport.retry_reason(state,'Permission denied',0))
        for event in ('start_attention','failed_preserved','admission_stop'):
            altered=copy.deepcopy(state);altered['events'].insert(0,{'event':event})
            self.assertIsNone(e.transport.retry_reason(altered,error,0))

    def test_transport_reentry_reconciles_before_second_main(self):
        error="import glob,os,json; ids=[]; config.log returned non-zero exit status 255"
        calls=[]
        with tempfile.TemporaryDirectory() as directory:
            state=Path(directory)/'state.json'
            def controller():
                calls.append('main')
                if len(calls)==1:
                    state.write_text(json.dumps({'failures':{},'events':[
                        {'event':'controller_stopped','error':error}]}))
                    raise RuntimeError(error)
            with patch.object(e,'STATE',state),patch.object(e,'validate'), \
                    patch.object(e,'supervisor_lock',return_value=nullcontext()), \
                    patch.object(e,'note'),patch.object(e,'preflight',return_value={}) as preflight, \
                    patch.object(e.v,'main',side_effect=controller),patch.object(e.time,'sleep') as sleep:
                e.run(None)
                self.assertEqual(len(calls),2)
                self.assertEqual([c.kwargs['continuing'] for c in preflight.call_args_list],[False,True])
                sleep.assert_called_once_with(10)

    def test_preflight_error_never_retries_controller(self):
        with patch.object(e,'validate'),patch.object(e,'supervisor_lock',return_value=nullcontext()), \
                patch.object(e,'note'),patch.object(e,'preflight',side_effect=RuntimeError('occupied')), \
                patch.object(e.v,'main') as main,patch.object(e.time,'sleep') as sleep:
            with self.assertRaisesRegex(RuntimeError,'occupied'):e.run(None)
            main.assert_not_called();sleep.assert_not_called()

    def test_recovery_budget_is_two_reentries(self):
        error="import glob,os,json; ids=[]; config.log timed out after 45 seconds"
        with tempfile.TemporaryDirectory() as directory:
            state=Path(directory)/'state.json'
            def controller():
                data=json.loads(state.read_text()) if state.exists() else {'failures':{},'events':[]}
                data['events'].append({'event':'controller_stopped','error':error})
                state.write_text(json.dumps(data));raise RuntimeError(error)
            with patch.object(e,'STATE',state),patch.object(e,'validate'), \
                    patch.object(e,'supervisor_lock',return_value=nullcontext()),patch.object(e,'note'), \
                    patch.object(e,'preflight',return_value={}), \
                    patch.object(e.v,'main',side_effect=controller) as main,patch.object(e.time,'sleep') as sleep:
                with self.assertRaisesRegex(RuntimeError,'timed out'):e.run(None)
                self.assertEqual(main.call_count,3)
                self.assertEqual([c.args[0] for c in sleep.call_args_list],[10,30])

    def test_second_supervisor_lock_refused(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(e,'LOCK',Path(directory)/'lock'):
            with e.supervisor_lock():
                with self.assertRaises(OSError):
                    with e.supervisor_lock():self.fail('second supervisor acquired lock')


if __name__=='__main__':unittest.main()
