import unittest
from unittest.mock import patch
import contextlib
import json
from pathlib import Path
import tempfile

import supervise_ws30_v14_transport as s


def failed(error, event='controller_stopped', failures=None):
    return {'events': [{'event': event, 'error': error}], 'failures': failures or {}}


PROBE = "ssh python3 -c import glob,os,json; ids=['id']; /source/mix/output/*/config.log "


class TransportRecoveryTests(unittest.TestCase):
    def test_second_supervisor_cannot_hold_same_lock(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(s,'LOCK',Path(folder)/'lock'):
            with s.supervisor_lock():
                with self.assertRaises(OSError):
                    with s.supervisor_lock():pass

    def test_identified_timeout_can_reenter_guarded_r2(self):
        self.assertTrue(s.retry_reason(failed(PROBE + 'timed out after 45 seconds'), '', 0))

    def test_identified_disconnect_can_reenter_guarded_r2(self):
        self.assertTrue(s.retry_reason(failed(PROBE + 'returned non-zero exit status 255'), '', 0))

    def test_mutating_build_timeout_is_not_retried(self):
        self.assertIsNone(s.retry_reason(failed('ssh remote_worker.py build timed out after 45 seconds'), '', 0))

    def test_host_identity_error_is_not_retried(self):
        self.assertIsNone(s.retry_reason(failed(PROBE + 'returned non-zero exit status 255'),
                                        'Host key verification failed', 0))

    def test_simulation_failure_is_not_retried(self):
        self.assertIsNone(s.retry_reason(failed(PROBE + 'timed out after 45 seconds',
                                               failures={'id': {'status': 'FAILED'}}), '', 0))

    def test_old_controller_error_is_not_reused(self):
        self.assertIsNone(s.retry_reason(failed(PROBE + 'timed out after 45 seconds'), '', 1))

    def test_start_or_admission_attention_stops_recovery(self):
        state=failed(PROBE + 'timed out after 45 seconds')
        state['events'].insert(0, {'event': 'start_attention'})
        self.assertIsNone(s.retry_reason(state, '', 0))

    def test_wrong_model_cannot_spawn_a_child(self):
        policy={'execution_authorized':True,'supervisor_sha256':'hash',
                'resume_plan_sha256':'hash','authorization_sha256':'hash',
                'maximum_transport_restarts':2,'backoff_seconds':[10,30]}
        with patch.object(s.v,'read',return_value=policy), patch.object(s.v,'sha',return_value='hash'), \
             patch.object(s.resume,'authorize',side_effect=RuntimeError('Actual supervision must be Luna')), \
             patch.object(s.subprocess,'Popen') as spawn:
            with self.assertRaises(RuntimeError):s.run(None)
            spawn.assert_not_called()

    def exercise_children(self, error, complete=False):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'results').mkdir();state=root/'state.json'
            state.write_text(json.dumps({'events':[],'verified':{},'failures':{}}))
            class Child:
                pid=123
                def wait(self):
                    row=json.loads(state.read_text())
                    if complete:row['verified']={str(i):{} for i in range(140)}
                    else:row['events'].append({'event':'controller_stopped','error':error})
                    state.write_text(json.dumps(row))
                    return 0 if complete else 1
            with patch.object(s,'preflight',return_value={}), \
                 patch.object(s,'supervisor_lock',return_value=contextlib.nullcontext()), \
                 patch.object(s.v,'ROOT',root),patch.object(s.resume,'STATE',state), \
                 patch.object(s.subprocess,'Popen',side_effect=lambda *a,**k:Child()) as spawn, \
                 patch.object(s.time,'sleep') as sleep:
                code=s.run(Path('actual-session.jsonl'))
                return code,spawn.call_count,[x.args[0] for x in sleep.call_args_list]

    def test_restart_budget_stops_after_three_total_attempts(self):
        self.assertEqual(self.exercise_children(PROBE+'timed out after 45 seconds'),(1,3,[10,30]))

    def test_nontransport_child_error_stops_immediately(self):
        self.assertEqual(self.exercise_children('Source mismatch'),(1,1,[]))

    def test_complete_child_does_not_restart(self):
        self.assertEqual(self.exercise_children('',complete=True),(0,1,[]))


if __name__ == '__main__':unittest.main()
