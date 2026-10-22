"""Offline parameter passage, sequence gates, STOP and scope separation."""
import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run_ws29_engineering as entry
import run_ws29_regressions as engine
import test_ws29_regression_entry as regression_tests


class EngineeringEntryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan, cls.cells = entry.load_plan()

    def test_exact_24_unchanged_cells_and_order(self):
        self.assertEqual(len(entry.LABELS), 24)
        self.assertEqual([c['label'] for c in self.cells[:3]], list(engine.LABELS))
        self.assertEqual([c['label'] for c in self.cells[3:]], list(entry.LABELS))
        self.assertEqual(entry.LABELS[0], 'k4-c1-normal')
        self.assertEqual(entry.LABELS[-3:], ('main-c1', 'main-c2', 'main-c3'))
        self.assertEqual({c['id'] for c in self.cells}, {c['id'] for c in self.plan['cells']})
        for c in self.cells:
            self.assertEqual(c, next(x for x in self.plan['cells'] if x['id'] == c['id']))
            self.assertNotIn('--unit-compat', engine.build_arguments(c))

    def test_all_24_commands_reach_worker_with_frozen_controls_and_faults(self):
        helper = regression_tests.RegressionEntryTests()
        for cell in self.cells[3:]:
            with self.subTest(label=cell['label']):
                params = helper.passage(cell)
                for key in ('arm', 'fault', 'fault_tor', 'fault_port', 'fault_start_ns', 'fault_end_ns'):
                    self.assertEqual(params['ws29_' + key], cell[key])
                self.assertEqual(params['flow_file'], cell['trace'])
                self.assertEqual(params['max_concurrent'] if 'max_concurrent' in params else 1, 1)
                self.assertEqual(params['ws25_diag'], 0)

    def test_prepare_is_local_and_complete(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(entry, 'MANIFEST', Path(tmp)/'entry.json'), \
             patch.object(engine.remote, 'config', side_effect=AssertionError('No SSH')), \
             patch.object(engine, 'command', side_effect=AssertionError('No remote command')):
            manifest = entry.prepare(self.plan, self.cells)
            self.assertEqual(len(manifest['cells']), 24)
            self.assertEqual(manifest['plan_sha256'], engine.PLAN_SHA)
            self.assertEqual(manifest['order'], list(entry.LABELS))
            self.assertTrue(all(row['frozen_cell']['source_sha'] == engine.SOURCE for row in manifest['cells']))

    def test_stage_transition_rechecks_every_prior_raw_and_rejects_missing(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(engine, 'CONTROL', Path(tmp)):
            selected = next(c for c in self.cells if c['label'] == 'main-c1')
            previous = self.cells[:self.cells.index(selected)]
            for cell in previous:
                (Path(tmp)/(cell['label']+'.verified.json')).write_text('{}')
            seen = []
            engine.guard_sequence(self.plan, self.cells, selected,
                                  lambda p,c: seen.append(c['id']))
            self.assertEqual(seen, [c['id'] for c in previous])
            (Path(tmp)/'synthetic-17.verified.json').unlink()
            with self.assertRaisesRegex(RuntimeError, 'Previous cell not accepted'):
                engine.guard_sequence(self.plan, self.cells, selected, lambda p,c: None)

    def test_existing_stop_is_preserved_without_remote_action(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(engine, 'CONTROL', Path(tmp)), \
             patch.object(engine, 'preflight', side_effect=AssertionError('No SSH')):
            stop = Path(tmp)/'STOP.json'; stop.write_bytes(b'original failure\n')
            with self.assertRaisesRegex(RuntimeError, 'Failure stop receipt'):
                engine.execute_phase(argparse.Namespace(phase='build', label=self.cells[0]['label']),
                                     self.plan, self.cells)
            self.assertEqual(stop.read_bytes(), b'original failure\n')

    def test_preflight_failure_stops_without_build_or_next_cell(self):
        cell = self.cells[3]
        with tempfile.TemporaryDirectory() as tmp, patch.object(engine, 'CONTROL', Path(tmp)), \
             patch.object(engine, 'guard_sequence'), patch.object(engine.remote, 'local_fork'), \
             patch.object(engine, 'preflight', side_effect=RuntimeError('unhealthy host')), \
             patch.object(engine, 'command') as command:
            with self.assertRaisesRegex(RuntimeError, 'unhealthy host'):
                engine.execute_phase(argparse.Namespace(phase='build', label=cell['label']), self.plan, self.cells)
            command.assert_not_called()
            self.assertEqual(json.loads((Path(tmp)/'STOP.json').read_text())['id'], cell['id'])

    def test_corrupt_prior_raw_is_not_accepted_by_receipt_flag(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(engine, 'CONTROL', Path(tmp)):
            (Path(tmp)/(self.cells[0]['label']+'.verified.json')).write_text('{}')
            with self.assertRaisesRegex(ValueError, 'corrupt raw'):
                engine.guard_sequence(self.plan, self.cells, self.cells[1],
                                      lambda p,c: (_ for _ in ()).throw(ValueError('corrupt raw')))

    def test_terminal_failure_fetches_raw_and_stops_before_verification(self):
        cell = self.cells[3]
        with tempfile.TemporaryDirectory() as tmp, patch.object(engine, 'ROOT', Path(tmp)), \
             patch.object(engine, 'CONTROL', Path(tmp)/'control'), \
             patch.object(engine, 'guard_sequence'), \
             patch.object(engine, 'status', return_value={'status':'FAILED'}), \
             patch.object(engine, 'command') as command, patch.object(engine, 'local_verify') as verify:
            with self.assertRaisesRegex(RuntimeError, 'Terminal failure'):
                engine.execute_phase(argparse.Namespace(phase='collect', label=cell['label']),
                                     self.plan, self.cells)
            command.assert_called_once_with(cell, ['fetch', cell['id']])
            verify.assert_not_called()
            self.assertEqual(json.loads((Path(tmp)/'control/STOP.json').read_text())['id'], cell['id'])

    def test_running_collect_does_not_fetch_verify_or_advance(self):
        cell = self.cells[3]
        with tempfile.TemporaryDirectory() as tmp, patch.object(engine, 'ROOT', Path(tmp)), \
             patch.object(engine, 'guard_sequence'), \
             patch.object(engine, 'status', return_value={'status':'RUNNING'}), \
             patch.object(engine, 'command') as command, patch.object(engine, 'local_verify') as verify:
            self.assertIsNone(engine.execute_phase(argparse.Namespace(phase='collect', label=cell['label']),
                                                  self.plan, self.cells))
            command.assert_not_called(); verify.assert_not_called()

    def test_zero_natural_opportunity_allowed_synthetic_kept_separate(self):
        main = next(c for c in self.cells if c['label'] == 'main-c2')
        lines = ['WS29_SUMMARY rows=1', 'WS29_DECISION reason=no_samples proposed=6 local=6 chosen=6']
        row = entry.observation(lines, main)
        self.assertEqual((row['two_fresh'], row['would_change'], row['adopted_changed']), (0,0,0))
        self.assertEqual(row['scope'], 'natural-main-demand')
        self.assertTrue(row['A06'].startswith('OPEN'))
        synthetic = next(c for c in self.cells if c['label'] == 'synthetic-15')
        other = entry.observation(['WS29_SUMMARY rows=2', 'WS29_SYNTHETIC fault=15',
            'WS29_DECISION reason=distinct_ce proposed=7 local=6 chosen=7'], synthetic)
        self.assertEqual(other['scope'], 'synthetic')
        self.assertEqual(other['adopted_changed'], 1)
        self.assertTrue(other['A06'].startswith('OPEN'))
        with self.assertRaisesRegex(RuntimeError, 'synthetic event count'):
            entry.observation(['WS29_SUMMARY rows=0'], synthetic)
        with self.assertRaisesRegex(RuntimeError, 'event row limit'):
            entry.observation(['WS29_SUMMARY rows=500001'], main)

    def test_cost_ledgers_do_not_add_enqueue_and_dequeue(self):
        cell = next(c for c in self.cells if c['label'] == 'main-c1')
        lines = ['WS29_SUMMARY rows=2',
                 'WS29_CONTROL switch=32 port=6 type=state event=enqueue bytes=72',
                 'WS29_CONTROL switch=32 port=6 type=state event=dequeue bytes=72',
                 'WS29_QP tx_payload_bytes=100']
        row = entry.observation(lines, cell)
        self.assertEqual(row['control_by_kind_event']['state/enqueue']['wire_bytes'], 72)
        self.assertEqual(row['control_by_kind_event']['state/dequeue']['wire_bytes'], 72)
        self.assertEqual(row['control_per_link_kind_event']['32/6/state/enqueue']['packets'], 1)
        self.assertEqual(row['application_input_bytes'], cell['input_bytes'])
        self.assertEqual(row['tx_payload_bytes'], 100)


if __name__ == '__main__':
    unittest.main()
