"""Local process-boundary checks; all remote entry points are replaced by mocks."""
import ast
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT/'scripts'/file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


controller = module('label_controller', 'remote_experiment.py')
worker = module('label_worker', 'remote_worker.py')
BASE = ['run', '20261101-114500-ws31-label-test', '--lb', 'ws31-c1',
        '--flow-file', 'ws31_correctness_r1.txt', '--ws30-observe', '2',
        '--pfc', '0', '--irn', '1']


class LabelRunner(unittest.TestCase):
    def test_controller_worker_cli_metadata(self):
        for profile in range(4):
            with patch.object(sys, 'argv', ['controller']+BASE+['--ws31-label-profile', str(profile)]), \
                    patch.object(controller, 'config', return_value={}), \
                    patch.object(controller, 'worker_call') as call:
                self.assertEqual(controller.main(), 0)
            args = list(call.call_args.args[1:])
            self.assertEqual(args[:3], ['run', '--id', BASE[1]])
            # Local controller emits worker's positional ID as --id; worker's
            # run parser has always consumed that option.
            with patch.object(sys, 'argv', ['worker']+args), patch.object(worker, 'start') as start:
                worker.main()
            params = start.call_args.args[1]
            self.assertEqual(params['ws31_label_profile'], profile)
            self.assertEqual(params['flow_file'], 'ws31_correctness_r1.txt')
            self.assertEqual(params['ws30_tag_transform'], 0)
            env = worker.ws31_label_environment(params, {'WS31_LABEL_PROFILE': '3', 'KEEP': 'value'})
            self.assertEqual(env['WS31_LABEL_PROFILE'], str(profile))
            self.assertEqual(env['KEEP'], 'value')

    def test_conflicts_rejected_before_dispatch(self):
        invalid = [('--lb', 'fecmp'), ('--ws30-tag-transform', '1'),
                   ('--ws30-composition', '1'), ('--ws30-lifecycle', '4'),
                   ('--ws30-life-profile', '1'), ('--ws30-observe', '1'),
                   ('--pfc', '1'), ('--irn', '0'), ('--flow-file', 'old.txt'),
                   ('--topo', 'ws30_composition8'), ('--ws23-pfc-probe-host', '1'),
                   ('--ws25-diag', '1')]
        for key, value in invalid:
            args=BASE+['--ws31-label-profile', '1', key, value]
            for obj, argv in ((controller, args), (worker, ['run', '--id']+args[1:])):
                with patch.object(sys, 'argv', ['test']+argv), \
                        patch.object(controller, 'config', return_value={}), \
                        patch.object(controller, 'worker_call') as call, \
                        patch.object(worker, 'start') as start:
                    with self.assertRaises(RuntimeError):
                        obj.main()
                    call.assert_not_called()
                    start.assert_not_called()

    def test_inherited_profile_cleared_for_old_metadata(self):
        inherited={'WS31_LABEL_PROFILE': '3'}
        self.assertEqual(worker.ws31_label_environment({}, inherited)['WS31_LABEL_PROFILE'], '0')
        self.assertEqual(inherited['WS31_LABEL_PROFILE'], '3')

    def test_active_profile_clears_disabled_inherited_diagnostics(self):
        params = {'ws31_label_profile': 1, 'lb': 'ws31-c1', 'ws30_observe': 2,
                  'pfc': 0, 'irn': 1, 'topo': 'leaf_spine_128_100G_OS2',
                  'flow_file': 'ws31_correctness_r1.txt'}
        inherited = {'WS25_DIAG': '1', 'IRN_PFC_DROP_DIAG': '1', 'KEEP': 'yes'}
        env = worker.ws31_label_environment(params, inherited)
        self.assertNotIn('WS25_DIAG', env)
        self.assertNotIn('IRN_PFC_DROP_DIAG', env)
        self.assertEqual(env['KEEP'], 'yes')
        self.assertEqual(inherited['WS25_DIAG'], '1')
        with self.assertRaises(RuntimeError):
            worker.ws31_label_environment(dict(params, ws25_diag=1), inherited)

    def test_worker_python35_syntax(self):
        ast.parse((ROOT/'scripts/remote_worker.py').read_text(encoding='utf-8'), feature_version=(3, 5))


if __name__ == '__main__':
    unittest.main(verbosity=2)
