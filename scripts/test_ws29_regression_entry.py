"""Offline checks for real legacy configs and controller/worker parameter passage."""
import copy
import contextlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import remote_experiment as controller
import remote_worker as worker
import run_ws29_regressions as entry
from verify_ws29_engineering import config
from ws29_evidence_checks import (verify_settings, verify_regression_config,
                                  verify_regression_diagnostics, verify_runtime)


class RegressionEntryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan, cls.cells = entry.load_plan()

    def passage(self, cell):
        calls = []
        with patch.object(controller, 'config', return_value={}), \
             patch.object(controller, 'worker_call', side_effect=lambda cfg, *a: calls.append(list(a))), \
             patch('sys.argv', ['remote_experiment.py'] + entry.run_arguments(cell)):
            self.assertEqual(controller.main(), 0)
        self.assertEqual(len(calls), 1)
        captured = []
        with patch.object(worker, 'start', side_effect=lambda *a, **k: captured.append((a, k))), \
             patch('sys.argv', ['remote_worker.py'] + calls[0]):
            worker.main()
        self.assertEqual(len(captured), 1)
        args, kw = captured[0]
        self.assertEqual(args[0], cell['id'])
        self.assertEqual(kw, dict(max_concurrent=1))
        return args[1]

    def test_three_commands_preserve_effective_metadata_and_defaults(self):
        for cell in self.cells:
            with self.subTest(cell=cell['label']):
                params = self.passage(cell)
                self.assertEqual({k: params[k] for k in cell['control_options']}, cell['control_options'])
                self.assertEqual(params['ws18_path'], int(cell['arm'] < 0))
                self.assertEqual(params['flow_file'], cell['trace'])
                self.assertEqual(params['ws25_diag'], 0)
                verify_regression_diagnostics(dict(parameters=params), cell)
                cfg = config(Path(cell['reference']['root']) / 'config/config.txt')
                cfg.update({k.upper(): str(v) for k, v in params.items() if k.startswith(('ws29_', 'ws21_'))})
                cfg.update(WS23_PFC_PROBE='-1 3 0 0', PAUSE_TIME='5')
                verify_settings(dict(parameters=params), cfg, cell)
                verify_regression_config(config(Path(cell['reference']['root']) / 'config/config.txt'), cfg)

    def test_closed_feedback_arms_are_normalized_without_launch(self):
        for arm in (1, 2, 3):
            cell = copy.deepcopy(self.cells[1]); cell['arm'] = arm
            cell['control_options'].update(ws21_feedback=1, ws21_heartbeat=int(arm in (1, 2)))
            params = self.passage(cell)
            self.assertEqual(params['ws21_identity'], 1)
            self.assertEqual(params['ws21_feedback'], 1)
            self.assertEqual(params['ws21_heartbeat'], int(arm in (1, 2)))

    def test_actual_legacy_schema_accepts_new_disabled_fields_but_rejects_control_drift(self):
        old = config(Path(self.cells[0]['reference']['root']) / 'config/config.txt')
        self.assertNotIn('WS23_PFC_PROBE', old)
        new = dict(old, WS21_IDENTITY='1', WS23_PFC_PROBE='-1 3 0 0', PAUSE_TIME='5', WS29_ARM='-1')
        verify_regression_config(old, new)
        for name, value in [('WS18_PATH', '0'), ('WS21_HEARTBEAT_INTERVAL_NS', '100000'),
                            ('WS21_FEEDBACK', '1'), ('ENABLE_IRN', '0'), ('WS23_PFC_PROBE', '1 3 0 0')]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                verify_regression_config(old, dict(new, **{name: value}))

    def test_fixed_run_py_renders_all_three_configs_matching_real_old_fields(self):
        source = subprocess.check_output(['git', 'show', entry.SOURCE + ':run.py'], cwd=entry.ROOT)
        scope = dict(__name__='offline_config_fixture')
        # NumPy is imported but unused by this fixed run.py. Python 3.12 no
        # longer accepts datetime in random.seed; neither affects config values.
        with patch.dict('sys.modules', {'numpy': SimpleNamespace()}), patch('random.seed'):
            exec(compile(source, 'fixed-run.py', 'exec'), scope)
        class ConfigRendered(Exception):
            pass
        def never_run(argv, **kwargs):
            self.assertEqual(argv[:2], ['./waf', '--run'])
            raise ConfigRendered()
        for cell in self.cells:
            with self.subTest(cell=cell['label']), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); (root / 'config').mkdir()
                for name in (cell['trace'], cell['topology'] + '.txt'):
                    (root / 'config' / name).write_bytes(subprocess.check_output(
                        ['git', 'show', entry.SOURCE + ':config/' + name], cwd=entry.ROOT))
                tokens = entry.run_arguments(cell)[2:]; argv = ['run.py']
                for flag, value in zip(tokens[::2], tokens[1::2]):
                    if flag in ('--max-concurrent', '--ws28-tail-diag'):
                        continue
                    argv.extend([flag.replace('--simul-time', '--simul_time'),
                                 'config/' + value if flag == '--flow-file' else value])
                previous = os.getcwd()
                try:
                    os.chdir(root)
                    with patch('sys.argv', argv), patch('subprocess.check_call', side_effect=never_run), \
                         contextlib.redirect_stdout(io.StringIO()), self.assertRaises(ConfigRendered):
                        scope['main']()
                finally:
                    os.chdir(previous)
                cfg = config(next(root.glob('mix/output/*/config.txt')))
                verify_regression_config(config(Path(cell['reference']['root']) / 'config/config.txt'), cfg)
                verify_settings(dict(parameters=self.passage(cell)), cfg, cell)

    def test_legacy_real_runtime_is_accepted_and_ws29_activation_is_rejected(self):
        cell = self.cells[0]; root = Path(cell['reference']['root'])
        meta = json.loads((root / 'metadata.json').read_text())
        lines = (root / 'raw' / str(meta['raw_directory']) / 'config.log').read_text().splitlines()
        verify_runtime(lines, cell)
        with self.assertRaises(ValueError):
            verify_runtime(lines + ['WS29_SETTINGS arm=0'], cell)
        with self.assertRaises(ValueError):
            verify_runtime([x for x in lines if not x.startswith('WS21_HEARTBEAT ')], cell)

    def test_inherited_environment_cannot_enable_legacy_diagnostics(self):
        original = dict(PATH='keep', WS29_ARM='2', WS25_DIAG='1', WS13_DIAG='1',
                        WS26_TIME_PROBE='1', WS28_TAIL_DIAG='1', IRN_PFC_DROP_DIAG='1')
        self.assertEqual(worker.ws29_clean_environment(original), dict(PATH='keep'))
        self.assertEqual(original['WS29_ARM'], '2')

    def test_next_cell_requires_actual_prior_acceptance(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(entry, 'CONTROL', Path(tmp)):
            with self.assertRaisesRegex(RuntimeError, 'Previous cell not accepted'):
                entry.guard_sequence(self.plan, self.cells, self.cells[1])
            (Path(tmp) / 'STOP.json').write_text('{}')
            with self.assertRaisesRegex(RuntimeError, 'Failure stop receipt'):
                entry.guard_sequence(self.plan, self.cells, self.cells[0])

    def test_sampler_separates_build_from_simulation_and_keeps_first_sample(self):
        real_open = open
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / 'logs').mkdir()
            (root / 'metadata.json').write_text('{"status":"RUNNING"}')
            memfile = root / 'meminfo'; memfile.write_text('MemAvailable: 104857600 kB\n')
            def fixture_open(name, *args, **kwargs):
                return real_open(memfile if str(name) == '/proc/meminfo' else name, *args, **kwargs)
            with patch.object(worker, 'ROOT', tmp), patch('builtins.open', side_effect=fixture_open), \
                 patch.object(worker, 'process_tree_rss_kib', return_value=1024), \
                 patch.object(worker.os, 'getloadavg', return_value=(1, 1, 1), create=True), \
                 patch.object(worker.os, 'statvfs', return_value=SimpleNamespace(f_bavail=1000000000, f_frsize=4096), create=True):
                for prefix, terminal in [('build-resource', 'BUILT'), ('resource', 'SUCCEEDED')]:
                    sampler = worker.ResourceSampler('fixture', tmp, 1, prefix)
                    sampler.finish(terminal)
                    data = json.loads((root / 'logs' / (prefix + '-summary.json')).read_text())
                    self.assertGreaterEqual(data['samples'], 1)
                    self.assertEqual(data['final_status'], terminal)


if __name__ == '__main__':
    unittest.main()
