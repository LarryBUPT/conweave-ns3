"""Strict WS21 identity parsing, including the actual simulator header."""
import unittest

from verify_ws29_engineering import parse_identity


HEADER = 'side tor src dst sport dport first_port packets upstream_ce first_ns last_ns inconsistent unmapped'
SOURCE = 'source 1280 4 36 10002 100 14 9 0 2000000070 2000000662 0 0'
DESTINATION = 'destination 1281 4 36 10002 100 14 9 0 2000000130 2000000694 0 0'


class IdentityParserTests(unittest.TestCase):
    def test_actual_header_and_data(self):
        rows = parse_identity([HEADER, SOURCE, DESTINATION])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['side'], 'source')
        self.assertEqual(rows[1]['side'], 'destination')
        self.assertEqual(rows[0]['sport'], 10002)
        self.assertTrue(all(row['unmapped'] == row['inconsistent'] == 0 for row in rows))

    def test_requires_exact_header_and_data(self):
        for lines in ([], [HEADER], [SOURCE], [HEADER.replace('unmapped', 'unknown'), SOURCE],
                      [HEADER + ' extra', SOURCE], [HEADER, HEADER, SOURCE]):
            with self.subTest(lines=lines), self.assertRaises(ValueError):
                parse_identity(lines)

    def test_rejects_bad_columns_side_and_every_numeric_field(self):
        bad = ['', ' '.join(SOURCE.split()[:-1]), SOURCE + ' 0', SOURCE.replace('source', 'other')]
        for index in range(1, 13):
            for value in ('bad', '1.0', '-1', '1e3', '１'):
                fields = SOURCE.split(); fields[index] = value
                bad.append(' '.join(fields))
        for line in bad:
            with self.subTest(line=line), self.assertRaises(ValueError):
                parse_identity([HEADER, SOURCE, line, DESTINATION])

    def test_preserves_violation_counts_for_acceptance(self):
        fields = SOURCE.split(); fields[-2:] = ['2', '3']
        row = parse_identity([HEADER, ' '.join(fields)])[0]
        self.assertEqual((row['inconsistent'], row['unmapped']), (2, 3))


if __name__ == '__main__':
    unittest.main()
