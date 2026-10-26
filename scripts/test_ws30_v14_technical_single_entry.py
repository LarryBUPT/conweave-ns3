"""Scope/model rejection checks; no remote calls or native simulation."""
import copy
from contextlib import nullcontext
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import run_ws30_v14_technical_single as entry


class ScopeTests(unittest.TestCase):
    def setUp(self):
        self.gate = {'approved': True, 'external_sync_approved': True,
                     'phases': ['technical-single'], 'phase_caps': {'technical-single': 1},
                     'ids': [entry.ID], 'fixed_source_sha': entry.SOURCE,
                     'authorization_evidence': {'source': 'test fixture'}}

    def test_exact_scope_accepted(self):
        entry.check_scope(self.gate)

    def test_phase_expansion_refused(self):
        for name in ('technical-rest', 'life-pair', 'w5-rest'):
            gate = copy.deepcopy(self.gate)
            gate['phases'].append(name)
            with self.assertRaises(RuntimeError):
                entry.check_scope(gate)

    def test_cap_expansion_refused(self):
        self.gate['phase_caps']['technical-single'] = 4
        with self.assertRaises(RuntimeError):
            entry.check_scope(self.gate)

    def test_source_or_id_substitution_refused(self):
        for key, value in (('ids', [entry.ID+'-retry']), ('fixed_source_sha', '0'*40)):
            gate = copy.deepcopy(self.gate)
            gate[key] = value
            with self.assertRaises(RuntimeError):
                entry.check_scope(gate)

    def test_unapproved_refused(self):
        self.gate['approved'] = False
        with self.assertRaises(RuntimeError):
            entry.check_scope(self.gate)

    def test_wrong_model_stops_before_backend(self):
        with patch.object(entry.v, 'require_model', side_effect=RuntimeError('model gate')), \
                patch.object(entry.v, 'Backend') as backend:
            with self.assertRaises(RuntimeError):
                entry.run(None)
            backend.assert_not_called()


class FrozenExecutorTests(unittest.TestCase):
    def test_original_main_passes_load_and_authorize_before_backend(self):
        with patch.object(entry, 'preflight'), \
                patch.object(entry.v, 'require_model'), \
                patch.object(entry.v, 'authorize', wraps=entry.v.authorize) as authorize, \
                patch.object(entry.v.recovery, 'controller_lock', return_value=nullcontext()), \
                patch.object(entry.v, 'prerequisite', side_effect=RuntimeError('offline stop before Backend')), \
                patch.object(entry.v, 'Backend') as backend:
            with self.assertRaisesRegex(RuntimeError, 'offline stop before Backend'):
                entry.run(None)
            authorize.assert_called_once_with([entry.PHASE], Path('None'))
            backend.assert_not_called()

    def test_real_load_then_real_authorize_use_separate_receipts(self):
        with entry.scoped_executor(None):
            _, schedule, cells = entry.v.load()
            self.assertEqual(schedule, entry.v.read(entry.v.SCHEDULE))
            self.assertEqual(schedule['authorization_file'],
                             entry.ORIGINAL_AUTH.relative_to(entry.v.ROOT).as_posix())
            self.assertEqual(cells[entry.ID]['source_sha'], entry.SOURCE)
            self.assertEqual(entry.v.AUTH, entry.AUTH)
            with patch.object(entry.v, 'require_model') as model:
                gate = entry.v.authorize([entry.PHASE], None)
            model.assert_called_once_with(None, 'supervision')
            self.assertEqual(gate['ids'], [entry.ID])

    def test_real_load_rejects_schedule_tampering(self):
        read = entry.v.read
        def altered(path):
            value = read(path)
            if path == entry.v.SCHEDULE:
                value['same_host_overlap'] = True
            return value
        with entry.scoped_executor(None), patch.object(entry.v, 'read', side_effect=altered):
            with self.assertRaisesRegex(RuntimeError, 'Frozen schedule differs'):
                entry.v.load()
            self.assertEqual(entry.v.AUTH, entry.AUTH)

    def test_real_load_rejects_fixed_source_input_tampering(self):
        with entry.scoped_executor(None), \
                patch.object(entry.v.subprocess, 'check_output', return_value=b'changed input'):
            with self.assertRaisesRegex(RuntimeError, 'Fixed-source input blob changed'):
                entry.v.load()

    def test_real_authorize_rejects_control_hash_tampering(self):
        read = entry.v.read
        def altered(path):
            value = read(path)
            if path == entry.AUTH:
                value['control_sha256']['scripts/run_ws30_v14.py'] = '0'*64
            return value
        with entry.scoped_executor(None), patch.object(entry.v, 'read', side_effect=altered):
            with self.assertRaisesRegex(RuntimeError, 'Controller/worker/verifier version not approved'):
                entry.v.authorize([entry.PHASE], None)

    def test_real_authorize_rejects_actual_wrong_model(self):
        with tempfile.TemporaryDirectory() as folder:
            session = Path(folder)/'session.jsonl'
            session.write_text('{"type":"turn_context","payload":'
                               '{"model":"gpt-6.1-sol","effort":"medium"}}\n')
            with entry.scoped_executor(session):
                with self.assertRaisesRegex(RuntimeError, 'Actual supervision must be'):
                    entry.v.authorize([entry.PHASE], session)

    def test_executor_globals_restored_after_failure(self):
        previous = entry.v.load, entry.v.AUTH, sys.argv
        with self.assertRaisesRegex(RuntimeError, 'retained failure'):
            with entry.scoped_executor(None):
                raise RuntimeError('retained failure')
        self.assertIs(entry.v.load, previous[0])
        self.assertEqual(entry.v.AUTH, previous[1])
        self.assertIs(sys.argv, previous[2])


if __name__ == '__main__':
    unittest.main()
