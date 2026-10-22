#!/usr/bin/env python3
"""Ensure the evidence verifier rejects stale, aliased and arm-contaminated rows."""
import unittest
from verify_ws29_engineering import check_decision


class EvidenceTests(unittest.TestCase):
    def valid(self):
        row = dict(time_ns='30000', first='5', second='6', local='5', chosen='6',
                   proposed='6', reason='distinct_ce', a_status='valid', b_status='valid')
        for p, ce in (('a', '1'), ('b', '0')):
            row.update({p+'_samples': '10', p+'_ce': ce, p+'_session': '1',
                        p+'_sequence': '2', p+'_start': '15000', p+'_end': '20000'})
        return row

    def test_actual_comparison(self):
        self.assertTrue(check_decision(self.valid(), 2))

    def test_stale_cannot_be_called_valid(self):
        row = self.valid(); row['a_end'] = '9999'; row['a_start'] = '9000'
        with self.assertRaises(ValueError): check_decision(row, 2)

    def test_c1_must_not_consume(self):
        with self.assertRaises(ValueError): check_decision(self.valid(), 1)
        row = self.valid(); row['chosen'] = row['local']
        self.assertTrue(check_decision(row, 1))

    def test_no_sample_fallback_must_remain_local(self):
        row = self.valid(); row['reason'] = 'a_no_sample'; row['a_samples'] = '0'
        with self.assertRaises(ValueError): check_decision(row, 2)
        row['proposed'] = row['chosen'] = row['local']
        self.assertFalse(check_decision(row, 2))

    def test_same_port_is_not_two_candidates(self):
        row = self.valid(); row['second'] = row['first']
        with self.assertRaises(ValueError): check_decision(row, 2)


if __name__ == '__main__':
    unittest.main()
