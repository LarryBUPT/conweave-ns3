"""Finite checks of accepted input invariants, without ns-3 or output files."""
import hashlib
import unittest
from collections import Counter, defaultdict

import ws31_demand_construct as subject


class ConstructorChecks(unittest.TestCase):
    def test_stream_serialization_and_rejection(self):
        stream = subject.Stream('D1', 5310001, 'check')
        expected = int.from_bytes(hashlib.sha256(b'v2|D1|5310001|check|0').digest(), 'big')
        self.assertEqual(stream.word(), expected)
        words = iter([2**256-1, 7])  # n=10 rejects the top6 words.
        stream.word = lambda: next(words)
        self.assertEqual(stream.below(10), 7)
        with self.assertRaises(ValueError):
            stream.below(0)

    def test_all_registered_k0_margins_identity_and_hidden_fields(self):
        for family in ('D1', 'D2'):
            for seed in subject.K0_SEEDS:
                online, evaluation, metadata = subject.construct(family, seed)
                self.assertEqual(len(online), 1120)
                self.assertEqual(Counter(r['policy_tag'] for r in online), {1: 1024, 2: 96})
                self.assertEqual([r['request_id'] for r in online], list(range(1120)))
                self.assertEqual(len({(r['src'], r['dst'], r['sport'], r['dport'], r['generation']) for r in online}), 1120)
                self.assertTrue(all(set(r) == set(subject.ONLINE_FIELDS) for r in online))
                self.assertTrue(all(0 < r['sport'] < 65536 and r['pg'] == 3 for r in online))
                self.assertTrue(all(0 <= r['src'] < 16 and 64 <= r['dst'] < 80 for r in online))
                self.assertEqual([r['demand_ns'] for r in online], sorted(r['demand_ns'] for r in online))
                by_block = defaultdict(list)
                by_task = defaultdict(list)
                for row, truth in zip(online, evaluation):
                    self.assertEqual(row['request_id'], truth['request_id'])
                    self.assertEqual(row['policy_tag'], truth['original_tag'])
                    by_block[truth['construction_block']].append(row)
                    if truth['business_task'] != '':
                        by_task[truth['business_task']].append(row)
                self.assertEqual(len(by_block), 70)
                self.assertEqual(len(by_task), 6)
                for block, rows in by_block.items():
                    self.assertEqual({r['src'] for r in rows}, set(range(16)))
                    self.assertEqual({r['dst'] for r in rows}, set(range(64, 80)))
                    sizes = Counter(r['payload_bytes'] for r in rows)
                    self.assertEqual(sizes, {16384: 16} if family == 'D1' else {16384: 8, 262144: 8})
                for task, rows in by_task.items():
                    self.assertEqual(len(rows), 16)
                    if family == 'D1':
                        self.assertEqual({r['demand_ns'] for r in rows}, {subject.T0+task*metadata['H_ns']//6})
                if family == 'D2':
                    for tag in (1, 2):
                        counts = Counter(r['payload_bytes'] for r in online if r['policy_tag'] == tag)
                        self.assertEqual(counts[16384], counts[262144])

    def test_reference_arithmetic_and_window(self):
        expected = {'D1': (19264000, 550400), 'D2': (163502080, 4671488)}
        for family, (wire, horizon) in expected.items():
            rows, _, metadata = subject.construct(family, 5310001)
            self.assertEqual(metadata['reference_W_bytes'], wire)
            self.assertEqual(metadata['H_ns'], horizon)
            self.assertEqual(metadata['stop_ns'], subject.T0+horizon+max(10*horizon, 10000000))
            self.assertTrue(all(subject.T0 <= r['demand_ns'] < subject.T0+horizon for r in rows))
            self.assertFalse(metadata['actual_runtime_framing_verified'])

    def test_d2_physical_construction_has_no_target_membership(self):
        physical, _, _ = subject.physical_requests('D2', 5310001)
        forbidden = {'policy_tag', 'original_tag', 'business_task', 'target_blocks'}
        self.assertTrue(all(not forbidden.intersection(r) for r in physical))
        self.assertEqual(len(subject.Stream('D2', 5310001, 'target-blocks').permutation(range(70))), 70)

    def test_determinism_and_seed_partition(self):
        for family in ('D1', 'D2'):
            first = subject.bundle_bytes(family, 5310001)
            self.assertEqual(first, subject.bundle_bytes(family, 5310001))
            self.assertNotEqual(first['online-current.csv'], subject.bundle_bytes(family, 5310002)['online-current.csv'])
        stages = [set(range(5310001, 5310009)), set(range(5310101, 5310125)),
                  set(range(5310151, 5310159)), set(range(5310201, 5310249))]
        self.assertEqual(len(set.union(*stages)), 88)


if __name__ == '__main__':
    unittest.main(verbosity=2)
