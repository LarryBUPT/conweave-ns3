"""Scope/model rejection checks; no remote calls or native simulation."""
import copy
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


if __name__ == '__main__':
    unittest.main()
