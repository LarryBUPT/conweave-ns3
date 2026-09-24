#!/usr/bin/env python3
"""Check input-denominator and target-subset semantics of MoE analysis."""
import hashlib
import json
import os
import tempfile
import unittest

import analyze_moe_tags


class MoETagAnalysisTest(unittest.TestCase):
    def test_missing_completion_and_fixed_target(self):
        old_project = analyze_moe_tags.PROJECT
        with tempfile.TemporaryDirectory() as project:
            analyze_moe_tags.PROJECT = project
            try:
                experiment = '20260925-000000-test'
                base = os.path.join(project, 'results', experiment)
                config = os.path.join(base, 'config')
                raw = os.path.join(base, 'raw', '123')
                os.makedirs(config)
                os.makedirs(raw)
                trace = b'3\n0 4 3 8192 2.000000000 2\n0 8 3 8192 2.000000000 2\n1 9 3 65536 2.000000000 1\n'
                with open(os.path.join(config, 'traffic_trace.txt'), 'wb') as target:
                    target.write(trace)
                with open(os.path.join(base, 'metadata.json'), 'w') as target:
                    json.dump({'status': 'SUCCEEDED', 'raw_directory': '123',
                               'input_flow_sha256': hashlib.sha256(trace).hexdigest(),
                               'git_commit': 'abc', 'algorithm': 'dualtrack'}, target)
                fct = os.path.join(raw, '123_out_fct.txt')
                with open(fct, 'w') as target:
                    target.write('0 4 10000 100 8192 2000000000 1000 900\n')
                    target.write('1 9 10000 100 65536 2000000000 2000 1800\n')
                target_trace = os.path.join(project, 'target.txt')
                with open(target_trace, 'w') as target:
                    target.write('1\n0 4 3 8192 2.000000000 2\n')
                summary = analyze_moe_tags.summarize(experiment, target_trace)
                self.assertEqual(summary['tags']['2']['input_flows'], 2)
                self.assertEqual(summary['tags']['2']['unfinished_flows'], 1)
                self.assertIsNone(summary['tags']['2']['synthetic_batch_completion_us'])
                self.assertEqual(summary['target_moe']['completed_flows'], 1)
                self.assertEqual(summary['target_moe']['synthetic_batch_completion_us'], 1.0)
                with open(fct, 'a') as output:
                    output.write('0 4 10000 100 8192 2000000000 1000 900\n')
                with self.assertRaisesRegex(ValueError, 'duplicate'):
                    analyze_moe_tags.summarize(experiment, target_trace)
            finally:
                analyze_moe_tags.PROJECT = old_project


if __name__ == '__main__':
    unittest.main()
